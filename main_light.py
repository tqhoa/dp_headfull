"""
Tier 1 scraper: requests_go với TLS/JA3 fingerprint giả Chrome thật.
Nhẹ, nhanh, dùng trước — chỉ fallback sang tier 2 (DrissionPage) khi bị 403/challenge.
"""

import requests_go as requests
from requests_go.tls_config import TLS_CHROME_LATEST
from fastapi import FastAPI

app = FastAPI()

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}


@app.get("/fetch")
def fetch(url: str):
    session = requests.Session()
    session.tls_config = TLS_CHROME_LATEST  # khớp JA3 với User-Agent Chrome 131 ở trên

    resp = session.get(url, headers=HEADERS, timeout=15)

    is_blocked = resp.status_code in (403, 503) or "just a moment" in resp.text.lower()

    return {
        "status_code": resp.status_code,
        "blocked": is_blocked,
        "html": resp.text if not is_blocked else None,
        # Client dùng field "blocked" để quyết định gọi sang tier 2 (scraper-heavy)
    }


@app.get("/health")
def health():
    return {"status": "ok"}
