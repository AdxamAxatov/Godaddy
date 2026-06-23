import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from website_generator import generate_job_description, _annualize

failures = []

# _annualize: weekly ×52, range only, None when not weekly.
if _annualize("$1,200 – $1,400 / week") != "$62,400 – $72,800":
    failures.append(f"_annualize wrong: {_annualize('$1,200 – $1,400 / week')}")
if _annualize("$90,000 / year") is not None:
    failures.append("_annualize should return None for non-weekly pay")

INFO = {
    "company_name": "Test Freight LLC", "city_state": "Dallas, TX 75001",
    "pay_range": "$1,200 – $1,400 / week", "home_time": "Home weekly",
    "perks": ["401(k) with match", "Health insurance"], "min_experience": "1 year",
    "routes_type": "OTR Routes",
}
# 1200*52=62,400 ; 1400*52=72,800

for i in range(150):
    jd = generate_job_description(INFO)
    if INFO["pay_range"] not in jd:
        failures.append(f"iter {i}: weekly range dropped")
    if "$62,400" not in jd or "$72,800" not in jd:
        failures.append(f"iter {i}: annual figure missing")
    low = jd.lower()
    if "year" not in low and "annual" not in low:
        failures.append(f"iter {i}: no annual wording")

if failures:
    for f in failures[:8]:
        print("FAIL:", f)
    print(f"... {len(failures)} total")
    sys.exit(1)
print("PASS: annual pay (×52) shown alongside the weekly range in every posting")
