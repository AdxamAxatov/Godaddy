import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import website_generator as wg

failures = []

info = {
    "company_name": "Press On Logistics Express LLC",
    "company_short": "Press On",
    "domain": "pressonlogistics.com",
    "email": "info@pressonlogistics.com",
    "address": "1951 Southampton Rd Apt H6",
    "city_state": "Atlanta, GA 30349",
    "job_title": "Regional CDL-A Truck Driver",
    "pay_range": "$1,200 – $1,400 / week",
    "home_time": "Home weekly for 2 days",
    "home_time_short": "Weekly",
    "home_time_detail": "Home 2 Days",
    "min_experience": "1 year",
    "fourth_card_value": "1 Yr. Exp",
    "fourth_card_label": "Min. Required",
    "routes": "Multi-State",
    "routes_type": "Regional Routes",
    "perks": ["Dental & Vision insurance", "401(k) with match", "Fuel card"],
}

zip_path = wg.generate_website_from_blocks(info)
with zipfile.ZipFile(zip_path) as z:
    html = z.read("index.html").decode("utf-8")

data = wg.extract_company_data(html)
if not data:
    print("FAIL: no company-data embedded in generated site")
    sys.exit(1)
for key in ("company_name", "pay_range", "perks", "routes_type"):
    if data.get(key) != info[key]:
        failures.append(f"{key} mismatch: {data.get(key)!r} != {info[key]!r}")
if not data.get("owner_name"):
    failures.append("owner_name missing from embed")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: generated site embeds matching company-data")
