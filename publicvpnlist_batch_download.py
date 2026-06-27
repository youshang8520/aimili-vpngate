from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

os.environ.setdefault("PUBLICVPNLIST_AUTO_COUNTRIES", "0")
os.environ.setdefault("PUBLICVPNLIST_SOURCES", "https://publicvpnlist.com/country/usa/")
os.environ.setdefault("PUBLICVPNLIST_MAX_DOWNLOADS", "0")

import vpngate_manager as manager
from playwright.sync_api import sync_playwright

COUNTRY_URL = os.environ.get("PUBLICVPNLIST_BATCH_URL", "https://publicvpnlist.com/country/usa/")
OUT_DIR = Path(os.environ.get("PUBLICVPNLIST_BATCH_DIR", "publicvpnlist_downloads_usa")).resolve()
JSON_OUT = Path(os.environ.get("PUBLICVPNLIST_BATCH_JSON", "publicvpnlist_usa_downloads.json")).resolve()
CSV_OUT = Path(os.environ.get("PUBLICVPNLIST_BATCH_CSV", "publicvpnlist_usa_downloads.csv")).resolve()
MAX_DOWNLOADS = int(os.environ.get("PUBLICVPNLIST_BATCH_MAX", "0") or "0")
PER_COUNTRY_LIMIT = int(os.environ.get("PUBLICVPNLIST_PER_COUNTRY_LIMIT", "20") or "0")
REACHABILITY_WARNING = "We could not confirm that this server is currently reachable"
PREFERRED_DETAIL_BUTTONS = (
    ("#downloadCurrentCheckBtn", "Run current check"),
    ("#dlStart", "Generate .ovpn link"),
)


def click_detail_button(page, selector: str) -> bool:
    locator = page.locator(selector)
    if locator.count() == 0:
        return False
    node = locator.first
    try:
        node.scroll_into_view_if_needed(timeout=5000)
    except Exception:
        pass
    try:
        node.click(timeout=15000)
        page.wait_for_timeout(2500)
        return True
    except Exception:
        try:
            node.evaluate("el => el.click()")
            page.wait_for_timeout(2500)
            return True
        except Exception:
            return False


def ready_download_url(page) -> str:
    ready = page.locator("#dlReadyLink")
    if ready.count() == 0:
        return ""
    try:
        href = (ready.first.get_attribute("href") or "").strip()
    except Exception:
        href = ""
    if href and href != "#" and not href.startswith("javascript:"):
        return urljoin(page.url, href)
    return ""


