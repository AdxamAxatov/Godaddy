import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from website_generator import generate_job_description

INFO = {
    "company_name": "Test Freight LLC",
    "city_state": "Dallas, TX 75001",
    "pay_range": "$1,400 – $1,700 / week",
    "home_time": "Home every 2 weeks for 3 days",
    "perks": ["401(k) with match", "Health insurance", "Paid time off"],
    "min_experience": "1 year",
    "routes_type": "OTR Routes",
}

# Indeed flags postings that route applying off-platform or make misleading
# guarantees. These phrases must never appear in a generated description.
BANNED = [
    "reach out within 24 hours",
    "within 24 hours",
    "we'll be in touch",
    "let's talk",
    "call us",
    "text us",
    "email your resume",
    "@",          # no email addresses / handles in the body
]
PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")

failures = []
# Generate many to cover the random tone / CTA / optional-block branches.
for i in range(400):
    jd = generate_job_description(INFO)
    low = jd.lower()
    for phrase in BANNED:
        if phrase in low:
            failures.append(f"iter {i}: banned phrase {phrase!r} present")
            break
    if PHONE.search(jd):
        failures.append(f"iter {i}: phone-number-as-apply-channel present")

if failures:
    for f in failures[:10]:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: generated job descriptions have no off-platform/guarantee CTAs (400 samples)")
