"""
Browser automation for creating M365 email accounts via GoDaddy Email & Office.
Uses Playwright to drive the web UI since GoDaddy has no API for this.
"""

from playwright.sync_api import sync_playwright
import logging

log = logging.getLogger("automation")


class GoDaddyEmailBot:
    """Automates GoDaddy Email & Office email account creation."""

    def __init__(self, email: str, password: str, headless: bool = True):
        self.email = email
        self.password = password
        self.headless = headless
        self._pw = None
        self._browser = None
        self._page = None

    def open(self):
        """Launch browser using the real installed Chrome (not Playwright's Chromium)."""
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self.headless,
            channel="chrome",
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        )
        self._page = self._browser.new_page(no_viewport=True)
        log.info("Browser launched (Chrome)")

    def _dismiss_popups(self):
        """Dismiss any modals/popups/recommendation overlays that appear."""
        page = self._page
        # Try common close/dismiss button patterns
        close_selectors = [
            'button[aria-label="Close"]',
            'button[aria-label="close"]',
            'button[aria-label="Dismiss"]',
            '[data-testid="close-button"]',
            '.modal button.close',
            'button:has-text("No thanks")',
            'button:has-text("Not now")',
            'button:has-text("Maybe later")',
            'button:has-text("Skip")',
            'button:has-text("Got it")',
            'button:has-text("Dismiss")',
            '[class*="close"][role="button"]',
            '[class*="dismiss"]',
            'svg[data-testid="CloseIcon"]',
        ]
        for selector in close_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=500):
                    btn.click()
                    log.debug(f"Dismissed popup via: {selector}")
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue

        # Also try clicking any visible X button (common pattern: button with just "X" or "×")
        try:
            x_btn = page.locator('button:has-text("×"), button:has-text("✕")').first
            if x_btn.is_visible(timeout=500):
                x_btn.click()
                log.debug("Dismissed popup via X button")
                page.wait_for_timeout(1000)
                return True
        except Exception:
            pass

        return False

    def login(self):
        """Log in to GoDaddy SSO."""
        page = self._page
        page.goto("https://sso.godaddy.com/login?realm=idp&app=productivity&path=%2F")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Dismiss any popups on the login page
        self._dismiss_popups()

        # Email/username input — try multiple selectors
        username_input = page.locator('#username, input[name="username"], input[type="email"]').first
        username_input.wait_for(state="visible", timeout=15000)
        username_input.fill(self.email)
        log.debug("Filled username")

        # Click next/submit — try multiple selectors
        submit_btn = page.locator('button[type="submit"], button:has-text("Next"), button:has-text("Sign in"), [data-testid="submit"]').first
        submit_btn.click()
        page.wait_for_timeout(3000)

        # Password input
        password_input = page.locator('#password, input[name="password"], input[type="password"]').first
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(self.password)
        log.debug("Filled password")

        # Click sign in
        submit_btn = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Next"), [data-testid="submit"]').first
        submit_btn.click()

        # Wait for redirect — be flexible about the URL
        page.wait_for_timeout(5000)
        # Check if we landed on productivity or are still on SSO
        current_url = page.url
        log.debug(f"After login, URL: {current_url}")

        if "productivity.godaddy.com" not in current_url:
            # Maybe there's an interstitial page, try waiting longer
            page.wait_for_timeout(10000)
            current_url = page.url
            log.debug(f"After extra wait, URL: {current_url}")

        if "productivity.godaddy.com" not in current_url:
            # Try navigating directly
            page.goto("https://productivity.godaddy.com/#/")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

        log.info("Logged in to GoDaddy")

        # Dismiss any post-login popups/recommendations
        self._dismiss_popups()

    def go_to_create_email(self, domain: str):
        """Navigate directly to the Create New Email form for a domain."""
        url = (
            f"https://productivity.godaddy.com/#/addnewemail"
            f"?domain={domain}&mailboxType=officeEmail&selectedAddons="
        )
        self._page.goto(url)
        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(3000)

        # Dismiss any popups that appear on this page
        self._dismiss_popups()

        # Default landing is "Create multiple emails" — switch to single
        page = self._page
        tab_clicked = False
        tab_selectors = [
            'a:has-text("Create single email")',
            'button:has-text("Create single email")',
            '[role="tab"]:has-text("Create single email")',
            'li:has-text("Create single email")',
            'span:has-text("Create single email")',
            'div[role="tab"]:has-text("Create single email")',
        ]
        for sel in tab_selectors:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    el.click()
                    page.wait_for_timeout(2000)
                    log.info(f"Clicked 'Create single email' tab via: {sel}")
                    tab_clicked = True
                    break
            except Exception:
                continue

        if not tab_clicked:
            # Last resort: click by exact text match
            try:
                page.locator("text=Create single email").first.click()
                page.wait_for_timeout(2000)
                log.info("Clicked 'Create single email' tab via text= selector")
            except Exception as e:
                log.warning(f"Could not click 'Create single email' tab: {e}")

        # Dismiss any popups that appeared after tab switch
        self._dismiss_popups()

        log.info(f"On email creation form for {domain}")

    def get_expiration_dates(self) -> list[str]:
        """Scrape available expiration dates from the dropdown."""
        page = self._page
        select = page.locator('select')
        select.wait_for(state="visible", timeout=15000)
        options = select.locator('option').all()
        dates = []
        for opt in options:
            text = opt.text_content().strip()
            if text:
                dates.append(text)
        log.info(f"Expiration dates: {dates}")
        return dates

    def fill_form(self, username: str, first_name: str, last_name: str,
                  admin: bool, expiration_idx: int, password: str, notify_email: str):
        """Fill in all fields on the Create New Email form."""
        page = self._page

        # Username (email prefix before @domain.com)
        page.get_by_label("Username").fill(username)

        # First name / Last name
        page.get_by_label("First name").fill(first_name)
        page.get_by_label("Last name").fill(last_name)

        # Expiration date dropdown
        select = page.locator('select')
        options = select.locator('option').all()
        if 0 <= expiration_idx < len(options):
            value = options[expiration_idx].get_attribute('value')
            if value:
                select.select_option(value=value)
            else:
                select.select_option(index=expiration_idx)

        # Administrator permissions (radio buttons)
        if admin:
            page.get_by_label("Yes").click()
        else:
            page.get_by_label("No").click()

        # Password
        page.get_by_label("Create a password").fill(password)

        # Send account info to
        notify_field = page.get_by_label("Send account info to")
        notify_field.clear()
        notify_field.fill(notify_email)

        log.info(f"Form filled: {username}@..., {first_name} {last_name}")

    def screenshot(self, path: str) -> str:
        """Take a screenshot of the current page."""
        self._page.screenshot(path=path, full_page=True)
        log.info(f"Screenshot saved: {path}")
        return path

    def submit(self):
        """Click the Create button to submit the form."""
        self._page.get_by_role("button", name="Create").click()
        self._page.wait_for_load_state("networkidle")
        self._page.wait_for_timeout(5000)
        log.info("Create button clicked")

    def close(self):
        """Clean up browser resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page = None
        self._browser = None
        self._pw = None
        log.info("Browser closed")
