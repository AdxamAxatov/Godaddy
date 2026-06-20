import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

# Round-trips, including hostile content (FIX 2): '<', '&', apostrophe, '</script>'.
data = {
    "company_name": "A<B & C's </script> LLC",
    "perks": ["401(k) with match", "Dental & Vision"],
    "pay_range": "$1,200 – $1,400 / week",
    "owner_name": "Lorna",
}
html = "<body>" + wg._company_data_script(data) + "<h1>hi</h1></body>"

inner = html.split('id="company-data">', 1)[1].split("</script>", 1)[0]
if "</script" in inner.lower():
    failures.append("embedded JSON can break out of the script tag")

out = wg.extract_company_data(html)
if out != data:
    failures.append(f"round-trip mismatch: {out}")

if wg.extract_company_data("<body>no data here</body>") is not None:
    failures.append("missing embed should return None")
if wg.extract_company_data('<script id="company-data">{bad json</script>') is not None:
    failures.append("unparseable embed should return None")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: company-data codec round-trips and is breakout-safe")
