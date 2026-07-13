"""Browser-based collection for JavaScript-rendered roster pages."""

from dataclasses import dataclass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


@dataclass
class RenderedPage:
    """Content collected from a rendered webpage."""

    html: str
    visible_text: str


def fetch_rendered_page(url: str) -> RenderedPage:
    """Load a webpage in Chromium and return HTML plus visible text."""

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200,
            }
        )

        try:
            page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45_000,
            )

        except PlaywrightTimeoutError:
            print(
                "Navigation timed out, but attempting to "
                "read the partially loaded page."
            )

        # Allow roster components a little time to render.
        page.wait_for_timeout(5_000)

        rendered_page = RenderedPage(
            html=page.content(),
            visible_text=page.locator("body").inner_text(
                timeout=10_000,
            ),
        )

        browser.close()

    return rendered_page