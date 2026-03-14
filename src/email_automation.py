"""
Browser automation for creating M365 email accounts via GoDaddy Email & Office.
Uses Playwright to drive the web UI since GoDaddy has no API for this.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import logging

log = logging.getLogger("automation")

_LOGS_DIR = str(Path(__file__).parent.parent / "logs")


class GoDaddyEmailBot:
    """Automates GoDaddy Email & Office email account creation."""

    def __init__(self, email: str, password: str, account_idx: int = 0, headless: bool = True):
        self.email = email
        self.password = password
        self.account_idx = account_idx
        self.headless = headless
        self._pw = None
        self._context = None
        self._page = None

    def open(self):
        """Launch browser using real Chrome with a per-account persistent profile."""
        profile_dir = str(Path(__file__).parent.parent / "browser_data" / f"account_{self.account_idx + 1}")
        self._pw = sync_playwright().start()
        self._context = self._pw.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=self.headless,
            channel="chrome",
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            no_viewport=True,
        )
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        log.info(f"Browser launched (Chrome, profile: account_{self.account_idx + 1})")

    def _dismiss_popups(self):
        """Dismiss any modals/popups/recommendation overlays that appear."""
        page = self._page
        dismissed = False

        # Run up to 3 rounds to catch stacked popups
        for _ in range(3):
            found = False

            # JS approach: find any visible modal/dialog close buttons
            try:
                found = page.evaluate("""() => {
                    // Look for X/close buttons inside modals/dialogs
                    const candidates = document.querySelectorAll(
                        '[class*="modal"] button, [class*="dialog"] button, ' +
                        '[role="dialog"] button, [class*="overlay"] button, ' +
                        'button[aria-label*="lose"], button[aria-label*="ismiss"], ' +
                        'button[class*="close"], [class*="close-btn"]'
                    );
                    for (const el of candidates) {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            el.click();
                            return true;
                        }
                    }
                    // Look for Cancel text inside modals
                    const all = document.querySelectorAll('[class*="modal"] a, [role="dialog"] a, [role="dialog"] button');
                    for (const el of all) {
                        if (el.textContent.trim() === 'Cancel') {
                            el.click();
                            return true;
                        }
                    }
                    return false;
                }""")
            except Exception:
                found = False

            if found:
                page.wait_for_timeout(1000)
                dismissed = True
                log.debug("Dismissed popup via JS")
                continue

            # Playwright selectors as fallback
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
                'button:has-text("Cancel")',
                'button:has-text("×")',
                'button:has-text("✕")',
                '[class*="close"][role="button"]',
                'svg[data-testid="CloseIcon"]',
            ]
            for selector in close_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=500):
                        btn.click()
                        log.debug(f"Dismissed popup via: {selector}")
                        page.wait_for_timeout(1000)
                        found = True
                        dismissed = True
                        break
                except Exception:
                    continue

            if not found:
                break  # No more popups

        return dismissed

    def _do_sso_login(self):
        """Perform the full SSO login flow (username → password → redirect)."""
        page = self._page
        log.info("Logging in via SSO...")

        # Make sure we're on the SSO page
        if "sso.godaddy.com" not in page.url:
            page.goto("https://sso.godaddy.com/login?realm=idp&app=productivity&path=%2F")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)

        self._dismiss_popups()

        # Email/username input
        username_input = page.locator('#username, input[name="username"], input[type="email"]').first
        username_input.wait_for(state="visible", timeout=15000)
        username_input.fill(self.email)
        log.debug("Filled username")

        submit_btn = page.locator('button[type="submit"], button:has-text("Next"), button:has-text("Sign in"), [data-testid="submit"]').first
        submit_btn.click()
        page.wait_for_timeout(3000)

        # Password input
        password_input = page.locator('#password, input[name="password"], input[type="password"]').first
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(self.password)
        log.debug("Filled password")

        submit_btn = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Next"), [data-testid="submit"]').first
        submit_btn.click()

        page.wait_for_timeout(5000)
        current_url = page.url
        log.debug(f"After login, URL: {current_url}")

        if "productivity.godaddy.com" not in current_url:
            page.wait_for_timeout(10000)

        log.info("SSO login complete")
        self._dismiss_popups()

    def _ensure_logged_in(self):
        """Check if we're on SSO and login if needed. Returns True if login was performed."""
        page = self._page
        if "sso.godaddy.com" in page.url:
            self._do_sso_login()
            return True
        return False

    def go_to_create_email(self, domain: str):
        """Follow the real manual flow to reach the Create New Email form.

        Step 1: Overview page → click "Set up accounts"
        Step 2: Choose account type → click "Get Started" under Microsoft 365 Email
        Step 3: Choose domain → type domain, click Continue
        Step 4: Lands on "Create multiple emails" → click "Create single email" tab
        """
        page = self._page

        # ── Step 1: Go to Overview ──
        page.goto("https://productivity.godaddy.com/#/")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)

        # Handle SSO redirect if session expired
        if self._ensure_logged_in():
            log.info("Was redirected to SSO — navigating back to Overview")
            page.goto("https://productivity.godaddy.com/#/")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(3000)
        else:
            log.info("Already logged in")

        self._dismiss_popups()
        page.wait_for_timeout(2000)

        # Click "Set up accounts"
        page.locator('text="Set up accounts"').first.click()
        page.wait_for_timeout(3000)
        log.info("Step 1: Clicked 'Set up accounts'")

        # ── Step 2: Choose account type → Microsoft 365 Email ──
        self._dismiss_popups()
        page.locator('text="Microsoft 365 Email"').first.wait_for(state="visible", timeout=15000)
        # Use JS to find the "Get Started" button inside the same card as "Microsoft 365 Email"
        clicked = page.evaluate("""() => {
            // Find the element containing "Microsoft 365 Email"
            const all = document.querySelectorAll('*');
            for (const el of all) {
                if (el.childNodes.length === 1 && el.textContent.trim() === 'Microsoft 365 Email') {
                    // Walk up to the card container and find its Get Started button
                    let card = el.closest('[class*="card"], [class*="panel"], section, article') || el.parentElement.parentElement;
                    const btn = card.querySelector('a, button');
                    if (btn && btn.textContent.includes('Get Started')) {
                        btn.click();
                        return true;
                    }
                }
            }
            return false;
        }""")
        if not clicked:
            # Fallback: click the first Get Started (M365 is on the left)
            page.locator('button:has-text("Get Started"), a:has-text("Get Started")').first.click()
        page.wait_for_timeout(3000)
        log.info("Step 2: Clicked 'Get Started' under Microsoft 365 Email")

        # ── Step 3: Choose domain → type domain, click Continue ──
        self._dismiss_popups()
        domain_input = page.locator('input[type="text"], input[placeholder*="domain"], input[placeholder*="business"]').first
        domain_input.wait_for(state="visible", timeout=15000)
        domain_input.clear()
        domain_input.fill(domain)
        page.wait_for_timeout(1000)
        page.locator('button:has-text("Continue")').first.click()
        page.wait_for_timeout(5000)
        log.info(f"Step 3: Entered domain '{domain}' and clicked Continue")

        # ── Step 4: Switch to "Create single email" tab ──
        self._dismiss_popups()
        page.wait_for_timeout(2000)

        tab_clicked = False
        for sel in [
            'text="Create single email"',
            'a:has-text("Create single email")',
            'button:has-text("Create single email")',
            '[role="tab"]:has-text("single")',
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=2000):
                    el.scroll_into_view_if_needed()
                    el.click(force=True)
                    page.wait_for_timeout(3000)
                    log.info(f"Step 4: Clicked 'Create single email' tab via: {sel}")
                    tab_clicked = True
                    break
            except Exception:
                continue

        if not tab_clicked:
            log.warning("Could not click 'Create single email' tab")
            try:
                page.screenshot(path=f"{_LOGS_DIR}/debug_tab.png")
            except Exception:
                pass

        # Wait for the form to fully render
        page.wait_for_timeout(3000)
        log.info(f"On email creation form for {domain}")

    def _find_expiration_dropdown(self):
        """Find the Renewal/Expiration date dropdown (custom component, not native <select>)."""
        page = self._page

        # Look for the dropdown by its label text "Renewal/Expiration date"
        # The dropdown trigger is typically a clickable div/button near that label
        for sel in [
            # Try to find a custom dropdown near the label
            'text="Renewal/Expiration date" >> .. >> [class*="select"]',
            'text="Renewal/Expiration date" >> .. >> [class*="dropdown"]',
            'text="Renewal/Expiration date" >> .. >> [role="listbox"]',
            'text="Renewal/Expiration date" >> .. >> [role="combobox"]',
        ]:
            try:
                el = page.locator(sel).first
                if el.is_visible(timeout=3000):
                    log.info(f"Found expiration dropdown via: {sel}")
                    return el
            except Exception:
                continue

        # Fallback: find by the visible text pattern like "December 6, 2026"
        # Click the element that contains the date text with "Available"
        try:
            el = page.locator('[class*="select"], [class*="dropdown"], [role="combobox"]').filter(
                has_text="Available"
            ).first
            if el.is_visible(timeout=3000):
                log.info("Found expiration dropdown via 'Available' text filter")
                return el
        except Exception:
            pass

        # Last resort: use JS to find the dropdown near the label
        try:
            page.screenshot(path=f"{_LOGS_DIR}/debug_expiration.png")
            log.info("Debug screenshot saved to debug_expiration.png")
        except Exception:
            pass
        raise RuntimeError("Could not find expiration date dropdown — check logs/debug_expiration.png")

    def get_expiration_dates(self) -> list[str]:
        """Scrape available expiration dates from the dropdown or static text."""
        page = self._page

        # Check if there's only one expiration date (no dropdown, just static text)
        try:
            label = page.locator('text="Renewal/Expiration date"').first
            if label.is_visible(timeout=3000):
                # Get the sibling/nearby text that contains the date
                parent = page.locator('text="Renewal/Expiration date" >> ..').first
                parent_text = parent.text_content().strip()
                # Extract the "Available" part
                if "Available" in parent_text:
                    # Remove the label text itself
                    date_text = parent_text.replace("Renewal/Expiration date", "").strip()
                    if date_text:
                        # Check if there's a dropdown — try finding one
                        try:
                            dropdown = self._find_expiration_dropdown()
                        except RuntimeError:
                            dropdown = None

                        if not dropdown:
                            # No dropdown — single value, return it directly
                            log.info(f"Single expiration date (no dropdown): {date_text}")
                            self._single_expiration = True
                            return [date_text]
        except Exception:
            pass

        self._single_expiration = False

        # Multiple dates — click the dropdown to open it
        dropdown = self._find_expiration_dropdown()
        dropdown.click()
        page.wait_for_timeout(2000)

        # Take a screenshot to see what options appeared
        try:
            page.screenshot(path=f"{_LOGS_DIR}/debug_expiration_open.png")
        except Exception:
            pass

        # Scrape options — filter to only those containing "Available" (expiration format)
        dates = []
        all_options = page.locator('[role="option"], [role="listbox"] [class*="option"], [class*="menu"] [class*="option"]').all()
        if not all_options:
            all_options = page.locator('[class*="dropdown"] li, [class*="menu"] li, [class*="select"] li').all()

        for opt in all_options:
            try:
                text = opt.text_content().strip()
                if text and "Available" in text:
                    dates.append(text)
            except Exception:
                continue

        # Close the dropdown
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

        log.info(f"Expiration dates: {dates}")
        if not dates:
            try:
                page.screenshot(path=f"{_LOGS_DIR}/debug_expiration_empty.png")
                log.info("Debug screenshot saved to debug_expiration_empty.png")
            except Exception:
                pass
            raise RuntimeError("Dropdown opened but no expiration options found — check logs/debug_expiration_open.png")
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

        # Expiration date dropdown — skip if only one option (no dropdown exists)
        if not getattr(self, '_single_expiration', False):
            dropdown = self._find_expiration_dropdown()
            dropdown.click()
            page.wait_for_timeout(2000)
            options = page.locator('[role="option"], [role="listbox"] [class*="option"], [class*="menu"] [class*="option"]').all()
            if not options:
                options = page.locator('[class*="dropdown"] li, [class*="menu"] li, [class*="select"] li').all()
            if 0 <= expiration_idx < len(options):
                options[expiration_idx].click()
                page.wait_for_timeout(1000)
            else:
                page.keyboard.press("Escape")
                log.warning(f"Expiration index {expiration_idx} out of range ({len(options)} options)")
        else:
            log.info("Single expiration date — skipping dropdown selection")

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
        """Click the Create button, then navigate back to Overview."""
        self._page.get_by_role("button", name="Create").click()
        self._page.wait_for_load_state("domcontentloaded")
        self._page.wait_for_timeout(5000)
        log.info("Create button clicked")

        # Go back to Overview so browser is ready for next email
        self._page.goto("https://productivity.godaddy.com/#/")
        self._page.wait_for_load_state("domcontentloaded")
        self._page.wait_for_timeout(3000)
        self._dismiss_popups()
        log.info("Navigated back to Overview")

    def close(self):
        """Clean up browser resources."""
        try:
            if self._context:
                self._context.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._page = None
        self._context = None
        self._pw = None
        log.info("Browser closed")
