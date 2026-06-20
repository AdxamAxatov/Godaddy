import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from website_generator import generate_appeal

INFO = {
    "company_name": "Press On Logistics Express LLC",
    "domain": "pressonlogistics.com",
    "email": "info@pressonlogistics.com",
    "owner_name": "Lorna",
    "address": "1951 Southampton Rd Apt H6",
    "city_state": "Atlanta, GA 30349",
    "job_title": "Regional CDL-A Truck Driver",
    "pay_range": "$1,200 – $1,400 / week",
    "home_time": "Home weekly for 2 days",
    "min_experience": "1 year",
    "routes_type": "Regional Routes",
    "perks": ["Dental & Vision insurance", "401(k) with match", "Fuel card"],
}

failures = []
samples = [generate_appeal(INFO) for _ in range(60)]

for i, a in enumerate(samples):
    for ch in ("<", "`", "*", "#"):
        if ch in a:
            failures.append(f"sample {i}: contains forbidden char {ch!r}")
            break
    if "Lorna" not in a:
        failures.append(f"sample {i}: missing owner name")
    if "Press On Logistics Express LLC" not in a:
        failures.append(f"sample {i}: missing company name")
    if "$1,200" not in a:
        failures.append(f"sample {i}: missing pay")
    if "pressonlogistics.com" not in a:
        failures.append(f"sample {i}: missing site URL for verification")

if len(set(samples)) < 30:
    failures.append(f"not unique enough: {len(set(samples))}/60 distinct")

partial = generate_appeal({"company_name": "X LLC", "domain": "x.com",
                           "city_state": "Dallas, TX 75001", "owner_name": "Roy"})
if "Roy" not in partial or "X LLC" not in partial:
    failures.append("partial-data appeal missing name/company")

if failures:
    for f in failures[:10]:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: generate_appeal — plain, factual, unique, partial-safe")
