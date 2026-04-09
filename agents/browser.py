from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
import time

class Browser:
    def __init__(self, headless=False, use_profile=True):
        self.headless = headless
        self.use_profile = use_profile
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        self._playwright = sync_playwright().start()

        if self.use_profile:
            # use your actual Chrome profile — you're already logged into everything
            # find your profile path: chrome://version → Profile Path
            self._browser = self._playwright.chromium.launch_persistent_context(
                user_data_dir="C:/Users/YOUR_USERNAME/AppData/Local/Google/Chrome/User Data",
                channel="chrome",
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def navigate(self, url: str) -> str:
        self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(1)
        return self.get_page_text()

    def get_page_text(self) -> str:
        html = self._page.content()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:8000]  # cap at 8k chars

    def click(self, selector: str):
        self._page.click(selector)
        time.sleep(0.5)

    def fill(self, selector: str, value: str):
        self._page.fill(selector, value)

    def search_google(self, query: str) -> list[dict]:
        self._page.goto(f"https://www.google.com/search?q={query}")
        time.sleep(1)
        results = []
        links = self._page.query_selector_all("a[href]")
        for link in links[:10]:
            href = link.get_attribute("href")
            text = link.inner_text()
            if href and href.startswith("http") and "google" not in href:
                results.append({"url": href, "title": text})
        return results[:5]

    def deep_research(self, topic: str, pages: int = 3) -> str:
        """Search a topic, visit top results, synthesize content."""
        results = self.search_google(topic)
        all_content = []
        for result in results[:pages]:
            try:
                content = self.navigate(result["url"])
                all_content.append(f"Source: {result['url']}\n{content}")
            except Exception:
                continue
        return "\n\n---\n\n".join(all_content)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()