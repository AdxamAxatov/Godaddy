import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import company_lookup as cl

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# 1. Unique match, suffix included.
r = cl.lookup("info@ptttransportationllc.com")
check(len(r) == 1, f"ptttransportationllc: expected 1 match, got {len(r)}")
check(r and r[0]["legal_name"] == "PTT TRANSPORTATION LLC",
      f"ptttransportationllc: wrong name {r}")

# 2. Same company matches with the LLC suffix DROPPED from the domain.
r = cl.lookup("info@ptttransportation.com")
check(len(r) == 1 and r[0]["legal_name"] == "PTT TRANSPORTATION LLC",
      f"ptttransportation (no suffix): expected unique PTT match, got {r}")

# 3. Address parsed into street + 'CITY, ST ZIP', whitespace normalized.
r = cl.lookup("info@ptttransportationllc.com")
cs = r[0]["city_state"]
check("," in cs, f"city_state missing comma: {cs!r}")
check(r[0]["address"] != "", f"street address empty: {r[0]}")
check("\xa0" not in cs and "  " not in cs, f"city_state not whitespace-normalized: {cs!r}")

# 4. '&' in the name still matches a domain that drops it (D&G -> dg).
r = cl.lookup("info@dgtransportinc.com")
check(len(r) >= 2, f"dgtransportinc: expected >=2 (ambiguous), got {len(r)}")
check(all("&" in rec["legal_name"] for rec in r),
      f"dgtransportinc: expected D&G records, got {[x['legal_name'] for x in r]}")
check(len({rec["city_state"] for rec in r}) >= 2,
      f"dgtransportinc: expected distinct cities, got {[x['city_state'] for x in r]}")

# 5. No match -> empty list.
r = cl.lookup("info@zzznotarealcompanyxyz.com")
check(r == [], f"bogus domain: expected [], got {r}")

# 6. Bare domain (no @) also works.
r = cl.lookup("ptttransportationllc.com")
check(len(r) == 1, f"bare domain: expected 1, got {len(r)}")

if failures:
    for f in failures:
        print("FAIL:", f)
    sys.exit(1)
print("PASS: company_lookup matches suffix/&/ambiguous/no-match correctly")
