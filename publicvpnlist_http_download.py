from __future__ import annotations

import csv
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

os.environ.setdefault("PUBLICVPNLIST_AUTO_COUNTRIES", "0")
os.environ.setdefault("PUBLICVPNLIST_MAX_DOWNLOADS", "0")

import vpngate_manager as manager

COUNTRY_URL = os.environ.get("PUBLICVPNLIST_HTTP_BATCH_URL", "https://publicvpnlist.com/country/vietnam/")
OUT_DIR = Path(os.environ.get("PUBLICVPNLIST_HTTP_BATCH_DIR", "publicvpnlist_http_downloads_vietnam")).resolve()
JSON_OUT = Path(os.environ.get("PUBLICVPNLIST_HTTP_BATCH_JSON", "publicvpnlist_http_vietnam_downloads.json")).resolve()
CSV_OUT = Path(os.environ.get("PUBLICVPNLIST_HTTP_BATCH_CSV", "publicvpnlist_http_vietnam_downloads.csv")).resolve()
MAX_DOWNLOADS = int(os.environ.get("PUBLICVPNLIST_HTTP_BATCH_MAX", "0") or "0")
PER_COUNTRY_LIMIT = int(os.environ.get("PUBLICVPNLIST_PER_COUNTRY_LIMIT", "20") or "0")
BASE_URL = "https://publicvpnlist.com/"
USER_AGENT = os.environ.get(
    "PUBLICVPNLIST_HTTP_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
)


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


def build_opener() -> urllib.request.OpenerDirector:
    cookie_jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def http_get(opener: urllib.request.OpenerDirector, url: str, accept: str, referer: str = "") -> tuple[int, str, bytes]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
    }
    if referer:
        headers["Referer"] = referer
        headers["X-Requested-With"] = "XMLHttpRequest"
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=120) as response:
        return response.status, response.headers.get("content-type", ""), response.read()


def fetch_json(opener: urllib.request.OpenerDirector, url: str, referer: str) -> tuple[int, dict[str, object]]:
    status, _content_type, body = http_get(opener, url, "application/json,text/plain,*/*", referer)
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except Exception:
        data = {"ok": False, "error": body.decode("utf-8", errors="replace")[:200]}
    return status, data if isinstance(data, dict) else {"ok": False, "error": "JSON root is not an object"}


