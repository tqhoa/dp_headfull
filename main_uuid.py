"""
Tier 3 scraper: Playwright headless, chỉ để lấy FB numeric ID (userID/pageID) từ HTML.
"""

import re
from fastapi import FastAPI, HTTPException

app = FastAPI()

PATTERNS = [
    r'"userID":"(\d+)"',
    r'"entity_id":"(\d+)"',
    r'"profile_id":"(\d+)"',
    r'"pageID":"(\d+)"',
    r'"post_id":"(\d+)"',
    r'"top_level_post_id":"(\d+)"',
    r'"story_fbid":\["?(\d+)"?\]',
    r'"video_id":"(\d+)"',
    r"fb://profile/(\d+)",
    r"fb://page/(\d+)",
]

POST_ID_PATTERNS = [
    r'"post_id":"(\d+)"',
    r'"top_level_post_id":"(\d+)"',
    r'"story_fbid":\["?(\d+)"?\]',
    r'"video_id":"(\d+)"',
]


def _get_async_playwright():
    try:
        from playwright.async_api import async_playwright

        return async_playwright
    except Exception:
        return None


async def _scrape_via_playwright(url: str, patterns: list[str]) -> str | None:
    async_playwright = _get_async_playwright()
    if not async_playwright:
        print(f"Playwright not available")
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                # Block heavy resources
                await page.route(
                    "**/*.{png,jpg,jpeg,css,woff2,svg,gif}",
                    lambda route: route.abort(),
                )
                # Post/video/reel/story data loads via GraphQL/XHR after DOM ready; needs networkidle.
                NEEDS_NETWORKIDLE = ("/reel/", "/videos/", "/watch", "/permalink.php", "/story.php", "story_fbid")
                wait_until = "networkidle" if any(k in url for k in NEEDS_NETWORKIDLE) else "domcontentloaded"
                await page.goto(url, wait_until=wait_until, timeout=30000)

                html = await page.content()

                for pattern in patterns:
                    m = re.search(pattern, html, re.S)
                    if m and m.group(1) != "0":
                        return m.group(1)
                return None
            finally:
                await browser.close()
    except Exception as e:
        print(f"[-] Playwright browser error: {e}")
        return None


async def get_uuid_via_playwright(url: str) -> str | None:
    return await _scrape_via_playwright(url, PATTERNS)


async def get_post_id_via_playwright(url: str) -> str | None:
    return await _scrape_via_playwright(url, POST_ID_PATTERNS)


@app.get("/get_uuid")
async def get_uuid(url: str):
    uid = await get_uuid_via_playwright(url)
    if not uid:
        raise HTTPException(status_code=404, detail="UUID not found")
    return {"url": url, "uuid": uid}


@app.get("/get_post_id")
async def get_post_id(url: str):
    pid = await get_post_id_via_playwright(url)
    if not pid:
        raise HTTPException(status_code=404, detail="post_id not found")
    return {"url": url, "post_id": pid}


@app.get("/health")
def health():
    return {"status": "ok"}
