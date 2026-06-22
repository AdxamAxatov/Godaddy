import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from website_generator import generate_job_description

# Two route types so both OTR/Regional branches and all lengths/tones are hit.
INFOS = [
    {
        "company_name": "Test Freight LLC",
        "city_state": "Dallas, TX 75001",
        "pay_range": "$1,400 – $1,700 / week",
        "home_time": "Home every 2 weeks for 3 days",
        "perks": ["401(k) with match", "Health insurance", "Paid time off"],
        "min_experience": "1 year",
        "routes_type": "OTR Routes",
        "sign_on_bonus": "$2,000",
    },
    {
        "company_name": "Summit Carriers Inc",
        "city_state": "Columbus, OH 43004",
        "pay_range": "$1,250 – $1,500 / week",
        "home_time": "Home weekly",
        "perks": ["Dental & Vision insurance", "Fuel card", "Referral program"],
        "min_experience": "6 months",
        "routes_type": "Regional Routes",
    },
]

# ── Indeed: never route applying off-platform; no misleading time guarantees ──
BANNED = [
    "within 24 hours", "reach out within", "we'll be in touch", "let's talk",
    "call us", "text us", "call or text", "email your resume", "email us",
    "give us a call", "apply at our website", "apply on our site",
    # misleading compensation language Indeed flags
    "up to $", "guaranteed pay", "guaranteed income", "unlimited earning",
    "unlimited income", "make $$$",
    # email/handle marker
    "@",
]
PHONE = re.compile(r"\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b")
URL = re.compile(r"https?://|www\.|\.com\b|\.net\b|\.org\b", re.I)
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
ALLCAPS = re.compile(r"\b[A-Z]{5,}\b")            # shouting words (acronyms are <=4 + FMCSA)
ALLCAPS_OK = {"FMCSA"}
PUNCT_SPAM = re.compile(r"[!]{1}|[?]{2,}|[.]{4,}|\${2,}")  # any "!", or runs of ?/./$

# Discrimination / coded language Indeed + EEOC prohibit.
CODED = [
    "recent grad", "young", "younger", "energetic team", "native english",
    "native speaker", "men only", "women only", "girls", "boys",
    "he/she must", "salesman", "us citizen only", "citizens only",
]

# Elements every compliant posting must contain.
def _required_present(jd, info):
    low = jd.lower()
    return (
        info["pay_range"] in jd
        and ("cdl" in low or "class a commercial driver" in low)
        and "21" in jd                       # federal age requirement stated
        and "dot medical" in low
        and ("equal opportunity employer" in low or "equal employment opportunit" in low)
        and jd.lstrip().startswith("<p>")    # intro first
        and jd.rstrip().endswith("</i></p>") # EEO last
    )

failures = []
N = 600
for i in range(N):
    info = INFOS[i % len(INFOS)]
    jd = generate_job_description(info)
    low = jd.lower()

    for phrase in BANNED:
        if phrase in low:
            failures.append(f"iter {i}: banned phrase {phrase!r}")
    for phrase in CODED:
        if phrase in low:
            failures.append(f"iter {i}: coded/discriminatory phrase {phrase!r}")
    if PHONE.search(jd):
        failures.append(f"iter {i}: phone number present")
    if URL.search(jd):
        failures.append(f"iter {i}: URL / external link present")
    if EMOJI.search(jd):
        failures.append(f"iter {i}: emoji present")
    if PUNCT_SPAM.search(jd):
        failures.append(f"iter {i}: spammy punctuation present")
    bad_caps = [w for w in ALLCAPS.findall(jd) if w not in ALLCAPS_OK]
    if bad_caps:
        failures.append(f"iter {i}: ALL-CAPS shouting {bad_caps[:3]}")
    if not _required_present(jd, info):
        failures.append(f"iter {i}: missing a required element (pay/CDL/21+/DOT med/EEO/order)")
    # keyword-stuffing guard: no key phrase repeated excessively
    for term, cap in (("cdl", 8), ("freight", 9), ("dry van", 7)):
        if low.count(term) > cap:
            failures.append(f"iter {i}: keyword stuffing {term!r} x{low.count(term)}")

# Variation guard: across many runs the output should genuinely differ.
seen = Counter(generate_job_description(INFOS[0]) for _ in range(200))
if seen.most_common(1)[0][1] > 3:
    failures.append(f"variation too low: a single posting repeated {seen.most_common(1)[0][1]}x in 200")
if len(seen) < 150:
    failures.append(f"variation too low: only {len(seen)} unique postings in 200 runs")

if failures:
    for f in failures[:15]:
        print("FAIL:", f)
    print(f"... {len(failures)} total failures")
    sys.exit(1)
print(f"PASS: {N} samples compliant; {len(seen)}/200 unique postings; all guardrails clean")