def download_item(item: dict[str, object], out_dir: Path) -> dict[str, object]:
    cfg_id = str(item.get("id") or "").strip()
    page_url = str(item.get("download_url") or urllib.parse.urljoin(COUNTRY_URL, f"/download/{cfg_id}/"))
    opener = build_opener()
    result: dict[str, object] = {**item, "method": "http"}

    try:
        http_get(opener, page_url, "text/html,*/*")
    except Exception as exc:
        return {**result, "status": "detail_page_error", "error": str(exc)}

    cache_buster = str(int(time.time() * 1000))
    test_url = urllib.parse.urljoin(BASE_URL, f"test_server.php?id={urllib.parse.quote(cfg_id)}&_={cache_buster}")
    try:
        test_status, test_data = fetch_json(opener, test_url, page_url)
    except Exception as exc:
        return {**result, "status": "live_test_error", "error": str(exc)}

    live_status = str(test_data.get("status") or "")
    if test_status != 200 or not test_data.get("ok") or live_status != "ok":
        return {
            **result,
            "status": "unreachable",
            "live_test_http_status": test_status,
            "live_test_status": live_status or "unknown",
            "live_test_error": str(test_data.get("error") or test_data.get("message") or ""),
        }

    token_url = urllib.parse.urljoin(BASE_URL, f"get_token.php?id={urllib.parse.quote(cfg_id)}&_={int(time.time() * 1000)}")
    try:
        token_status, token_data = fetch_json(opener, token_url, page_url)
    except Exception as exc:
        return {**result, "status": "token_error", "error": str(exc)}

    dl_value = str(token_data.get("url") or "").strip()
    if not dl_value and token_data.get("token"):
        dl_value = "download.php?token=" + urllib.parse.quote(str(token_data.get("token") or ""))
    if token_status != 200 or not dl_value:
        return {
            **result,
            "status": "token_error",
            "token_http_status": token_status,
            "token_error": str(token_data.get("error") or token_data.get("message") or ""),
        }

    download_url = urllib.parse.urljoin(BASE_URL, dl_value)
    try:
        download_status, content_type, content = http_get(
            opener,
            download_url,
            "application/x-openvpn-profile,text/plain,*/*",
            page_url,
        )
    except Exception as exc:
        return {**result, "status": "download_error", "error": str(exc)}

    safe_ip = str(item.get("ip") or item.get("host") or "unknown").replace(":", "-")
    filename = f"publicvpnlist_http_{cfg_id}_{safe_ip}_{item.get('port')}_{item.get('proto')}.ovpn"
    save_path = unique_path(out_dir / filename)
    save_path.write_bytes(content)
    text = content.decode("utf-8", errors="replace")
    remote_host, remote_port, remote_proto = manager.extract_ovpn_remote(text)
    ok, reason = manager.publicvpnlist_config_matches_item(item, text)
    common = {
        "download_http_status": download_status,
        "download_content_type": content_type,
        "saved_path": str(save_path),
        "bytes": save_path.stat().st_size,
        "ovpn_remote_host": remote_host,
        "ovpn_remote_port": remote_port,
        "ovpn_remote_proto": remote_proto,
        "remote_matches_item": ok,
    }
    if not manager.looks_like_openvpn_config(text):
        return {**result, **common, "status": "downloaded_not_ovpn"}
    if not ok:
        return {**result, **common, "status": "downloaded_remote_mismatch", "mismatch_reason": reason}
    return {**result, **common, "status": "downloaded"}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    page_text = manager.fetch_publicvpnlist_page_html(COUNTRY_URL)
    items = manager.extract_publicvpnlist_items(COUNTRY_URL, page_text)
    total_items = len(items)
    if PER_COUNTRY_LIMIT > 0:
        items = items[:PER_COUNTRY_LIMIT]
    if MAX_DOWNLOADS > 0:
        items = items[:MAX_DOWNLOADS]

    results: list[dict[str, object]] = []
    successes: list[dict[str, object]] = []
    print(
        f"[PublicVPNList HTTP] {COUNTRY_URL} parsed={total_items} selected={len(items)} "
        f"per_country_limit={PER_COUNTRY_LIMIT or 'all'} max={MAX_DOWNLOADS or 'all'}",
        flush=True,
    )
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] http {item.get('id')} {item.get('ip')} {item.get('proto')} speed={item.get('speed')} latency={item.get('latency')}", flush=True)
        row = download_item(item, OUT_DIR)
        results.append(row)
        if row.get("status") == "downloaded":
            successes.append(row)
            print(f"[{index}/{len(items)}] downloaded {item.get('id')} {item.get('ip')} -> {row.get('saved_path')}", flush=True)
        else:
            print(f"[{index}/{len(items)}] {row.get('status')} {item.get('id')} {item.get('ip')}", flush=True)

    payload = {"country_url": COUNTRY_URL, "method": "http", "total": len(items), "downloaded": len(successes), "results": results}
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fp:
        fieldnames = [
            "status",
            "method",
            "id",
            "ip",
            "host",
            "country",
            "country_name",
            "proto",
            "port",
            "speed",
            "latency",
            "score",
            "saved_path",
            "bytes",
            "ovpn_remote_host",
            "ovpn_remote_port",
            "ovpn_remote_proto",
            "remote_matches_item",
            "live_test_status",
        ]
        writer = csv.DictWriter(fp, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print(f"[PublicVPNList HTTP] downloaded={len(successes)}/{len(items)} json={JSON_OUT} csv={CSV_OUT}", flush=True)
    return 0 if successes else 1


if __name__ == "__main__":
    raise SystemExit(main())
