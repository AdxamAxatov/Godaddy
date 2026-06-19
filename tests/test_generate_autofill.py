import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main
import company_lookup

failures = []
sent = []
main.tg_send = lambda chat_id, text, **kw: sent.append((chat_id, text, kw))
main.tg_edit_message = lambda chat_id, mid, text, **kw: sent.append((chat_id, text, kw))

CHAT = 999


def reset(fake_matches):
    sent.clear()
    main.pending_generate.clear()
    main.pending_generate[CHAT] = {"step": "awaiting_info"}
    company_lookup.lookup = lambda email: list(fake_matches)


# 1. Unique match -> auto-fill + route-type prompt.
reset([{"legal_name": "PTT TRANSPORTATION LLC", "address": "138 FREIDA RD",
        "city_state": "LEXINGTON, SC 29073"}])
main._handle_generate_input(CHAT, "info@ptttransportationllc.com")
st = main.pending_generate[CHAT]
if st.get("company_name") != "PTT TRANSPORTATION LLC":
    failures.append(f"unique: company_name not filled: {st}")
if st.get("city_state") != "LEXINGTON, SC 29073":
    failures.append(f"unique: city_state not filled: {st}")
if st.get("domain") != "ptttransportationllc.com":
    failures.append(f"unique: domain wrong: {st}")
if st.get("step") != "awaiting_route_type":
    failures.append(f"unique: step not advanced: {st.get('step')}")
if not any("Route type" in t for _, t, _ in sent):
    failures.append("unique: route-type prompt not sent")

# 2. No match -> stays awaiting_info, no company filled, asks for manual.
reset([])
main._handle_generate_input(CHAT, "info@nope.com")
st = main.pending_generate[CHAT]
if "company_name" in st:
    failures.append(f"no-match: should not fill company: {st}")
if st.get("step") != "awaiting_info":
    failures.append(f"no-match: step changed: {st.get('step')}")
if not any("find" in t.lower() or "paste" in t.lower() for _, t, _ in sent):
    failures.append(f"no-match: no fallback prompt: {sent}")

# 3. Ambiguous -> stores candidates, sends a picker with one button per match.
reset([{"legal_name": "D&G TRANSPORT INC", "address": "1 A ST", "city_state": "LODI, CA 95242"},
       {"legal_name": "D&G TRANSPORT INC", "address": "2 B ST", "city_state": "ANNANDALE, VA 22003"}])
main._handle_generate_input(CHAT, "info@dgtransportinc.com")
st = main.pending_generate[CHAT]
if len(st.get("company_candidates", [])) != 2:
    failures.append(f"ambiguous: candidates not stored: {st}")
picker = [kw for _, _, kw in sent if kw.get("reply_markup")]
if not picker or len(picker[-1]["reply_markup"]["inline_keyboard"]) != 2:
    failures.append(f"ambiguous: expected 2-button picker, got {picker}")

# 4. Picker callback applies the chosen record.
main.handle_callback("cbid", CHAT, 123, "gen_company:1")
st = main.pending_generate[CHAT]
if st.get("city_state") != "ANNANDALE, VA 22003":
    failures.append(f"picker: wrong record applied: {st}")
if st.get("step") != "awaiting_route_type":
    failures.append(f"picker: step not advanced: {st.get('step')}")

# 5. Regression: a multi-line Label: block still uses manual parsing (no lookup).
reset([{"legal_name": "SHOULD NOT BE USED", "address": "x", "city_state": "y"}])
called = {"n": 0}
company_lookup.lookup = lambda email: (called.__setitem__("n", called["n"] + 1) or [])
main._handle_generate_input(
    CHAT, "Company: Acme Trucking\nEmail: info@acme.com\nAddress: 1 Main St, Dallas, TX 75001")
st = main.pending_generate[CHAT]
if called["n"] != 0:
    failures.append("regression: Label: block should not call lookup")
if st.get("company_name") != "Acme Trucking":
    failures.append(f"regression: manual parse broke: {st}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: /generate email auto-fill (unique/no-match/ambiguous/picker/manual)")
