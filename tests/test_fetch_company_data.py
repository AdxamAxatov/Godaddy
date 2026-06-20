import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import main
import website_generator as wg

failures = []


class _Resp:
    def __init__(self, text):
        self.text = text


# Case A: page has an embed -> (data, False).
embed_html = "<body>" + wg._company_data_script(
    {"company_name": "Z LLC", "domain": "z.com", "pay_range": "$1k", "perks": []}) + "</body>"
main._http = lambda method, url, **kw: _Resp(embed_html)
data, partial = main._fetch_company_data("z.com")  # no scheme -> normalized
if not data or data.get("company_name") != "Z LLC" or partial:
    failures.append(f"embed case wrong: {(data, partial)}")

# Case B: first fetch raises (SSL), retry succeeds (FIX 4).
calls = {"n": 0}
def flaky(method, url, **kw):
    calls["n"] += 1
    if kw.get("verify", True):
        raise main.requests.exceptions.SSLError("bad cert")
    return _Resp(embed_html)
main._http = flaky
data, partial = main._fetch_company_data("https://z.com")
if not data or calls["n"] < 2:
    failures.append(f"SSL retry path failed: calls={calls['n']} data={bool(data)}")

# Case C: no embed, domain matches CSV -> partial.
main._http = lambda method, url, **kw: _Resp("<body>no embed</body>")
main.company_lookup.lookup = lambda d: [
    {"legal_name": "CSV Carrier LLC", "address": "1 A St", "city_state": "Dallas, TX 75001"}]
data, partial = main._fetch_company_data("csvcarrier.com")
if not data or not partial or data.get("company_name") != "CSV Carrier LLC":
    failures.append(f"CSV fallback wrong: {(data, partial)}")

# Case D: no embed, no CSV match -> (None, False).
main.company_lookup.lookup = lambda d: []
data, partial = main._fetch_company_data("nope.com")
if data is not None:
    failures.append(f"no-data case should be None: {(data, partial)}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: _fetch_company_data (embed / SSL-retry / CSV fallback / none)")
