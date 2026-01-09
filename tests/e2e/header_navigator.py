from typing import List

from playwright.sync_api import Locator, Page


class HeaderNavigator:
    """Helper to interact with the unified dashboard header navigation bar."""

    NAV_CONTAINER = ".navbar-nav.me-auto"
    NAV_LINKS_SELECTOR = f"{NAV_CONTAINER} .nav-link"

    def __init__(self, page: Page):
        self.page = page
        self._wait_for_nav()

    def _wait_for_nav(self) -> None:
        self.page.wait_for_selector(self.NAV_CONTAINER, timeout=5000)

    def _nav_links(self) -> Locator:
        self._wait_for_nav()
        return self.page.locator(self.NAV_LINKS_SELECTOR)

    def labels(self) -> List[str]:
        nav_links = self._nav_links()
        count = nav_links.count()
        return [
            nav_links.nth(idx).inner_text(timeout=2000).strip() for idx in range(count)
        ]

    def get_link(self, label: str) -> Locator:
        nav_links = self._nav_links()
        total = nav_links.count()
        for idx in range(total):
            if nav_links.nth(idx).inner_text(timeout=2000).strip() == label:
                return nav_links.nth(idx)
        raise ValueError(f"Navigation link '{label}' not found in header")

    def click(self, label: str) -> None:
        self.get_link(label).click()
