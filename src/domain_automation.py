"""
Browser automation for purchasing domains via GoDaddy's website.
Uses Playwright to drive the web UI since GoDaddy API keys are not available.
"""

from playwright.sync_api import sync_playwright
from pathlib import Path
import logging

log = logging.getLogger("automation")

_LOGS_DIR = str(Path(__file__).parent.parent / "logs")


class GoDaddyDomainBot:
    """Automates GoDaddy domain purchase flow via browser."""

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
        log.info(f"Domain bot: Browser launched (Chrome, profile: account_{self.account_idx + 1})")
        self._dismiss_restore_popup()
        self._accept_cookies()

    def _dismiss_restore_popup(self):
        """Dismiss Chrome's 'Restore pages?' popup that appears after unclean shutdown."""
        page = self._page
        try:
            restore_btn = page.locator('button:has-text("Restore"), button:has-text("Close")').first
            if restore_btn.is_visible(timeout=2000):
                # Click the X to dismiss rather than restoring old pages
                close_btn = page.locator('button[aria-label="Close"], button:has-text("Close")').first
                if close_btn.is_visible(timeout=1000):
                    close_btn.click()
                    log.info("Domain bot: Dismissed 'Restore pages' popup")
                else:
                    restore_btn.click()
                    log.info("Domain bot: Clicked Restore button")
                page.wait_for_timeout(1000)
        except Exception:
            pass

    def _accept_cookies(self):
        """Accept cookie consent banner if it appears, so session cookies persist."""
        page = self._page
        cookie_selectors = [
            'button#onetrust-accept-btn-handler',
            'button:has-text("Accept All Cookies")',
            'button:has-text("Accept All")',
            'button:has-text("Accept Cookies")',
            'button:has-text("I Accept")',
            'button:has-text("Got It")',
            'button:has-text("OK")',
            '#cookie-accept',
        ]
        for selector in cookie_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=1000):
                    btn.click()
                    page.wait_for_timeout(1000)
                    log.info(f"Domain bot: Accepted cookie consent via: {selector}")
                    return
            except Exception:
                continue
        log.debug("Domain bot: No cookie consent banner found")

    def _dismiss_popups(self):
        """Dismiss any modals/popups/recommendation overlays that appear."""
        page = self._page
        for _ in range(3):
            found = False
            close_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label="close"]',
                'button[aria-label="Dismiss"]',
                'button:has-text("No, Thanks")',
                'button:has-text("Not now")',
                'button:has-text("Maybe later")',
                'button:has-text("Skip")',
                'button:has-text("Got it")',
                'button:has-text("×")',
                'button:has-text("✕")',
                '[class*="close"][role="button"]',
            ]
            for selector in close_selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=500):
                        btn.click()
                        log.debug(f"Domain bot: Dismissed popup via: {selector}")
                        page.wait_for_timeout(1000)
                        found = True
                        break
                except Exception:
                    continue
            if not found:
                break

    def _do_sso_login(self):
        """Perform the full SSO login flow (username → password → redirect)."""
        page = self._page
        log.info("Domain bot: Logging in via SSO...")

        if "sso.godaddy.com" not in page.url:
            page.goto("https://sso.godaddy.com/login?realm=idp&app=mya&path=%2Fproducts")
            page.wait_for_load_state("domcontentloaded")
            page.wait_for_timeout(2000)

        self._dismiss_popups()

        # Email/username input
        username_input = page.locator('#username, input[name="username"], input[type="email"]').first
        username_input.wait_for(state="visible", timeout=15000)
        username_input.fill(self.email)
        log.debug("Domain bot: Filled username")

        submit_btn = page.locator('button[type="submit"], button:has-text("Next"), button:has-text("Sign in")').first
        submit_btn.click()
        page.wait_for_timeout(3000)

        # Password input
        password_input = page.locator('#password, input[name="password"], input[type="password"]').first
        password_input.wait_for(state="visible", timeout=15000)
        password_input.fill(self.password)
        log.debug("Domain bot: Filled password")

        submit_btn = page.locator('button[type="submit"], button:has-text("Sign in"), button:has-text("Next")').first
        submit_btn.click()
        page.wait_for_timeout(5000)

        page.wait_for_load_state("domcontentloaded")
        log.info("Domain bot: SSO login complete")
        self._dismiss_popups()

    def _ensure_logged_in(self):
        """Check if we're on SSO and login if needed. Returns True if login was performed."""
        if "sso.godaddy.com" in self._page.url:
            self._do_sso_login()
            return True
        return False

    def search_domain(self, domain: str) -> dict:
        """Navigate to GoDaddy products page, search for domain, return availability info.

        Returns dict with:
            available: bool
            price: str (e.g. "$14.77") or None
        """
        page = self._page

        # Go to products/dashboard page
        for attempt in range(3):
            try:
                page.goto("https://account.godaddy.com/products", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                # Check for error pages (upstream timeout, etc.) and retry
                body_text = page.text_content("body") or ""
                if "upstream request timeout" in body_text.lower() or "error" in body_text.lower()[:100]:
                    if attempt < 2:
                        log.warning(f"Domain bot: Page error (attempt {attempt + 1}), reloading...")
                        page.reload(wait_until="domcontentloaded")
                        page.wait_for_timeout(3000)
                        continue
                break
            except Exception as e:
                if attempt < 2:
                    log.warning(f"Domain bot: Navigation interrupted (attempt {attempt + 1}): {e}")
                    page.wait_for_timeout(2000)
                else:
                    raise

        # Handle SSO if needed
        if self._ensure_logged_in():
            page.goto("https://account.godaddy.com/products", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

        self._dismiss_popups()
        self._accept_cookies()
        self._dismiss_popups()
        page.wait_for_timeout(2000)

        # Type domain in search box and search
        search_input = page.locator(
            'input[placeholder*="Search using your business name"], '
            'input[placeholder*="domain name"], '
            'input[placeholder*="domain"]'
        ).first
        search_input.wait_for(state="visible", timeout=15000)
        search_input.fill(domain)
        log.info(f"Domain bot: Typed '{domain}' in search box")

        # Click search button (the magnifying glass icon next to the input)
        search_btn = page.locator(
            'button[aria-label="Search"], '
            'button[type="submit"]:near(input[placeholder*="domain"])'
        ).first
        try:
            search_btn.click()
        except Exception:
            # Fallback: press Enter in the search box
            search_input.press("Enter")
        page.wait_for_timeout(5000)
        page.wait_for_load_state("domcontentloaded")
        log.info(f"Domain bot: Searched for {domain}")

        self._accept_cookies()
        self._dismiss_popups()
        page.wait_for_timeout(3000)

        # Check if domain is available — try multiple indicators
        result = {"available": False, "price": None}

        try:
            # Look for buy button — GoDaddy uses different text depending on account/A-B test
            buy_selectors = [
                'button:has-text("Make It Yours")',
                'a:has-text("Make It Yours")',
                'button:has-text("Get It")',
                'a:has-text("Get It")',
                'button:has-text("Get")',
                'button:has-text("Add to Cart")',
                'a:has-text("Add to Cart")',
            ]
            for sel in buy_selectors:
                try:
                    btn = page.locator(sel).first
                    if btn.is_visible(timeout=2000):
                        result["available"] = True
                        log.info(f"Domain bot: {domain} is available (found '{sel}')")
                        break
                except Exception:
                    continue

            if not result["available"]:
                # Fallback: check for "GREAT NAME" badge or price
                great_name = page.locator('text="GREAT NAME"').first
                if great_name.is_visible(timeout=3000):
                    result["available"] = True
                    log.info(f"Domain bot: {domain} is available (found 'GREAT NAME' badge)")
        except Exception:
            pass

        if not result["available"]:
            # Last fallback: check page content via JS
            try:
                available = page.evaluate("""() => {
                    const body = document.body.innerText;
                    return body.includes('Make It Yours') || body.includes('GREAT NAME') ||
                           body.includes('Get It') || body.includes('Add to Cart') ||
                           body.includes('1 YEAR TERM');
                }""")
                if available:
                    result["available"] = True
                    log.info(f"Domain bot: {domain} is available (found via JS text check)")
            except Exception:
                pass

        if not result["available"]:
            # Take debug screenshot before returning
            try:
                self.screenshot(f"{_LOGS_DIR}/debug_domain_search.png")
            except Exception:
                pass
            log.info(f"Domain bot: {domain} does not appear to be available")
            return result

        # Extract price from the 1 Year Term section
        try:
            price_text = page.evaluate("""() => {
                const body = document.body.innerText;
                // Find price pattern near "1 YEAR TERM"
                const match = body.match(/1 YEAR TERM[\\s\\S]*?\\$(\\d+\\.\\d{2})/i);
                if (match) return '$' + match[1];
                // Fallback: find any price on the page
                const priceMatch = body.match(/\\$(\\d+\\.\\d{2})/);
                if (priceMatch) return '$' + priceMatch[1];
                return null;
            }""")
            result["price"] = price_text
            log.info(f"Domain bot: {domain} price: {price_text}/yr")
        except Exception:
            log.debug(f"Domain bot: Could not extract price for {domain}")

        return result

    def select_term_and_add(self):
        """Select 1 Year Term and click Make It Yours."""
        page = self._page

        # Click the 1 Year Term card to ensure it's selected (not the 3 Year)
        try:
            # Try clicking the card/container that holds "1 YEAR TERM"
            selected = page.evaluate("""() => {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    const text = el.textContent.trim();
                    if ((text.startsWith('1 YEAR TERM') || text.startsWith('1 Year Term'))
                        && el.childNodes.length <= 3) {
                        // Click the parent card element
                        let card = el.closest('div[class]') || el.parentElement;
                        if (card) {
                            card.click();
                            return 'clicked_card';
                        }
                        el.click();
                        return 'clicked_text';
                    }
                }
                return 'not_found';
            }""")
            page.wait_for_timeout(1500)
            log.info(f"Domain bot: 1 Year Term selection: {selected}")
        except Exception as e:
            log.warning(f"Domain bot: Could not select 1 Year Term: {e}")

        # Click the buy button (text varies by account)
        buy_selectors = [
            'button:has-text("Make It Yours")',
            'a:has-text("Make It Yours")',
            'button:has-text("Get It")',
            'a:has-text("Get It")',
            'button:has-text("Add to Cart")',
            'a:has-text("Add to Cart")',
        ]
        for sel in buy_selectors:
            try:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    page.wait_for_timeout(3000)
                    log.info(f"Domain bot: Clicked '{sel}'")
                    return
            except Exception:
                continue
        raise RuntimeError("Could not find buy button (Make It Yours / Get It / Add to Cart)")

    def go_to_cart(self):
        """Click View Cart from the bottom bar after adding domain."""
        page = self._page

        # After "Make It Yours", a bottom bar appears with "View Cart"
        for selector in [
            'button:has-text("View Cart")',
            'a:has-text("View Cart")',
            'button:has-text("Continue to Cart")',
            'a:has-text("Continue to Cart")',
        ]:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=3000):
                    btn.click()
                    page.wait_for_timeout(4000)
                    page.wait_for_load_state("domcontentloaded")
                    log.info(f"Domain bot: Clicked '{selector}'")
                    return
            except Exception:
                continue

        log.warning("Domain bot: Could not find View Cart / Continue to Cart button")
        raise RuntimeError("Could not find View Cart button")

    def skip_extras(self):
        """On the registration/extras page, select No Domain Protection and No Thanks, then Continue to Cart."""
        page = self._page
        page.wait_for_timeout(3000)

        # Select "No Domain Protection" radio
        try:
            no_protection = page.locator('text="No Domain Protection"').first
            if no_protection.is_visible(timeout=5000):
                no_protection.click()
                page.wait_for_timeout(1000)
                log.info("Domain bot: Selected 'No Domain Protection'")
        except Exception:
            log.warning("Domain bot: Could not find 'No Domain Protection' option")

        # Select "No Thanks" radio (for email upsell)
        try:
            no_thanks = page.locator('text="No Thanks"').first
            if no_thanks.is_visible(timeout=3000):
                no_thanks.click()
                page.wait_for_timeout(1000)
                log.info("Domain bot: Selected 'No Thanks' for email")
        except Exception:
            log.debug("Domain bot: Could not find 'No Thanks' option")

        # Click "Continue to Cart"
        continue_btn = page.locator(
            'button:has-text("Continue to Cart"), '
            'a:has-text("Continue to Cart")'
        ).first
        continue_btn.wait_for(state="visible", timeout=10000)
        continue_btn.click()
        page.wait_for_timeout(4000)
        page.wait_for_load_state("domcontentloaded")
        log.info("Domain bot: Clicked 'Continue to Cart' on extras page")

    def prepare_checkout(self):
        """On the cart page, ensure toggles are off, term is 1 Year, click Ready for Checkout."""
        page = self._page
        page.wait_for_timeout(3000)

        # Turn off "Full Domain Protection" toggle if it's on
        try:
            page.evaluate("""() => {
                const labels = document.querySelectorAll('*');
                for (const label of labels) {
                    if (label.childNodes.length === 1 &&
                        label.textContent.trim().startsWith('Full Domain Protection')) {
                        // Walk up to find the toggle
                        let container = label.parentElement;
                        for (let i = 0; i < 5 && container; i++) {
                            const toggle = container.querySelector(
                                'input[type="checkbox"], [role="switch"], [class*="toggle"]'
                            );
                            if (toggle) {
                                const isOn = toggle.checked ||
                                    toggle.getAttribute('aria-checked') === 'true' ||
                                    toggle.classList.contains('on') ||
                                    toggle.classList.contains('active');
                                if (isOn) {
                                    toggle.click();
                                    return 'turned_off';
                                }
                                return 'already_off';
                            }
                            container = container.parentElement;
                        }
                    }
                }
                return 'not_found';
            }""")
            log.info("Domain bot: Checked Full Domain Protection toggle")
        except Exception:
            log.debug("Domain bot: Could not check Full Domain Protection toggle")

        page.wait_for_timeout(1000)

        # Turn off "Professional Email" toggle if it's on
        try:
            page.evaluate("""() => {
                const labels = document.querySelectorAll('*');
                for (const label of labels) {
                    if (label.childNodes.length === 1 &&
                        label.textContent.trim().startsWith('Professional Email')) {
                        let container = label.parentElement;
                        for (let i = 0; i < 5 && container; i++) {
                            const toggle = container.querySelector(
                                'input[type="checkbox"], [role="switch"], [class*="toggle"]'
                            );
                            if (toggle) {
                                const isOn = toggle.checked ||
                                    toggle.getAttribute('aria-checked') === 'true' ||
                                    toggle.classList.contains('on') ||
                                    toggle.classList.contains('active');
                                if (isOn) {
                                    toggle.click();
                                    return 'turned_off';
                                }
                                return 'already_off';
                            }
                            container = container.parentElement;
                        }
                    }
                }
                return 'not_found';
            }""")
            log.info("Domain bot: Checked Professional Email toggle")
        except Exception:
            log.debug("Domain bot: Could not check Professional Email toggle")

        page.wait_for_timeout(1000)

        # Ensure term is 1 Year
        try:
            term_dropdown = page.locator('select').first
            if term_dropdown.is_visible(timeout=2000):
                current = term_dropdown.input_value()
                if "1" not in current:
                    term_dropdown.select_option(label="1 Year")
                    page.wait_for_timeout(1000)
                    log.info("Domain bot: Set term to 1 Year")
                else:
                    log.debug("Domain bot: Term already set to 1 Year")
        except Exception:
            log.debug("Domain bot: Could not verify term dropdown")

        page.wait_for_timeout(2000)

        # Click "Ready for Checkout"
        checkout_btn = page.locator(
            'button:has-text("Ready for Checkout"), '
            'a:has-text("Ready for Checkout")'
        ).first
        checkout_btn.wait_for(state="visible", timeout=10000)
        checkout_btn.click()
        page.wait_for_timeout(5000)
        page.wait_for_load_state("domcontentloaded")
        log.info("Domain bot: Clicked 'Ready for Checkout'")

    def screenshot(self, path: str) -> str:
        """Take a screenshot of the current page."""
        self._page.screenshot(path=path, full_page=True)
        log.info(f"Domain bot: Screenshot saved: {path}")
        return path

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
        log.info("Domain bot: Browser closed")
