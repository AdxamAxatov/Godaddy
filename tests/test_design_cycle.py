import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import react_engine as R

failures = []

# 1) Exactly 50 designs, all distinct on their full signature.
if len(R.DESIGNS) != 50:
    failures.append(f"expected 50 designs, got {len(R.DESIGNS)}")

def sig(d):
    return (d["mode"], d["hue"], d["scheme"], d["radius"], d["family"],
            tuple(sorted(d["variants"].items())), tuple(d["order"]))

uniq = len({sig(d) for d in R.DESIGNS})
if uniq != len(R.DESIGNS):
    failures.append(f"designs not all distinct: {uniq}/{len(R.DESIGNS)} unique")

# 2) Consecutive designs must differ in EVERY loud lever (what a human notices
#    first): light/dark mode, hero archetype, font family, brand hue.
loud = [(d["mode"], d["variants"]["hero"], d["family"], d["hue"]) for d in R.DESIGNS]
for k, (a, b) in enumerate(zip(loud, loud[1:] + [loud[0]])):
    for name, x, y in zip(("mode", "hero", "family", "hue"), a, b):
        if x == y:
            failures.append(f"design {k}->{(k+1) % 50} share {name}={x}")

# 3) The cyclic counter visits 0..49 in order and wraps, using a temp state file.
state = R._DESIGN_INDEX_FILE
backup = None
if os.path.exists(state):
    with open(state) as f:
        backup = f.read()
    os.remove(state)
try:
    seq = [R._next_design_index(50) for _ in range(52)]
    if seq[:50] != list(range(50)):
        failures.append("counter did not ascend 0..49 in order")
    if seq[50] != 0 or seq[51] != 1:
        failures.append(f"counter did not wrap after 49 (got {seq[50]}, {seq[51]})")
finally:
    if backup is not None:
        with open(state, "w") as f:
            f.write(backup)
    elif os.path.exists(state):
        os.remove(state)

# 4) Every variant value a design emits must be one the engine actually supports.
VALID = {
    "nav": {"rule", "solid", "floating"},
    "hero": {"editorial", "split", "cinematic", "centered"},
    "stats": {"ledger", "strip"},
    "freight": {"cards", "list", "split"},
    "careers": {"list", "accordion"},
    "about": {"splitL", "splitR", "fullbleed", "centered"},
    "process": {"timeline", "numbered"},
    "showcase": {"marquee", "frame", "grid"},
    "testimonials": {"pull", "cards"},
    "footer": {"wordmark", "columns", "minimal"},
}
for d in R.DESIGNS:
    for slot, val in d["variants"].items():
        if val not in VALID.get(slot, {val}):
            failures.append(f"{d['id']} has invalid {slot}={val}")
    # spine sections always present so the site always sells + recruits
    for must in ("services", "about", "careers"):
        if must not in d["order"]:
            failures.append(f"{d['id']} order missing spine section {must}")

if failures:
    for f in failures[:12]:
        print("FAIL:", f)
    print(f"... {len(failures)} total")
    sys.exit(1)
print("PASS: 50 distinct designs, every neighbour differs in mode/hero/family/hue, "
      "counter cycles 0..49 and wraps, all variants valid")