def generate_ready_url(page, item: dict[str, object]) -> tuple[str, list[str], str]:
    clicked: list[str] = []
    page.goto(str(item["download_url"]), wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(1500)
    body_text = page.locator("body").inner_text()
    if REACHABILITY_WARNING in body_text:
        return "", clicked, body_text

    for selector, label in PREFERRED_DETAIL_BUTTONS:
        if click_detail_button(page, selector):
            clicked.append(label)
            body_text = page.locator("body").inner_text()
            if REACHABILITY_WARNING in body_text:
                return "", clicked, body_text
            ready_url = ready_download_url(page)
            if ready_url:
                return ready_url, clicked, body_text

    body_text = page.locator("body").inner_text()
    return ready_download_url(page), clicked, body_text


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(2, 10000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"cannot allocate unique filename for {path}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_text = manager.fetch_publicvpnlist_page_html(COUNTRY_URL)
    items = manager.extract_publicvpnlist_items(COUNTRY_URL, page_text)
    if PER_COUNTRY_LIMIT > 0:
        items = items[:PER_COUNTRY_LIMIT]
    if MAX_DOWNLOADS > 0:
        items = items[:MAX_DOWNLOADS]

    results: list[dict[str, object]] = []
    successes: list[dict[str, object]] = []
    print(f"[PublicVPNList batch] {COUNTRY_URL} selected={len(items)} per_country_limit={PER_COUNTRY_LIMIT or 'all'} max={MAX_DOWNLOADS or 'all'}", flush=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        download_page = browser.new_page(viewport={"width": 1440, "height": 1200})
        try:
            for index, item in enumerate(items, start=1):
                if not item.get("reachable", True):
                    result = {**item, "status": "skipped_unreachable"}
                    results.append(result)
                    print(f"[{index}/{len(items)}] skip unreachable {item.get('id')} {item.get('ip')}", flush=True)
                    continue

                print(f"[{index}/{len(items)}] open {item.get('id')} {item.get('ip')} {item.get('proto')} score={item.get('score')}", flush=True)
                try:
                    ready_url, clicked, body_text = generate_ready_url(page, item)
                    if not ready_url:
                        status = "unreachable" if REACHABILITY_WARNING in body_text else "no_ready_link"
                        result = {**item, "status": status, "clicked": clicked}
                        results.append(result)
                        print(f"[{index}/{len(items)}] {status} {item.get('id')} clicked={clicked}", flush=True)
                        continue

                    with download_page.expect_download(timeout=120000) as download_info:
                        try:
                            download_page.goto(ready_url, wait_until="commit", timeout=120000)
                        except Exception:
                            pass
                    download = download_info.value
                    safe_ip = str(item.get("ip") or item.get("host") or "unknown").replace(":", "-")
                    filename = f"publicvpnlist_{item.get('id')}_{safe_ip}_{item.get('port')}_{item.get('proto')}.ovpn"
                    save_path = unique_path(OUT_DIR / filename)
                    download.save_as(str(save_path))
                    text = save_path.read_text(encoding="utf-8", errors="ignore")
                    remote_match = re.search(r"^remote\s+(\S+)\s+(\S+)", text, re.MULTILINE)
                    ovpn_remote_host = remote_match.group(1) if remote_match else ""
                    ovpn_remote_port = remote_match.group(2) if remote_match else ""
                    expected_hosts = {str(item.get("ip") or ""), str(item.get("host") or "")}
                    expected_port = str(item.get("port") or "")
                    remote_ok = ovpn_remote_host in expected_hosts and (not expected_port or ovpn_remote_port == expected_port)
                    common_fields = {
                        "ready_url": ready_url,
                        "clicked": clicked,
                        "suggested_filename": download.suggested_filename,
                        "saved_path": str(save_path),
                        "bytes": save_path.stat().st_size,
                        "ovpn_remote_host": ovpn_remote_host,
                        "ovpn_remote_port": ovpn_remote_port,
                        "remote_matches_item": remote_ok,
                    }
                    if not manager.looks_like_openvpn_config(text):
                        result = {**item, **common_fields, "status": "downloaded_not_ovpn"}
                        results.append(result)
                        print(f"[{index}/{len(items)}] downloaded_not_ovpn {item.get('id')} -> {save_path}", flush=True)
                        continue
                    if not remote_ok:
                        result = {**item, **common_fields, "status": "downloaded_remote_mismatch"}
                        results.append(result)
                        print(f"[{index}/{len(items)}] remote_mismatch {item.get('id')} expected={item.get('ip')}:{item.get('port')} got={ovpn_remote_host}:{ovpn_remote_port}", flush=True)
                        continue

                    result = {**item, **common_fields, "status": "downloaded"}
                    results.append(result)
                    successes.append(result)
                    print(f"[{index}/{len(items)}] downloaded {item.get('id')} {item.get('ip')} -> {save_path}", flush=True)
                except Exception as exc:
                    result = {**item, "status": "error", "error": str(exc)}
                    results.append(result)
                    print(f"[{index}/{len(items)}] error {item.get('id')} {item.get('ip')}: {exc}", flush=True)
        finally:
            download_page.close()
            page.close()
            browser.close()

    payload = {"country_url": COUNTRY_URL, "total": len(items), "downloaded": len(successes), "results": results}
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fp:
        fieldnames = ["status", "id", "ip", "host", "country", "country_name", "proto", "port", "speed", "latency", "score", "saved_path", "bytes", "ovpn_remote_host", "ovpn_remote_port", "remote_matches_item", "ready_url"]
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"[PublicVPNList batch] downloaded={len(successes)}/{len(items)} json={JSON_OUT} csv={CSV_OUT}", flush=True)
    return 0 if successes else 1


if __name__ == "__main__":
    raise SystemExit(main())
