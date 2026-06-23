import os
import re
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

# Slang/tone the grounded-professional rewrite must NOT use.
SLANG = ["no bs", "nothing fancy", "no games", "plain and simple", "bait-and-switch"]
# Must never route applicants off-platform or embed contact channels.
OFFPLATFORM = ["call us", "text us", "email your resume", "call or text", "apply at our site"]
PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")

failures = []
samples = [generate_appeal(INFO) for _ in range(250)]

for i, a in enumerate(samples):
    low = a.lower()
    for ch in ("<", "`", "*", "#"):           # plain text only
        if ch in a:
            failures.append(f"sample {i}: forbidden char {ch!r}")
            break
    for s in SLANG:
        if s in low:
            failures.append(f"sample {i}: slang {s!r}")
    for s in OFFPLATFORM:
        if s in low:
            failures.append(f"sample {i}: off-platform routing {s!r}")
    if PHONE.search(a):
        failures.append(f"sample {i}: phone number present")
    if "Lorna" not in a:
        failures.append(f"sample {i}: missing owner name")
    if "Press On Logistics Express LLC" not in a:
        failures.append(f"sample {i}: missing company name")
    if "$1,200" not in a:                      # role/pay always present
        failures.append(f"sample {i}: missing pay")
    if "pressonlogistics.com" not in a:        # verification offer references domain
        failures.append(f"sample {i}: missing site URL for verification")
    if "indeed" not in low:                    # on-platform handling stated
        failures.append(f"sample {i}: does not mention applying through Indeed")
    # grounding: must not invent facts that weren't supplied
    for bad in ("dot#", "usdot", "mc#", "founded in", "since 19", "since 20",
                "trucks in our fleet", "drivers on staff"):
        if bad in low:
            failures.append(f"sample {i}: invented/ungrounded fact {bad!r}")

# Uniqueness floor — submissions across companies must not look templated.
uniq = len(set(samples))
if uniq < 230:
    failures.append(f"variation too low: {uniq}/250 distinct")

# Partial-data (older site, no job facts) must still work and not hallucinate pay.
partial = generate_appeal({"company_name": "X LLC", "domain": "x.com",
                           "city_state": "Dallas, TX 75001", "owner_name": "Roy"})
if "Roy" not in partial or "X LLC" not in partial:
    failures.append("partial-data appeal missing name/company")
if "$" in partial:
    failures.append("partial-data appeal hallucinated a pay figure")

# No-owner path must not leave a dangling name.
noowner = generate_appeal({"company_name": "Y Carriers LLC", "domain": "y.com",
                           "city_state": "Reno, NV", "routes_type": "OTR Routes"})
if "Y Carriers LLC" not in noowner:
    failures.append("no-owner appeal missing company name")

if failures:
    for f in failures[:12]:
        print("FAIL:", f)
    print(f"... {len(failures)} total failures")
    sys.exit(1)
print(f"PASS: generate_appeal — grounded, plain, on-platform, {uniq}/250 unique, partial-safe")
