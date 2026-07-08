"""
Tier 2 scraper: DrissionPage headful (qua Xvfb) trong container.
Dùng khi requests_go bị chặn bởi JS challenge / Turnstile.
"""

import time
from fastapi import FastAPI, HTTPException
from DrissionPage import ChromiumPage, ChromiumOptions

app = FastAPI()


def make_options() -> ChromiumOptions:
    options = ChromiumOptions()
    options.set_paths(browser_path="/usr/bin/google-chrome")

    # QUAN TRỌNG: không bật headless(True) — Cloudflare check headless rất gắt.
    # Ta chạy "headful" thật nhưng bên trong Xvfb (ảo) nên không cần GUI thật.
    options.headless(False)

    # Các cờ giảm dấu hiệu automation
    args = [
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
        "--start-maximized",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--password-store=basic",
        "--use-mock-keychain",
        "--disable-background-mode",
        "--disable-dev-shm-usage",  # dùng /tmp thay vì /dev/shm nhỏ trong container
        "--no-sandbox",  # cần thiết khi chạy trong container không có user namespace đầy đủ
    ]
    for a in args:
        options.set_argument(a)

    return options


def bypass_turnstile(page: ChromiumPage, timeout: int = 15) -> bool:
    """Click vào Cloudflare Turnstile checkbox nếu xuất hiện."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if page.ele("#turnstile-wrapper", timeout=1):
                page.ele("#turnstile-wrapper").click()
                time.sleep(2)
                # Kiểm tra đã pass chưa (title/content đổi)
                if "just a moment" not in page.title.lower():
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


@app.get("/fetch")
def fetch(url: str):
    options = make_options()
    page = ChromiumPage(addr_or_opts=options)
    try:
        page.get(url)

        # Nếu gặp Cloudflare interstitial thì thử bypass
        if (
            "just a moment" in page.title.lower()
            or "checking your browser" in page.html.lower()
        ):
            ok = bypass_turnstile(page)
            if not ok:
                raise HTTPException(status_code=502, detail="Cloudflare bypass failed")

        return {
            "status": "ok",
            "title": page.title,
            "html": page.html,
        }
    finally:
        page.quit()


@app.get("/health")
def health():
    return {"status": "ok"}
