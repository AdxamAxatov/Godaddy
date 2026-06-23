import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import react_engine as re_

# Start from a clean rotation state so the test is deterministic-ish.
state = os.path.join(os.path.dirname(__file__), "..", "logs", "last_used_studios.json")
try:
    os.remove(state)
except OSError:
    pass

INFO = {
    "company_name": "Press On Logistics Express LLC", "company_short": "Press On",
    "domain": "pressonlogistics.com", "email": "info@pressonlogistics.com",
    "address": "1951 Southampton Rd", "city_state": "Atlanta, GA 30349",
    "job_title": "Regional CDL-A Truck Driver", "pay_range": "$1,200 – $1,400 / week",
    "home_time": "Home weekly", "home_time_short": "Weekly", "home_time_detail": "Home 2 Days",
    "min_experience": "1 year", "fourth_card_value": "1 Yr. Exp", "fourth_card_label": "Min. Required",
    "routes": "Multi-State", "routes_type": "Regional Routes",
    "perks": ["Dental & Vision insurance", "401(k) with match", "Fuel card"],
}

failures = []

# Every studio must offer a wide palette pool (not the old 2).
pal_counts = {s: len(re_.THEMES[s]) for s in re_.THEMES}
if any(c < 8 for c in pal_counts.values()):
    failures.append(f"palette pool too small: {pal_counts}")

N = 40
studios, combos = [], []
for _ in range(N):
    data, d, theme, fh, fb, sf = re_._build_payload(INFO)
    studios.append(data["studio"]["id"])
    combos.append((data["studio"]["id"], theme["name"]))


def max_run(seq):
    m = c = 1
    for i in range(1, len(seq)):
        c = c + 1 if seq[i] == seq[i - 1] else 1
        m = max(m, c)
    return m


# No site may look like the one right before it (studio+palette).
b2b = sum(1 for i in range(1, len(combos)) if combos[i] == combos[i - 1])
if b2b:
    failures.append(f"{b2b} back-to-back identical studio+palette combos")

# Rotation (keep=4) means a studio can't repeat immediately.
run = max_run(studios)
if run > 2:
    failures.append(f"studio repeated {run}x in a row (rotation not working)")

# Strong overall variety across many generations.
uniq = len(set(combos))
if uniq < N - 4:
    failures.append(f"variation too low: only {uniq}/{N} unique studio+palette combos")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print(f"PASS: studio/palette rotation — {uniq}/{N} unique, 0 back-to-back, max studio run {run}")
