from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://publicvpnlist.com/download/59075/"
PREFERRED_DETAIL_BUTTONS = (
    ("#downloadCurrentCheckBtn", "Run current check"),
    ("#dlStart", "Generate .ovpn link"),
)


def snapshot(page, label: str) -> dict[str, object]:
    page.wait_for_timeout(1500)
    buttons = page.locator("button, a, input[type=button], input[type=submit]")
    button_data = []
    for index in range(buttons.count()):
        handle = buttons.nth(index)
        try:
            text = (handle.inner_text() or handle.get_attribute("value") or "").strip()
        except Exception:
            text = ""
        try:
            href = handle.get_attribute("href")
        except Exception:
            href = None
        try:
            disabled = handle.is_disabled()
        except Exception:
            disabled = None
        button_data.append(
            {
                "text": text,
                "href": href,
                "disabled": disabled,
                "id": handle.get_attribute("id"),
                "class": handle.get_attribute("class"),
            }
        )

    ready_link = page.locator("#dlReadyLink")
    ready = None
    if ready_link.count():
        try:
            ready = {
                "text": ready_link.first.inner_text().strip(),
                "href": ready_link.first.get_attribute("href"),
                "disabled": ready_link.first.is_disabled() if ready_link.first.evaluate("el => 'disabled' in el") else None,
            }
        except Exception:
            ready = None

    body_text = page.locator("body").inner_text()
    return {
        "label": label,
        "url": page.url,
        "title": page.title(),
        "ready_link": ready,
        "buttons": button_data,
        "body_contains": {
            "server_selected": "Step 1 of 3 - Server selected" in body_text,
            "current_check": "Run current check" in body_text,
            "generate_link": "Generate .ovpn link" in body_text,
            "download_file": "Download .ovpn file" in body_text,
            "reachable_warning": "We could not confirm that this server is currently reachable" in body_text,
            "temporary_ready": "Temporary link is ready" in body_text,
        },
    }


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


def try_generate_download(page, trace: list[dict[str, object]]) -> str:
    for selector, label in PREFERRED_DETAIL_BUTTONS:
        if click_detail_button(page, selector):
            trace.append(snapshot(page, f"after_{label.lower().replace(' ', '_').replace('.', '_')}"))
        else:
            trace.append({"label": f"missing_{label.lower().replace(' ', '_').replace('.', '_')}", "url": page.url})

    ready = page.locator("#dlReadyLink")
    if ready.count():
        try:
            href = ready.first.get_attribute("href") or ""
            if href and href != "#":
                ready_url = urljoin(page.url, href)
                trace.append({"label": "ready_download_url", "url": ready_url, "href": href})
                return ready_url
        except Exception:
            pass
    return ""


def main() -> int:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("publicvpnlist_capture.json")
    target_url = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_URL
    save_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("publicvpnlist_downloads")
    save_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1200})
        trace: list[dict[str, object]] = []
        page.goto(target_url, wait_until="domcontentloaded", timeout=120000)
        trace.append(snapshot(page, "initial"))

        ready_url = try_generate_download(page, trace)
        if ready_url:
            download_page = browser.new_page(viewport={"width": 1440, "height": 1200})
            try:
                with download_page.expect_download(timeout=120000) as download_info:
                    try:
                        download_page.goto(ready_url, wait_until="commit", timeout=120000)
                    except Exception:
                        pass
                download = download_info.value
                download_path = save_dir / download.suggested_filename
                download.save_as(str(download_path))
                trace.append({
                    "label": "download_file",
                    "suggested_filename": download.suggested_filename,
                    "saved_path": str(download_path),
                    "url": ready_url,
                })
            except Exception as exc:
                trace.append({
                    "label": "download_failed",
                    "url": ready_url,
                    "error": str(exc),
                })
            finally:
                download_page.close()

        trace.append(snapshot(page, "final"))
        browser.close()

    out_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
