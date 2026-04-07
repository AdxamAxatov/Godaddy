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
        self._accept_cookies()

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
                    log.info(f"Accepted cookie consent via: {selector}")
                    return
            except Exception:
                continue
        log.debug("No cookie consent banner found")

    def _dismiss_popups(self):
        """Dismiss any modals/popups/recommendation overlays that appear."""
        page = self._page
        dismissed = False

        # Run up to 3 rounds to catch stacked popups
        for _ in range(3):
            found = False

            # Check for "Create an email account" popup — this is the one that
            # gets stuck the most. It's a modal with an email form, Cancel link,
            # X close button, and "Create Email Account" button. We need to
            # dismiss it WITHOUT accidentally clicking something behind it.
            # Strategy: use JS to find the modal container first, then click
            # Cancel or X specifically inside that container.
            try:
                popup_dismissed = page.evaluate("""() => {
                    // Find the heading "Create an email account" anywhere on the page
                    const allEls = document.querySelectorAll('*');
                    for (const el of allEls) {
                        if (el.childNodes.length === 1 &&
                            el.textContent.trim() === 'Create an email account') {
                            // Walk up to find the modal/dialog container
                            let modal = el.closest('[class*="modal"], [class*="dialog"], [role="dialog"], [class*="overlay"], [class*="popup"]');
                            if (!modal) {
                                // No semantic container — walk up a few levels
                                modal = el.parentElement?.parentElement?.parentElement;
                            }
                            if (!modal) continue;

                            // Try 1: Click "Cancel" inside this modal
                            const links = modal.querySelectorAll('a, button, span');
                            for (const link of links) {
                                if (link.textContent.trim() === 'Cancel') {
                                    link.click();
                                    return 'cancel';
                                }
                            }

                            // Try 2: Click the X close button inside this modal
                            const closeButtons = modal.querySelectorAll(
                                'button[aria-label*="lose"], button[aria-label*="ismiss"], ' +
                                '[class*="close"], svg'
                            );
                            for (const btn of closeButtons) {
                                const rect = btn.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    btn.click();
                                    return 'close';
                                }
                            }

                            // Try 3: Any clickable element that looks like a close/X
                            for (const child of modal.querySelectorAll('*')) {
                                const text = child.textContent.trim();
                                if ((text === '×' || text === '✕' || text === 'X' || text === 'x') &&
                                    child.children.length === 0) {
                                    child.click();
                                    return 'x';
                                }
                            }
                        }
                    }
                    return null;
                }""")

                if popup_dismissed:
                    page.wait_for_timeout(1000)
                    dismissed = True
                    found = True
                    log.debug(f"Dismissed 'Create an email account' popup via {popup_dismissed}")
                    continue
            except Exception:
                pass

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
                    // Look for Cancel text inside modals/popups
                    const all = document.querySelectorAll('[class*="modal"] a, [role="dialog"] a, [role="dialog"] button, [class*="popup"] a, [class*="popup"] button');
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
                'button:has-text("No, Thanks")',
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

    def _safe_click(self, locator, description="element", timeout=5000, force=False, max_retries=3):
        """Try to click a locator. If it fails, dismiss popups and retry.

        This is the core of the "smart popup handling" — instead of only
        checking for popups at a few hardcoded points in the flow, every
        important click goes through this method. If a popup (like the
        "Create an email account" recommendation) is covering the button
        we want to click, Playwright throws an error. We catch that error,
        call _dismiss_popups() to clear whatever is blocking, then retry
        the click. Up to max_retries attempts before giving up.

        Args:
            locator: Playwright locator for the element to click.
            description: Human-readable name for logging (e.g. "Continue button").
            timeout: How long to wait for the element to be visible before each attempt.
            force: If True, use Playwright's force click (bypasses actionability checks).
            max_retries: Number of times to retry after popup dismissal.
        """
        page = self._page
        last_error = None

        for attempt in range(max_retries):
            try:
                # Make sure the element is visible first
                locator.wait_for(state="visible", timeout=timeout)
                locator.click(force=force)
                if attempt > 0:
                    log.info(f"Clicked {description} after {attempt} popup dismissal(s)")
                return True
            except Exception as e:
                last_error = e
                log.debug(f"Click on {description} failed (attempt {attempt + 1}/{max_retries}): {e}")

                # The click failed — likely a popup is covering the element.
                # Try to dismiss whatever is blocking and retry.
                if attempt < max_retries - 1:
                    dismissed = self._dismiss_popups()
                    if dismissed:
                        log.info(f"Dismissed popup blocking {description} — retrying click")
                        page.wait_for_timeout(1000)
                    else:
                        # No popup found but click still failed — wait a bit
                        # in case the page is still loading/animating
                        page.wait_for_timeout(2000)

        raise last_error

    def _safe_fill(self, locator, value, description="field", timeout=5000, max_retries=3):
        """Try to fill a field. If it fails (popup blocking), dismiss popups and retry.

        Same idea as _safe_click but for typing into input fields. A popup
        covering the input would prevent Playwright from focusing it, so we
        catch that, clear the popup, and try again.
        """
        page = self._page
        last_error = None

        for attempt in range(max_retries):
            try:
                locator.wait_for(state="visible", timeout=timeout)
                locator.fill(value)
                if attempt > 0:
                    log.info(f"Filled {description} after {attempt} popup dismissal(s)")
                return True
            except Exception as e:
                last_error = e
                log.debug(f"Fill on {description} failed (attempt {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    dismissed = self._dismiss_popups()
                    if dismissed:
                        log.info(f"Dismissed popup blocking {description} — retrying fill")
                        page.wait_for_timeout(1000)
                    else:
                        page.wait_for_timeout(2000)

        raise last_error

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

    def go_to_create_email(self, domain: str, _retry=0):
        """Follow the real manual flow to reach the Create New Email form.

        Step 1: Overview page → click "Set up accounts"
        Step 2: Choose account type → click "Get Started" under Microsoft 365 Email
        Step 3: Choose domain → type domain, click Continue
        Step 4: Lands on "Create multiple emails" → click "Create single email" tab
        """
        page = self._page

        # ── Step 1: Go to Overview ──
        for attempt in range(3):
            try:
                page.goto("https://productivity.godaddy.com/#/", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                break
            except Exception as e:
                if attempt < 2:
                    log.warning(f"Navigation interrupted (attempt {attempt + 1}), retrying: {e}")
                    page.wait_for_timeout(2000)
                else:
                    raise

        # Handle SSO redirect if session expired
        if self._ensure_logged_in():
            log.info("Was redirected to SSO — navigating back to Overview")
            page.goto("https://productivity.godaddy.com/#/", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
        else:
            log.info("Already logged in")

        self._dismiss_popups()
        page.wait_for_timeout(2000)

        # Click "Set up accounts"
        self._safe_click(page.locator('text="Set up accounts"').first, "Set up accounts")
        page.wait_for_timeout(3000)
        log.info("Step 1: Clicked 'Set up accounts'")

        # ── Step 2: Choose account type → Microsoft 365 Email ──
        # Some accounts show a type selector (M365 vs other), others skip straight
        # to domain entry or the email form. Check which page we landed on.
        self._dismiss_popups()
        page.wait_for_timeout(2000)

        # Check if account type selector is present
        m365_visible = False
        try:
            m365_visible = page.locator('text="Microsoft 365 Email"').first.is_visible(timeout=5000)
        except Exception:
            pass

        if m365_visible:
            # Use JS to find the "Get Started" button inside the same card as "Microsoft 365 Email"
            clicked = page.evaluate("""() => {
                const all = document.querySelectorAll('*');
                for (const el of all) {
                    if (el.childNodes.length === 1 && el.textContent.trim() === 'Microsoft 365 Email') {
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
                self._safe_click(page.locator('button:has-text("Get Started"), a:has-text("Get Started")').first, "Get Started")
            page.wait_for_timeout(3000)
            log.info("Step 2: Clicked 'Get Started' under Microsoft 365 Email")
        else:
            log.info("Step 2: No account type selector — skipped (account goes straight to domain/form)")

        # ── Step 3: Choose domain → type domain, click Continue ──
        # Some accounts skip straight to the email form (no domain entry step).
        # Check if we're already on the form by looking for Username field.
        self._dismiss_popups()
        already_on_form = False
        try:
            already_on_form = page.locator('text="Username"').first.is_visible(timeout=3000)
        except Exception:
            pass

        if not already_on_form:
            domain_input = page.locator('input[type="text"], input[placeholder*="domain"], input[placeholder*="business"]').first
            self._safe_fill(domain_input, domain, "domain input", timeout=15000)
            page.wait_for_timeout(1000)

            # Wait for Continue button to stop showing "Loading..."
            continue_btn = page.locator('button:has-text("Continue")').first
            continue_btn.wait_for(state="visible", timeout=15000)
            for _ in range(40):  # up to ~20 seconds
                btn_text = continue_btn.inner_text()
                if "loading" not in btn_text.lower():
                    break
                page.wait_for_timeout(500)
            self._safe_click(continue_btn, "Continue button")

            # Wait for the next page (email form) to load — up to 20 seconds
            page.wait_for_timeout(5000)
            reached_form = False
            for _ in range(30):  # up to ~15 more seconds
                if page.locator('text="Create single email"').first.is_visible():
                    reached_form = True
                    break
                if page.locator('text="Username"').first.is_visible():
                    reached_form = True
                    break
                page.wait_for_timeout(500)

            # Check if GoDaddy redirected back to Overview
            if not reached_form or "productivity.godaddy.com/#/" in page.url:
                overview_check = False
                try:
                    overview_check = page.locator('text="Set up accounts"').first.is_visible(timeout=2000)
                except Exception:
                    pass
                if overview_check:
                    if _retry < 2:
                        log.warning(f"GoDaddy redirected back to Overview after domain entry — retry {_retry + 1}/2")
                        page.wait_for_timeout(3000)
                        return self.go_to_create_email(domain, _retry=_retry + 1)
                    else:
                        raise Exception("GoDaddy keeps redirecting back to Overview after entering domain — could not reach email form")

            log.info(f"Step 3: Entered domain '{domain}' and clicked Continue")
        else:
            log.info("Step 3: Already on email form — skipped domain entry")

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
                    self._safe_click(el, "Create single email tab", force=True)
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

    def get_expiration_dates(self, _domain: str = "", _retry: int = 0) -> list[str]:
        """Scrape available expiration dates from the dropdown or static text."""
        page = self._page

        # Check if GoDaddy redirected us away from the email form
        on_overview = False
        try:
            on_overview = page.locator('text="Set up accounts"').first.is_visible(timeout=2000)
        except Exception:
            pass
        if on_overview:
            if _retry < 2 and _domain:
                log.warning(f"GoDaddy redirected to Overview before expiration check — retrying ({_retry + 1}/2)")
                self.go_to_create_email(_domain)
                return self.get_expiration_dates(_domain=_domain, _retry=_retry + 1)
            raise RuntimeError("GoDaddy keeps redirecting back to Overview page — could not reach email form")

        # First, try to find and open the dropdown
        try:
            dropdown = self._find_expiration_dropdown()
        except RuntimeError:
            dropdown = None

        if dropdown:
            # Dropdown exists — always open it to get the real count
            dropdown.click()
            page.wait_for_timeout(5000)

            try:
                page.screenshot(path=f"{_LOGS_DIR}/debug_expiration_open.png")
            except Exception:
                pass

            # Scrape options via JS — catches all items regardless of scroll/visibility
            # Some accounts show "December 15, 2026  (2 Available)", others just "December 15, 2026"
            dates = page.evaluate("""() => {
                const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
                function looksLikeDate(text) {
                    return months.some(m => text.includes(m));
                }
                const dates = [];
                // First try: items with name="expirationDateDropDown"
                const byName = document.querySelectorAll('[name="expirationDateDropDown"]');
                for (const el of byName) {
                    const text = el.textContent.trim();
                    if (text && looksLikeDate(text)) dates.push(text);
                }
                if (dates.length > 0) return dates;
                // Fallback: any role="option" or dropdown-item that looks like a date
                const fallback = document.querySelectorAll('[role="option"], .dropdown-item, [class*="dropdown"] li, [class*="select"] li');
                for (const el of fallback) {
                    const text = el.textContent.trim();
                    if (text && looksLikeDate(text)) dates.push(text);
                }
                return dates;
            }""")

            # Close the dropdown
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

            log.info(f"Expiration dates: {dates}")
            self._expiration_dates = dates

            if len(dates) <= 1:
                self._single_expiration = True
                log.info(f"Only {len(dates)} expiration date(s) — will skip dropdown in fill_form")
            else:
                self._single_expiration = False

            if not dates:
                try:
                    page.screenshot(path=f"{_LOGS_DIR}/debug_expiration_empty.png")
                    log.info("Debug screenshot saved to debug_expiration_empty.png")
                except Exception:
                    pass
                raise RuntimeError("Dropdown opened but no expiration options found — check logs/debug_expiration_open.png")
            return dates

        # No dropdown — check for static text
        try:
            label = page.locator('text="Renewal/Expiration date"').first
            if label.is_visible(timeout=3000):
                parent = page.locator('text="Renewal/Expiration date" >> ..').first
                parent_text = parent.text_content().strip()
                date_text = parent_text.replace("Renewal/Expiration date", "").strip()
                if date_text:
                    log.info(f"Single expiration date (no dropdown): {date_text}")
                    self._single_expiration = True
                    self._expiration_dates = [date_text]
                    return [date_text]
        except Exception:
            pass

        raise RuntimeError("Could not find expiration dates — no dropdown and no static text")

    def fill_form(self, username: str, first_name: str, last_name: str,
                  admin: bool, expiration_idx: int, password: str, notify_email: str):
        """Fill in all fields on the Create New Email form."""
        page = self._page

        # Username (email prefix before @domain.com)
        self._safe_fill(page.get_by_label("Username"), username, "Username")

        # First name / Last name
        self._safe_fill(page.get_by_label("First name"), first_name, "First name")
        self._safe_fill(page.get_by_label("Last name"), last_name, "Last name")

        # Expiration date dropdown — skip if only one option
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

        # Link domains — select "Do not share"
        try:
            link_dropdown = page.get_by_text("Please select...").first
            if link_dropdown.is_visible(timeout=3000):
                link_dropdown.click()
                page.wait_for_timeout(1000)
                # The dropdown has its own scroller — use JS to find and click "Do not share"
                clicked = page.evaluate("""() => {
                    const items = document.querySelectorAll('[role="option"], .dropdown-item, [class*="drop-down"] *');
                    for (const item of items) {
                        if (item.textContent.trim() === 'Do not share') {
                            item.scrollIntoView({block: 'center'});
                            item.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                if clicked:
                    page.wait_for_timeout(1000)
                    log.info("Selected 'Do not share' for Link domains")
                else:
                    log.warning("'Do not share' option not found in dropdown items")
                    # Close the dropdown by clicking elsewhere
                    page.locator("body").click(position={"x": 0, "y": 0})
                    page.wait_for_timeout(500)
            else:
                log.info("Link domains dropdown not found — skipping")
        except Exception as e:
            log.warning(f"Could not select 'Do not share' for Link domains: {e}")
            # Make sure the dropdown is closed so it doesn't block subsequent elements
            try:
                page.locator("body").click(position={"x": 0, "y": 0})
                page.wait_for_timeout(500)
            except Exception:
                pass

        # Administrator permissions (radio buttons)
        if admin:
            self._safe_click(page.get_by_label("Yes"), "Admin Yes radio")
        else:
            self._safe_click(page.get_by_label("No"), "Admin No radio")

        # Password
        self._safe_fill(page.get_by_label("Create a password"), password, "Password")

        # Send account info to
        notify_field = page.get_by_label("Send account info to")
        self._safe_click(notify_field, "Send account info field")
        notify_field.clear()
        notify_field.fill(notify_email)

        log.info(f"Form filled: {username}@..., {first_name} {last_name}")

    def screenshot(self, path: str) -> str:
        """Take a screenshot of the current page."""
        self._page.screenshot(path=path, full_page=True)
        log.info(f"Screenshot saved: {path}")
        return path

    def submit(self):
        """Click the Create button, dismiss phone number offer, then navigate back to Overview."""
        page = self._page
        self._safe_click(page.get_by_role("button", name="Create"), "Create button")
        page.wait_for_load_state("domcontentloaded")
        log.info("Create button clicked")

        # Handle Microsoft Customer Agreement Acknowledgment page
        # GoDaddy shows this after clicking Create on some accounts — it loads a
        # heavy embedded Microsoft doc viewer, so the page can take a while.
        # We poll for up to 20 seconds looking for the Accept Agreement button,
        # checking every second. Using JS to find ANY element with that text,
        # not just <button> or <a>, since GoDaddy could render it as anything.
        agreement_clicked = False
        for _ in range(20):
            page.wait_for_timeout(1000)
            try:
                clicked = page.evaluate("""() => {
                    const all = document.querySelectorAll('button, a, input[type="submit"], [role="button"]');
                    for (const el of all) {
                        if (el.textContent.trim() === 'Accept Agreement' || el.value === 'Accept Agreement') {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                el.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                if clicked:
                    log.info("Clicked 'Accept Agreement' on Microsoft Customer Agreement page")
                    page.wait_for_load_state("domcontentloaded")
                    page.wait_for_timeout(10000)
                    agreement_clicked = True
                    break
            except Exception:
                continue

        if not agreement_clicked:
            log.debug("No Microsoft Customer Agreement page appeared within 20 seconds")

        # Wait for the phone number notification offer to appear (up to 25 seconds)
        # GoDaddy often offers to notify via phone after email creation
        dismissed_offer = False
        for _ in range(50):
            page.wait_for_timeout(500)
            try:
                no_thanks = page.locator('button:has-text("No, Thanks"), button:has-text("No Thanks"), a:has-text("No, Thanks"), a:has-text("No Thanks")').first
                if no_thanks.is_visible(timeout=200):
                    no_thanks.click()
                    page.wait_for_timeout(1000)
                    log.info("Dismissed phone number notification offer")
                    dismissed_offer = True
                    break
            except Exception:
                continue

        if not dismissed_offer:
            log.info("Phone number offer did not appear — skipping")

        # Go back to Overview so browser is ready for next email
        page.goto("https://productivity.godaddy.com/#/")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(3000)
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
