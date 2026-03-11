import time
import random
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright_stealth import Stealth

ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    {"source_id": 1, "url": "https://www.ahajournals.org/doi/10.1161/HYP.0000000000000238", "file": "HYP.0000000000000238.html"},
    {"source_id": 2, "url": "https://www.ahajournals.org/doi/10.1161/CIRCRESAHA.121.318083", "file": "CIRCRESAHA.121.318083.html"},
    {"source_id": 3, "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341", "file": "CIR.0000000000001341.html"},
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:70.0) Gecko/20100101 Firefox/70.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 "
    "Edg/122.0.100.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36 OPR/"
    "65.0.3467.48",
]


def human_like_interaction(page):
    page.mouse.move(100, 100)
    time.sleep(random.uniform(0.5, 1.5))
    page.mouse.move(200, 300)
    time.sleep(random.uniform(0.5, 1.5))
    page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
    time.sleep(random.uniform(1, 2))


def download_html(url, out_path: Path, storage_state_path: Path, headed=True):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    storage_state_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and out_path.stat().st_size > 20_000:
        print(f"[CACHE] {out_path.name}")
        return

    with Stealth().use_sync(sync_playwright()) as p:
        user_agent = random.choice(USER_AGENTS)
        browser = p.chromium.launch(headless=not headed)

        context_kwargs = {
            "viewport": {"width": 1365, "height": 768},
            "java_script_enabled": True,
            "user_agent": user_agent,
        }
        if storage_state_path.exists():
            context_kwargs["storage_state"] = str(storage_state_path)

        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        page.set_default_timeout(60_000)

        try:
            page.goto(url, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=60_000)
            except PWTimeoutError:
                time.sleep(3)

            human_like_interaction(page)

            html = page.content()
            out_path.write_text(html, encoding="utf-8")

            # SAVE COOKIE FILES
            context.storage_state(path=str(storage_state_path))

        finally:
            page.close()
            context.close()
            browser.close()


def main(headed: bool = True) -> None:
    out_dir = ROOT / "data" / "raw" / "scraped"
    storage_state = ROOT / "data" / "storage_state.json"

    for src in SOURCES:
        out_path = out_dir / src["file"]
        print(f"[GET] {src['url']} -> {out_path}")
        download_html(src["url"], out_path, storage_state, headed=headed)
        print(f"[OK] saved {out_path.name} ({out_path.stat().st_size} bytes)")


def scrape_website_data(headed: bool = True) -> None:
    main(headed=headed)


if __name__ == "__main__":
    main(headed=True)