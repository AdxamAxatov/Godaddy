"""
React studio engine — art-directed, never-repeating single-file React sites.

Each `render_site(info)` emits ONE self-contained index.html using the real
modern stack with **no build step** (deploys through the existing zip -> cPanel
static pipeline):

  • React 18            (esm.sh ES modules)
  • Framer Motion       (esm.sh — reveal / stagger / parallax / magnetic / marquee)
  • Tailwind CSS        (Play CDN — utilities generated at runtime)
  • Babel standalone    (transpiles inline JSX in the browser)
  • shadcn-style UI kit  (Button / Card / Badge / Input … hand-built in JSX)

Design philosophy (why it doesn't look "AI generated"):
  - CURATED, restrained palettes — never random neon.
  - Typography as the hero: oversized display, editorial index numerals,
    letter-spaced labels, serif/sans contrast.
  - No tiny icon-card grids — editorial numbered lists & interactive accordions.
  - Asymmetry: offset heads, sticky side-rail labels, full-bleed photo bands.
  - Photographic grade (duotone tint + grain + scrims) unifies stock into a brand.
  - Craft: benefits marquee, credential bar, monogram, big footer wordmark.

Reuses studio_engine._build_data for copy/images; preserves the breakout-safe
<script id="company-data"> embed so /appeal + CSV-autofill keep working.

render_site(info) -> (html, ctx); ctx carries image filenames for the zip.
"""

import colorsys
import json
import os
import random

from studio_engine import _build_data, _company_data, _ICON_PATHS, _fmt
from website_generator import _company_data_script

# ── No-repeat rotation for studio layout + palette ────────────────────────────
# Plain random.choice over 6 studios with replacement makes look-alikes (and
# even back-to-back repeats) common. Mirror the image picker: persist recently
# used studios/palettes and pick around them so each site differs until the pool
# cycles. Best-effort; never breaks rendering on a state-file error.
_ROT_STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "last_used_studios.json")


def _load_rot_state():
    try:
        with open(_ROT_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError, OSError):
        return {}


def _save_rot_state(state):
    try:
        os.makedirs(os.path.dirname(_ROT_STATE_FILE), exist_ok=True)
        with open(_ROT_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def _rotate_pick(options, recent, keep):
    """Pick from `options` avoiding the `recent` list; update recent in place
    (keeping the last `keep`). Falls back to the full pool once exhausted."""
    candidates = [o for o in options if o not in recent] or list(options)
    pick = random.choice(candidates)
    recent.append(pick)
    if len(recent) > keep:
        del recent[: len(recent) - keep]
    return pick


def _rgb(h):
    h = h.lstrip("#")
    return "%d,%d,%d" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# ─────────────────────────────────────────────────────────────────────────────
# Curated, art-directed themes (sophisticated palettes only — no neon)
# keys: mode bg surface s2 text muted border primary primary2 accent on radius grain
# ─────────────────────────────────────────────────────────────────────────────

def T(name, mode, bg, surface, s2, text, muted, border, primary, primary2, accent, on, radius, grain=0.0):
    return {"name": name, "mode": mode, "bg": bg, "surface": surface, "surface-2": s2,
            "text": text, "muted": muted, "border": border, "primary": primary,
            "primary-2": primary2, "accent": accent, "on-primary": on,
            "radius": radius, "grain": grain, "prgb": _rgb(primary), "argb": _rgb(accent)}


THEMES = {
    # editorial / magazine — ink on warm paper, terracotta accent
    "press": [
        T("ink-paper", "light", "#F4F1EA", "#FBF9F4", "#ECE7DB", "#16130F", "#6B6157",
          "#E0D8C9", "#1A1714", "#3A332C", "#B5462F", "#FBF9F4", "2px", 0.05),
        T("cream-oxblood", "light", "#F6F3EC", "#FFFFFF", "#EEE8DC", "#1C1A16", "#6A625A",
          "#E4DCCD", "#7A1F2B", "#5A1620", "#B5462F", "#FFFFFF", "2px", 0.05),
    ],
    # luxury minimal — bone + deep green / gold
    "lumen": [
        T("forest-bone", "light", "#F3F4EF", "#FFFFFF", "#E9ECE2", "#1A1E18", "#5F665A",
          "#DDE0D4", "#2C3A2A", "#3E5236", "#B08D57", "#FFFFFF", "6px", 0.03),
        T("graphite-gold", "light", "#F5F4F1", "#FFFFFF", "#ECEAE4", "#1B1A17", "#67625A",
          "#E2DED4", "#1C1B19", "#3A3833", "#B08D57", "#FFFFFF", "6px", 0.03),
    ],
    # automotive premium — midnight + copper
    "apex": [
        T("midnight-copper", "dark", "#0C0C0E", "#151517", "#1F1F22", "#EFEBE3", "#938E84",
          "#262428", "#C97B4A", "#E0925B", "#C97B4A", "#0C0C0E", "4px", 0.05),
        T("carbon-amber", "dark", "#0E0E10", "#17171A", "#212126", "#F0EEE9", "#908B83",
          "#262529", "#E0962B", "#F2B24B", "#E0962B", "#0E0E10", "4px", 0.05),
    ],
    # futuristic enterprise — slate + restrained electric blue
    "nebula": [
        T("slate-electric", "dark", "#0A0C10", "#12151B", "#1B1F27", "#EAEEF5", "#8893A3",
          "#20252E", "#4D7DF6", "#7AA0FF", "#36E0C2", "#0A0C10", "12px", 0.05),
        T("obsidian-azure", "dark", "#08090C", "#10131A", "#181C24", "#E8EDF6", "#828D9E",
          "#1D222B", "#3D9BFF", "#6FC0FF", "#7C7CFF", "#08090C", "12px", 0.05),
    ],
    # modern SaaS — clean light, confident blue/indigo (restrained)
    "atlas": [
        T("porcelain-indigo", "light", "#F7F8FC", "#FFFFFF", "#EFF2F8", "#0E1322", "#5A6173",
          "#E4E8F1", "#3B5BDB", "#5B4BFF", "#0CA678", "#FFFFFF", "12px", 0.0),
        T("mist-teal", "light", "#F4F8F8", "#FFFFFF", "#E8F1F0", "#0B1A19", "#566863",
          "#DCE8E6", "#0E8074", "#13A29A", "#3B5BDB", "#FFFFFF", "12px", 0.0),
    ],
    # industrial — graphite + safety amber
    "forge": [
        T("graphite-amber", "dark", "#0E0E10", "#171719", "#202023", "#F0EEE9", "#8E8980",
          "#262529", "#E08A1E", "#F2A63E", "#E08A1E", "#0E0E10", "2px", 0.06),
        T("concrete-rust", "light", "#EFEDE7", "#FBFAF6", "#E4E1D8", "#141312", "#5C574E",
          "#D8D3C7", "#B24A1E", "#CC5E2E", "#141312", "#FBFAF6", "2px", 0.05),
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# Color-theory engine — palettes derived from a brand hue + harmony scheme,
# with temperature-tinted neutrals and WCAG-validated contrast.
# This OVERRIDES the curated THEMES above with theory-grounded equivalents.
# ─────────────────────────────────────────────────────────────────────────────

def _hsl_rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, max(0, min(1, l / 100.0)), max(0, min(1, s / 100.0)))
    return (round(r * 255), round(g * 255), round(b * 255))


def _hx(h, s, l):
    return "#%02X%02X%02X" % _hsl_rgb(h, s, l)


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(rgb):
    r, g, b = (_lin(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b):
    la, lb = _lum(a), _lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# harmony schemes: hue offset of the accent from the brand hue
_SCHEME = {"complementary": 180, "analogous": 30, "triadic": 120, "split": 150, "monochrome": 0}


def _nudge_l(h, s, l, bg_rgb, target, mode, step=2):
    """Push lightness until text/element clears the WCAG contrast target vs bg."""
    for _ in range(60):
        if _contrast(_hsl_rgb(h, s, l), bg_rgb) >= target:
            break
        l = min(100, l + step) if mode == "dark" else max(0, l - step)
    return l


def _theory_theme(hue, scheme, radius, grain, mode):
    ah = hue + _SCHEME.get(scheme, 150)          # accent hue via harmony rule
    if mode == "dark":
        ns = 12                                   # neutral saturation (tinted, not gray)
        bg = _hx(hue, ns, 6); bg2 = _hx(hue, ns, 9); surface = _hx(hue, ns - 2, 11); s2 = _hx(hue, ns - 3, 15)
        bgr = _hsl_rgb(hue, ns, 6)
        text = _hx(hue, 8, _nudge_l(hue, 8, 95, bgr, 12.0, "dark"))
        muted = _hx(hue, 10, _nudge_l(hue, 10, 62, bgr, 4.6, "dark"))
        border = _hx(hue, ns + 4, 20); border2 = _hx(hue, ns + 6, 26)
        pS, pL, aL = 74, 60, 62
    else:
        ns = 14
        bg = _hx(hue, ns + 14, 98); bg2 = _hx(hue, ns + 12, 96); surface = "#FFFFFF"; s2 = _hx(hue, ns + 16, 97)
        bgr = _hsl_rgb(hue, ns + 14, 98)
        text = _hx(hue, 26, _nudge_l(hue, 26, 14, bgr, 11.0, "light"))
        muted = _hx(hue, 12, _nudge_l(hue, 12, 44, bgr, 4.6, "light"))
        border = _hx(hue, ns, 89); border2 = _hx(hue, ns, 84)
        pS, pL, aL = 72, 48, 50
    # primary: ensure it reads against bg (icons/large text) — contrast >= 3
    pl = pL
    for _ in range(40):
        if _contrast(_hsl_rgb(hue, pS, pl), bgr) >= 3.0:
            break
        pl = min(100, pl + 3) if mode == "dark" else max(0, pl - 3)
    # guarantee button-label (on-primary) contrast >= 4.6 by moving primary L
    # away from the mid-luminance dead-zone (lighter favors black text, darker favors white)
    prgb = _hsl_rgb(hue, pS, pl)
    for _ in range(30):
        cb, cw = _contrast((11, 11, 14), prgb), _contrast((255, 255, 255), prgb)
        if max(cb, cw) >= 4.6:
            break
        pl = min(100, pl + 3) if cb >= cw else max(0, pl - 3)
        prgb = _hsl_rgb(hue, pS, pl)
    primary = _hx(hue, pS, pl)
    primary2 = _hx(hue + 18, pS, min(100, pl + (8 if mode == "dark" else 6)))
    accent = _hx(ah, 70, aL); argb = _hsl_rgb(ah, 70, aL)
    on = "#0B0B0E" if _contrast((11, 11, 14), prgb) >= _contrast((255, 255, 255), prgb) else "#FFFFFF"
    return {"name": "h%d-%s" % (int(hue) % 360, scheme), "mode": mode, "bg": bg, "surface": surface,
            "surface-2": s2, "text": text, "muted": muted, "border": border, "border2": border2,
            "primary": primary, "primary-2": primary2, "accent": accent, "on-primary": on,
            "radius": "%dpx" % radius, "grain": grain, "prgb": "%d,%d,%d" % prgb, "argb": "%d,%d,%d" % argb}


# Each studio keeps its signature character — (mode, radius, grain, harmony
# scheme) — but its palette is generated across a WIDE spread of brand hues so
# two sites on the same layout still differ clearly in color. The contrast
# engine keeps every hue readable (curated, not neon). This + rotation is what
# stops generated sites from looking alike.
_STUDIO_STYLE = {
    # studio:  (mode,    radius, grain, scheme)
    "press":  ("light",  2,  0.05, "analogous"),    # editorial magazine, warm
    "lumen":  ("light",  6,  0.03, "split"),        # luxury minimal, calm
    "apex":   ("dark",   4,  0.05, "monochrome"),   # automotive premium
    "nebula": ("dark",   12, 0.05, "triadic"),      # futuristic enterprise
    "atlas":  ("light",  12, 0.0,  "split"),        # modern SaaS
    "forge":  ("dark",   2,  0.06, "analogous"),    # dark industrial
}
# Curated hue spread (skips muddy yellow-greens ~60-85); 11 hues × 6 studios.
_PALETTE_HUES = [8, 24, 42, 96, 150, 175, 200, 224, 258, 292, 330]
THEMES = {sid: [_theory_theme(h, sch, rad, gr, mode) for h in _PALETTE_HUES]
          for sid, (mode, rad, gr, sch) in _STUDIO_STYLE.items()}


# studio presets — each a distinct art direction
PRESETS = [
    {"id": "press", "label": "editorial magazine", "fonts": "serif",
     "v": {"nav": "rule", "hero": "editorial", "stats": "ledger", "services": "list",
           "process": "numbered", "showcase": "frame", "testimonials": "pull"},
     "order": ["services", "coverage", "stats", "about", "showcase", "careers", "process", "testimonials"]},
    {"id": "lumen", "label": "luxury minimal", "fonts": "serif",
     "v": {"nav": "solid", "hero": "split", "stats": "ledger", "services": "accordion",
           "process": "timeline", "showcase": "marquee", "testimonials": "pull"},
     "order": ["about", "services", "coverage", "stats", "showcase", "careers", "process", "testimonials"]},
    {"id": "apex", "label": "automotive premium", "fonts": "display",
     "v": {"nav": "solid", "hero": "cinematic", "stats": "strip", "services": "list",
           "process": "timeline", "showcase": "grid", "testimonials": "pull"},
     "order": ["services", "showcase", "coverage", "stats", "about", "careers", "process", "testimonials"]},
    {"id": "nebula", "label": "futuristic enterprise", "fonts": "grotesk",
     "v": {"nav": "floating", "hero": "centered", "stats": "strip", "services": "accordion",
           "process": "timeline", "showcase": "grid", "testimonials": "cards"},
     "order": ["services", "coverage", "stats", "about", "showcase", "careers", "process", "testimonials"]},
    {"id": "atlas", "label": "modern SaaS", "fonts": "grotesk",
     "v": {"nav": "floating", "hero": "centered", "stats": "strip", "services": "list",
           "process": "numbered", "showcase": "grid", "testimonials": "cards"},
     "order": ["services", "stats", "coverage", "about", "showcase", "careers", "process", "testimonials"]},
    {"id": "forge", "label": "dark industrial", "fonts": "display",
     "v": {"nav": "rule", "hero": "editorial", "stats": "ledger", "services": "list",
           "process": "numbered", "showcase": "frame", "testimonials": "cards"},
     "order": ["services", "coverage", "showcase", "stats", "about", "careers", "process", "testimonials"]},
]

_FONTS = {
    "grotesk": [("Space Grotesk", "Inter"), ("Sora", "Inter"), ("Plus Jakarta Sans", "Inter"),
                ("Outfit", "Inter"), ("Manrope", "Inter")],
    "display": [("Archivo", "Inter"), ("Bricolage Grotesque", "Inter"), ("Syne", "Inter")],
    "serif":   [("Fraunces", "Inter"), ("Playfair Display", "Inter"),
                ("Libre Caslon Display", "Inter"), ("Instrument Serif", "Inter")],
}
_WEIGHTS = {
    "Space Grotesk": "400;500;600;700", "Sora": "400;500;600;700;800",
    "Plus Jakarta Sans": "400;500;600;700;800", "Outfit": "300;400;500;600;700;800",
    "Manrope": "400;500;600;700;800", "Archivo": "400;500;600;700;800;900",
    "Bricolage Grotesque": "400;500;600;700;800", "Syne": "500;600;700;800",
    "Fraunces": "opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,900",
    "Playfair Display": "400;500;600;700;800;900", "Libre Caslon Display": "400",
    "Instrument Serif": "400", "Inter": "400;500;600;700",
    "Caveat": "500;600;700", "Dancing Script": "500;600;700",
}

# flowing script fonts for the mixed-font hero accent word (21st.dev-style)
_SCRIPTS = ["Caveat", "Dancing Script"]

# short script-accent headline mixes for the centered hero
_HERO_MIX = [
    {"lead": "Drive your best", "accent": "miles yet"},
    {"lead": "More money, more miles,", "accent": "more home"},
    {"lead": "The driving job", "accent": "you’ve earned"},
    {"lead": "Real freight,", "accent": "real home time"},
    {"lead": "Your next mile", "accent": "starts here"},
]


def _gfont(name):
    w = _WEIGHTS.get(name, "400;500;600;700")
    fam = name.replace(" ", "+")
    return "family=" + fam + (":" + w if "opsz" in w else ":wght@" + w)


_SHOWCASE = [
    ("Late-model fleet", "Spec'd for the long haul"),
    ("Miles that pay", "Steady freight, every week"),
    ("Built-in coverage", "Lanes designed around drivers"),
    ("Real home time", "Back when we promise"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Carrier content — the pivot: make the site read as a real operating freight
# carrier (broker-credible) that ALSO recruits drivers. Soft credibility signals
# only — never a DOT/MC number a broker could fail to find in FMCSA.
# ─────────────────────────────────────────────────────────────────────────────

# extra line-icons for freight service lines (merged into _ICON_PATHS at build)
_CARRIER_ICONS = {
    "box":     '<path d="M3 7l9-4 9 4v10l-9 4-9-4z"/><path d="M3 7l9 4 9-4"/><path d="M12 11v10"/>',
    "snow":    '<path d="M12 2v20M4 6l16 12M20 6L4 18"/><path d="M9 4l3 2 3-2M9 20l3-2 3 2"/>',
    "layers":  '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "pin":     '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    "headset": '<path d="M4 13a8 8 0 0 1 16 0"/><path d="M4 13v3a2 2 0 0 0 2 2h1v-6H6a2 2 0 0 0-2 2z"/><path d="M20 13v3a2 2 0 0 1-2 2h-1v-6h1a2 2 0 0 1 2 2z"/>',
    "gauge":   '<path d="M12 13l5-3"/><path d="M3.5 17a9 9 0 1 1 17 0"/><circle cx="12" cy="13" r="1.5"/>',
    "check":   '<path d="M20 6L9 17l-5-5"/>',
}

# freight service lines (pick 6) — what a real carrier sells to shippers
_FREIGHT_SERVICES = [
    ("box", "Dry Van", "Our core service — secure, weather-protected trailers for general palletized and packaged freight on dependable schedules."),
    ("snow", "Refrigerated", "Temperature-controlled reefer capacity for food, beverage and other perishable freight, monitored end to end."),
    ("layers", "Flatbed & Step-Deck", "Open-deck capacity for building materials, machinery and oversized loads, secured to spec by experienced drivers."),
    ("route", "Dedicated Lanes", "Committed equipment and drivers on your recurring lanes for consistent transit times and capacity you can plan around."),
    ("bolt", "Expedited & Team", "Time-critical freight moved with team drivers and direct routing when a load absolutely has to be there."),
    ("truck", "Intermodal & Drayage", "Port, rail and container drayage that bridges the first and last mile of your intermodal moves."),
    ("chart", "LTL & Partial", "Cost-efficient less-than-truckload and partial options that get smaller shipments moving without paying for empty space."),
    ("clock", "Just-in-Time", "Scheduled, appointment-based delivery that keeps production lines and retail shelves supplied on time."),
    ("shield", "Warehousing & 3PL", "Short-term storage, cross-docking and managed transportation that extend your supply chain beyond the trailer."),
]

# coverage / network regions (pick 4-5) — soft, no terminal addresses
_COVERAGE_REGIONS = [
    ("Southeast & Gulf", "Atlanta, Dallas and the I-10/I-75 corridors"),
    ("Midwest & Great Lakes", "Chicago, Columbus and the manufacturing belt"),
    ("Northeast Corridor", "I-95 metro markets from DC to Boston"),
    ("Texas Triangle", "Dallas, Houston and San Antonio freight"),
    ("Mountain & West", "Denver, Salt Lake and the I-80 run"),
    ("West Coast", "California, the Pacific Northwest and port drayage"),
    ("Plains & Central", "Kansas City, Omaha and cross-country OTR"),
]

# about / safety soft-signal points — credibility without lookup-able numbers
_SAFETY_POINTS = [
    "Fully licensed, bonded & insured",
    "Late-model, regularly inspected fleet",
    "Safety-first culture & ongoing driver training",
    "Real-time tracking & 24/7 dispatch",
    "Experienced operations & compliance team",
    "Proactive preventive-maintenance program",
    "Cargo & liability coverage on every load",
    "Hours-of-service & ELD compliant",
]

# carrier-first hero copy (company as a freight carrier, with a hiring hook)
_CARRIER_HEADLINES = [
    "Freight that moves\non time. Every time.",
    "Your freight.\nOur commitment.",
    "Reliable capacity.\nReal accountability.",
    "Moving freight,\nmile by mile.",
    "Driven to deliver.\nBuilt on safety.",
]
_CARRIER_SUBHEADS = [
    "{company} is a {city}-based motor carrier moving dry van, refrigerated and specialized freight across {coverageArea} — backed by a modern fleet and a dispatch team that answers the phone.",
    "From a single lane to a dedicated fleet, {company} delivers dependable capacity, on-time transit and the communication shippers actually want.",
    "Licensed, insured and built on safety, {company} keeps freight moving across {coverageArea} with newer equipment and experienced professional drivers.",
    "{company} pairs asset-based capacity with real accountability — so your freight is covered, tracked and delivered when we say it will be.",
]
_CARRIER_KICKERS = [
    "Freight & Logistics", "Asset-Based Motor Carrier", "{cityState}",
    "Licensed & Insured Carrier", "Now Serving {routes}",
]
_CARRIER_HERO_MIX = [
    {"lead": "Freight that moves", "accent": "on time"},
    {"lead": "Capacity you can", "accent": "count on"},
    {"lead": "Your freight,", "accent": "delivered"},
    {"lead": "Built on safety,", "accent": "driven to deliver"},
]
_CARRIER_ABOUT_TITLES = [
    "A carrier built on accountability",
    "Freight handled the right way",
    "The carrier behind your freight",
    "Capacity, safety and real communication",
]
_CARRIER_ABOUT_P1 = [
    "{company} was built by people who understand freight. We run a modern, well-maintained fleet and treat every shipment — and every driver — like it matters.",
    "Out of {cityState}, {company} keeps freight moving with safety-first operations, real-time tracking and a dispatch team available around the clock.",
    "From a single committed lane to a dedicated fleet, {company} delivers the dependable capacity and on-time transit your supply chain depends on.",
]
_CARRIER_ABOUT_P2 = [
    "Licensed, bonded and fully insured, we pair asset-based capacity with the kind of communication that turns a vendor into a partner.",
    "Our drivers stay because we invest in equipment, safety and pay — and that consistency is exactly what our shippers feel on every load.",
    "No black boxes and no runaround: clear updates, proactive maintenance, and freight that arrives when we promise it will.",
]
_CARRIER_CTA_TITLES = [
    "Let's keep your freight moving",
    "Ready to put us on your lanes?",
    "Drive with us or ship with us",
    "Get capacity you can count on",
]
_CARRIER_CTA_SUBS = [
    "Shippers: tell us about your freight and we'll get back to you with capacity. Drivers: apply below and a recruiter will call within one business day.",
    "Whether you're moving freight or looking to drive it, reach out — a real person will get back to you fast.",
    "From your first load to your first mile, {company} is ready when you are. Send us a note to get started.",
]


# ── Structural archetypes ─────────────────────────────────────────────────────
# Studio = visual treatment; archetype = STRUCTURE (which sections, how many,
# how long). Independent + rotated, so two sites differ in shape, not just paint.
# Real carrier homepages range from lean ~6-block brochures to ~18-block corporate
# scrolls; the mid-body is a shuffleable/optional pool. A 3-section spine
# (services + about + careers) is always kept so every site still sells the
# carrier AND recruits; everything else varies.
_SPINE = ["services", "about", "careers"]
_OPTIONAL = ["coverage", "stats", "showcase", "process", "testimonials"]
_ARCHETYPES = {
    "lean":       {"mid": (3, 4), "ticker": 0.15},   # tight brochure
    "recruiting": {"mid": (4, 5), "ticker": 0.35},   # driver-forward
    "mixed":      {"mid": (5, 6), "ticker": 0.50},   # shipper + driver
    "corporate":  {"mid": (7, 8), "ticker": 0.85},   # long full scroll
}
# label/anchor for sections that earn a nav link (supporting sections don't)
_NAV_LABELS = [("services", "Services", "#services"), ("coverage", "Coverage", "#coverage"),
               ("about", "About", "#about"), ("careers", "Careers", "#careers")]


# Layout variants are now chosen INDEPENDENTLY per generation (not locked to the
# studio), so the "bones" — nav, hero, each section's layout, footer — vary site
# to site instead of being one of 6 fixed combos.
_VARIANTS = {
    "nav": ["rule", "solid", "floating"],
    "hero": ["editorial", "split", "cinematic", "centered"],
    "stats": ["ledger", "strip"],
    "freight": ["cards", "list", "split"],
    "careers": ["list", "accordion"],
    "about": ["splitL", "splitR", "fullbleed", "centered"],
    "process": ["timeline", "numbered"],
    "showcase": ["marquee", "frame", "grid"],
    "testimonials": ["pull", "cards"],
    "footer": ["wordmark", "columns", "minimal"],
}


def _pick_variants():
    return {k: random.choice(opts) for k, opts in _VARIANTS.items()}


def _compose_structure(rot):
    """Pick a rotated archetype and build a varied section order + ticker flag.
    Returns (archetype, order, show_ticker)."""
    arch_recent = rot.get("archetypes", [])
    arch = _rotate_pick(list(_ARCHETYPES), arch_recent, keep=2)
    rot["archetypes"] = arch_recent
    spec = _ARCHETYPES[arch]
    target = random.randint(*spec["mid"])
    fill_n = max(0, target - len(_SPINE))
    fill = random.sample(_OPTIONAL, min(fill_n, len(_OPTIONAL)))
    order = _SPINE + fill
    random.shuffle(order)
    return arch, order, random.random() < spec["ticker"]


# ─────────────────────────────────────────────────────────────────────────────
# 50 FIXED DESIGNS, cycled in order
# Each generation uses the next design in a deterministic ascending cycle, so
# consecutive sites ALWAYS differ and all 50 distinct looks appear before any
# repeat. Each design pins every high-impact lever — mode (light/dark), hero
# archetype, font family + pair, brand hue, corner radius, colour-harmony scheme,
# nav style, each section's layout, and the section order. Only copy / images /
# which freight & coverage items appear still randomise per company, so the same
# design renders as a believable (and still varied) trucking site for any client.
# The list is built with index-seeded RNG → identical on every import/run.
# ─────────────────────────────────────────────────────────────────────────────
_DESIGN_INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "last_design_index.json")

_D_MODES    = ["light", "dark"]
_D_HEROES   = ["editorial", "split", "cinematic", "centered"]
_D_NAVS     = ["rule", "solid", "floating"]
_D_ABOUTS   = ["splitL", "splitR", "fullbleed", "centered"]
_D_FREIGHT  = ["cards", "list", "split"]
_D_SHOW     = ["marquee", "frame", "grid"]
_D_FOOT     = ["wordmark", "columns", "minimal"]
_D_SCHEMES  = ["complementary", "analogous", "triadic", "split", "monochrome"]
_D_RADII    = [0, 2, 4, 8, 12, 16]
_D_GRAINS   = [0.0, 0.03, 0.05, 0.06]
_D_FAMILIES = ["serif", "display", "grotesk"]
# curated brand hues (skips muddy yellow-greens ~60-90); ordered so a *7 stride
# lands big colour hops between neighbours.
_D_HUES = [8, 210, 145, 28, 265, 175, 330, 100, 248, 18,
           200, 292, 158, 42, 225, 308, 122, 188, 338, 52]


def _design_order(rng):
    """Deterministic-but-varied section order + ticker flag for one design."""
    arch = rng.choice(list(_ARCHETYPES))
    lo, hi = _ARCHETYPES[arch]["mid"]
    target = rng.randint(lo, hi)
    fill_n = max(0, target - len(_SPINE))
    fill = rng.sample(_OPTIONAL, min(fill_n, len(_OPTIONAL)))
    order = _SPINE + fill
    rng.shuffle(order)
    return order, rng.random() < _ARCHETYPES[arch]["ticker"], arch


def _build_designs(n=50):
    """Build the fixed list of n distinct designs. Strides are chosen so that
    neighbouring designs differ in the loudest levers (mode every step, hero
    every step, font family every step, hue in big hops)."""
    out = []
    for i in range(n):
        rng = random.Random(7001 + i * 13)   # stable, independent of global RNG
        fam = _D_FAMILIES[(i * 2) % 3]
        order, ticker, arch = _design_order(rng)
        variants = {
            "nav":          _D_NAVS[(i * 2) % 3],
            "hero":         _D_HEROES[(i * 3) % 4],
            "stats":        ["ledger", "strip"][i % 2],
            "freight":      _D_FREIGHT[(i * 2) % 3],
            "careers":      ["list", "accordion"][(i + 1) % 2],
            "about":        _D_ABOUTS[(i * 3) % 4],
            "process":      ["timeline", "numbered"][i % 2],
            "showcase":     _D_SHOW[(i * 2) % 3],
            "testimonials": ["pull", "cards"][(i + 1) % 2],
            "footer":       _D_FOOT[(i * 2) % 3],
        }
        out.append({
            "id": "d%02d" % i,
            "mode": _D_MODES[i % 2],
            "hue": _D_HUES[(i * 7) % len(_D_HUES)],
            "scheme": _D_SCHEMES[(i * 3) % 5],
            "radius": _D_RADII[(i * 5) % len(_D_RADII)],
            "grain": _D_GRAINS[i % 4],
            "family": fam,
            "font_pair": rng.choice(_FONTS[fam]),
            "script": rng.choice(_SCRIPTS),
            "variants": variants,
            "order": order, "ticker": ticker, "archetype": arch,
        })
    return out


DESIGNS = _build_designs()


def _next_design_index(n):
    """Current design index for this generation, then advance the cyclic counter
    (wraps at n). Plain ascending cycle 0..n-1 → no repeat until all n are used."""
    idx = 0
    try:
        with open(_DESIGN_INDEX_FILE, encoding="utf-8") as f:
            idx = int(json.load(f).get("next", 0)) % n
    except (FileNotFoundError, ValueError, OSError, TypeError, KeyError):
        idx = 0
    try:
        os.makedirs(os.path.dirname(_DESIGN_INDEX_FILE), exist_ok=True)
        with open(_DESIGN_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump({"next": (idx + 1) % n}, f)
    except OSError:
        pass
    return idx


def _build_payload(info):
    d = _build_data(info)
    # Deterministic 50-design cycle: each generation uses the NEXT fixed design,
    # so consecutive sites always differ and all 50 looks appear before any repeat.
    design = DESIGNS[_next_design_index(len(DESIGNS))]
    theme = _theory_theme(design["hue"], design["scheme"], design["radius"],
                          design["grain"], design["mode"])
    order = list(design["order"])
    show_ticker = design["ticker"]
    variants = design["variants"]
    fh, fb = design["font_pair"]
    sf = design["script"]
    hero_mix = random.choice(_HERO_MIX)

    imgs = [d["hero_src"], d["about_src"], d["coverage_src"], d["about2_src"]]
    showcase = [{"img": imgs[i], "title": _SHOWCASE[i][0], "sub": _SHOWCASE[i][1]} for i in range(4)]
    mono = "".join(w[0] for w in d["short"].split()[:2]).upper() or d["short"][:2].upper()

    # ── carrier framing: company as a real freight carrier that also recruits ──
    regional = "regional" in d["routes_type"].lower()
    coverage_area = "a multi-state regional network" if regional else "all 48 states"
    fmt = dict(d, coverageArea=coverage_area, cityState=d["city_state"])

    freight_pool = _FREIGHT_SERVICES[:]; random.shuffle(freight_pool)
    freight = [{"icon": ic, "title": t, "desc": de} for ic, t, de in freight_pool[:6]]

    regions_pool = _COVERAGE_REGIONS[:]; random.shuffle(regions_pool)
    regions = [{"name": n, "note": note} for n, note in regions_pool[:(4 if regional else 5)]]
    coverage_stats = [
        {"v": d["routes"], "l": "Coverage"}, {"v": "98%", "l": "On-Time Delivery"},
        {"v": "24/7", "l": "Dispatch & Tracking"}, {"v": "100%", "l": "No-Touch Freight"},
    ]
    safety_pool = _SAFETY_POINTS[:]; random.shuffle(safety_pool)
    safety = safety_pool[:6]

    # carrier-first hero / about / cta copy (overrides the recruiting-only copy)
    headline = _fmt(random.choice(_CARRIER_HEADLINES), fmt)
    subhead = _fmt(random.choice(_CARRIER_SUBHEADS), fmt)
    kicker = _fmt(random.choice(_CARRIER_KICKERS), fmt)
    hero_mix = random.choice(_CARRIER_HERO_MIX)
    about_title = _fmt(random.choice(_CARRIER_ABOUT_TITLES), fmt)
    about_p1 = _fmt(random.choice(_CARRIER_ABOUT_P1), fmt)
    about_p2 = _fmt(random.choice(_CARRIER_ABOUT_P2), fmt)
    cta_title = _fmt(random.choice(_CARRIER_CTA_TITLES), fmt)
    cta_sub = _fmt(random.choice(_CARRIER_CTA_SUBS), fmt)

    # nav reflects the sections actually present (logical order, not body order),
    # so links never point at a section that was composed out.
    nav = [(label, href) for key, label, href in _NAV_LABELS if key in order]
    nav.append(("Contact", "#contact"))

    icons = dict(_ICON_PATHS); icons.update(_CARRIER_ICONS)

    data = {
        "company": d["company"], "short": d["short"], "logoMain": d["logo_main"],
        "logoAccent": d["logo_accent"], "monogram": mono, "domain": d["domain"],
        "email": d["email"], "cityState": d["city_state"], "city": d["city"],
        "state": d["state"], "year": d["year"], "jobTitle": d["job_title"],
        "pay": d["pay_range"], "homeTime": d["home_time"], "homeShort": d["home_time_short"],
        "minExp": d["min_experience"], "routes": d["routes"], "routesType": d["routes_type"],
        "coverageArea": coverage_area,
        "headline": headline, "subhead": subhead, "kicker": kicker,
        "aboutTitle": about_title, "aboutP1": about_p1, "aboutP2": about_p2,
        "ctaTitle": cta_title, "ctaSub": cta_sub,
        "nav": [{"label": t, "href": h} for t, h in nav],
        "stats": [{"v": v, "l": l} for v, l in d["stats"]],
        "freight": freight,
        "coverage": {"regions": regions, "stats": coverage_stats},
        "safety": safety,
        "benefits": [{"icon": ic, "title": t, "desc": de} for ic, t, de in d["services"]],
        "process": [{"title": t, "desc": de} for t, de in d["process"]],
        "testimonials": [{"q": q, "n": n, "r": r} for q, n, r in d["testimonials"]],
        "perks": d["perks"], "showcase": showcase,
        "heroMix": hero_mix,
        "studio": {"id": design["id"], "label": "design " + design["id"], "variants": variants,
                   "order": order, "ticker": show_ticker, "archetype": design.get("archetype", ""),
                   "mode": theme["mode"], "fonts": design["family"]},
        "icons": icons,
    }
    return data, d, theme, fh, fb, sf


# ─────────────────────────────────────────────────────────────────────────────
# React application (static JSX; data via window.__DATA__)
# ─────────────────────────────────────────────────────────────────────────────

_APP_JSX = r"""
import React, { useRef, useState, useEffect } from "react";
import { createRoot } from "react-dom/client";
import { motion, useInView, useScroll, useTransform, useMotionValue, useSpring, animate, AnimatePresence } from "framer-motion";

const D = window.__DATA__;
const V = D.studio.variants;
const SERIF = D.studio.fonts === "serif";
const cn = (...a) => a.filter(Boolean).join(" ");
const EASE = [0.16, 1, 0.3, 1];
const nn = (i) => String(i).padStart(2, "0");

function Icon({ name, className }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
    dangerouslySetInnerHTML={{ __html: D.icons[name] || D.icons.bolt }} />;
}

/* shadcn-style primitives */
function Button({ variant = "default", size = "default", className, children, ...p }) {
  const base = "inline-flex items-center justify-center gap-2.5 whitespace-nowrap font-semibold tracking-tight transition-all duration-300 focus-visible:outline-none disabled:opacity-60 rounded-[var(--radius)]";
  const variants = {
    default: "bg-primary text-onp hover:brightness-[1.08] shadow-[0_14px_34px_-14px_rgba(var(--prgb),.7)]",
    outline: "border border-border bg-transparent text-text hover:bg-surface-2",
    ghost: "text-text hover:bg-surface-2",
  };
  const sizes = { default: "h-12 px-7 text-[15px]", lg: "h-[58px] px-9 text-base", sm: "h-10 px-5 text-sm" };
  return <button className={cn(base, variants[variant], sizes[size], className)} {...p}>{children}</button>;
}
function Card({ className, children, ...p }) {
  return <div className={cn("rounded-[calc(var(--radius)+6px)] border border-border bg-surface", className)} {...p}>{children}</div>;
}
const inputCls = "w-full rounded-[var(--radius)] border border-border bg-surface px-4 h-12 text-[15px] text-text outline-none transition focus:border-primary focus:ring-2 focus:ring-[rgba(var(--prgb),.16)]";

/* motion */
function Reveal({ children, className, y = 28, delay = 0, as = "div" }) {
  const M = motion[as] || motion.div;
  return <M className={className} initial={{ opacity: 0, y }} whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.8, ease: EASE, delay }}>{children}</M>;
}
function Lines({ text, className }) {
  // word-by-word mask reveal for big headlines
  const words = text.split("\n");
  return <span className={className}>{words.map((w, li) => <span key={li} className="block overflow-hidden">
    <motion.span className="block" initial={{ y: "110%" }} whileInView={{ y: 0 }} viewport={{ once: true }}
      transition={{ duration: 0.85, ease: EASE, delay: li * 0.08 }}>{w}</motion.span></span>)}</span>;
}
function Stagger({ children, className, gap = 0.08 }) {
  return <motion.div className={className} initial="h" whileInView="s" viewport={{ once: true, margin: "-60px" }}
    variants={{ s: { transition: { staggerChildren: gap } } }}>{children}</motion.div>;
}
const itemV = { h: { opacity: 0, y: 26 }, s: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } } };
function Item({ children, className, ...p }) { return <motion.div variants={itemV} className={className} {...p}>{children}</motion.div>; }

function Counter({ value }) {
  const ref = useRef(null), inView = useInView(ref, { once: true, margin: "-40px" });
  const [disp, setDisp] = useState(value);
  useEffect(() => {
    const m = String(value).match(/[0-9][0-9,\.]*/); if (!inView || !m) return;
    const num = parseFloat(m[0].replace(/,/g, "")), pre = value.slice(0, m.index), post = value.slice(m.index + m[0].length);
    const c = animate(0, num, { duration: 1.6, ease: EASE, onUpdate: v => setDisp(pre + (num % 1 ? v.toFixed(1) : Math.round(v).toLocaleString()) + post) });
    return () => c.stop();
  }, [inView]);
  return <span ref={ref}>{disp}</span>;
}
function Magnetic({ children, className }) {
  const ref = useRef(null), x = useMotionValue(0), y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 170, damping: 13 }), sy = useSpring(y, { stiffness: 170, damping: 13 });
  return <motion.div ref={ref} style={{ x: sx, y: sy }} className={cn("inline-block", className)}
    onMouseMove={e => { const r = ref.current.getBoundingClientRect(); x.set((e.clientX - r.left - r.width / 2) * 0.3); y.set((e.clientY - r.top - r.height / 2) * 0.3); }}
    onMouseLeave={() => { x.set(0); y.set(0); }}>{children}</motion.div>;
}
function Img({ src, alt, className, imgClass, parallax, scrim }) {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], ["-9%", "9%"]);
  return <div ref={ref} className={cn("relative overflow-hidden gframe", className)}>
    <motion.img style={parallax ? { y } : undefined} src={src} alt={alt} loading="lazy"
      className={cn("w-full h-full object-cover gimg", parallax && "scale-[1.18]", imgClass)} />
    <div className="grade-ov" />{scrim && <div className="scrim" />}
  </div>;
}

/* shared */
function Logo({ onDark }) {
  return <a href="#top" className="flex items-center gap-2.5 font-heading font-bold text-[1.15rem] tracking-tight">
    <span className="grid place-items-center w-9 h-9 rounded-[calc(var(--radius)*.6)] bg-primary text-onp text-[13px] font-extrabold tracking-tight">{D.monogram}</span>
    <span>{D.logoMain}{D.logoAccent ? <span className="text-primary"> {D.logoAccent}</span> : null}</span>
  </a>;
}
function Label({ children, n }) {
  return <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-primary">
    {n && <span className="font-heading text-muted/70">{n}</span>}<span className="h-px w-8 bg-primary/50" />{children}</div>;
}
function Head({ kicker, n, title, desc, center, light }) {
  return <div className={cn("max-w-2xl mb-16", center && "mx-auto text-center")}>
    <Reveal><Label n={n}>{kicker}</Label></Reveal>
    <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.02]", SERIF ? "text-[clamp(2.1rem,4.4vw,3.6rem)]" : "text-[clamp(2rem,4vw,3.2rem)]")}>{title}</h2></Reveal>
    {desc && <Reveal delay={0.12}><p className={cn("mt-5 text-lg leading-relaxed", light ? "text-white/70" : "text-muted")}>{desc}</p></Reveal>}
  </div>;
}
function Section({ id, alt, children, className }) {
  return <section id={id} className={cn("relative py-24 md:py-32", alt && "bg-surface-2/50", className)}>{children}</section>;
}

/* ===== NAV ===== */
function Nav() {
  const [open, setOpen] = useState(false), [sc, setSc] = useState(false);
  useEffect(() => { const f = () => setSc(window.scrollY > 24); f(); addEventListener("scroll", f, { passive: true }); return () => removeEventListener("scroll", f); }, []);
  const links = D.nav.map(n => <a key={n.href} href={n.href} className="text-sm font-medium text-muted hover:text-text transition">{n.label}</a>);
  const burger = <button className="md:hidden" onClick={() => setOpen(!open)} aria-label="Menu"><div className="space-y-1.5"><span className="block w-6 h-px bg-text" /><span className="block w-6 h-px bg-text" /><span className="block w-4 h-px bg-text" /></div></button>;
  let bar;
  if (V.nav === "floating") {
    bar = <header className="fixed top-4 inset-x-0 z-50 flex justify-center px-4">
      <nav className={cn("flex items-center gap-7 w-full max-w-5xl rounded-full border px-5 py-2.5 transition-all", sc ? "bg-surface/85 border-border shadow-[0_14px_44px_-18px_rgba(var(--prgb),.4)] backdrop-blur-xl" : "bg-surface/40 border-transparent backdrop-blur-md")}>
        <Logo /><div className="hidden md:flex items-center gap-7 ml-auto">{links}</div>
        <Button size="sm" className="hidden md:inline-flex" onClick={() => location.href = "#contact"}>Apply</Button>{burger}</nav></header>;
  } else if (V.nav === "rule") {
    bar = <header className={cn("fixed top-0 inset-x-0 z-50 transition-all", sc ? "bg-bg/90 backdrop-blur-xl" : "")}>
      <div className="mx-auto max-w-6xl px-6 h-[68px] flex items-center justify-between border-b border-border/0" style={{ borderColor: sc ? "var(--border)" : "transparent" }}>
        <Logo /><nav className="hidden md:flex items-center gap-8">{links}<a href="#contact" className="text-sm font-semibold text-primary">Apply →</a></nav>{burger}</div></header>;
  } else {
    bar = <header className={cn("fixed top-0 inset-x-0 z-50 transition-all", sc ? "bg-bg/85 backdrop-blur-xl border-b border-border" : "border-b border-transparent")}>
      <div className="mx-auto max-w-6xl px-6 h-[72px] flex items-center justify-between"><Logo /><nav className="hidden md:flex items-center gap-8">{links}</nav>
        <div className="hidden md:flex"><Button size="sm" onClick={() => location.href = "#contact"}>Apply Now</Button></div>{burger}</div></header>;
  }
  return <>{bar}<AnimatePresence>{open && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="md:hidden fixed inset-0 z-40 bg-bg/97 backdrop-blur-xl flex flex-col items-center justify-center gap-7">
    {D.nav.map(n => <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="font-heading text-2xl font-bold">{n.label}</a>)}
    <Button onClick={() => { setOpen(false); location.href = "#contact"; }}>Apply Now</Button></motion.div>}</AnimatePresence></>;
}

/* ===== HERO ===== */
function Keycap({ children }) {
  return <span className="inline-flex items-center gap-2.5 rounded-xl border border-border bg-surface/80 backdrop-blur px-3.5 py-2 text-[12px] font-semibold uppercase tracking-[0.14em] text-text/90 shadow-sm">
    <kbd className="grid place-items-center w-5 h-5 rounded-md bg-surface-2 border border-border text-[10px] text-primary">⌘</kbd>{children}</span>;
}
function FramePanel({ src, alt }) {
  return <div className="rounded-[calc(var(--radius)+12px)] border border-border bg-surface p-2.5 shadow-2xl">
    <div className="flex items-center gap-1.5 px-3 py-2.5">
      <span className="w-2.5 h-2.5 rounded-full bg-muted/40" /><span className="w-2.5 h-2.5 rounded-full bg-muted/30" /><span className="w-2.5 h-2.5 rounded-full bg-muted/20" />
      <span className="ml-3 text-[11px] text-muted/70 font-medium">{D.domain}</span></div>
    <Img src={src} alt={alt} parallax className="rounded-[var(--radius)] aspect-[16/9] border border-border" scrim />
  </div>;
}
function HeroCTA() {
  return <div className="flex flex-wrap items-center gap-x-7 gap-y-4">
    <Magnetic><Button size="lg" onClick={() => location.href = "#contact"}>Start your application <Icon name="route" className="w-5 h-5" /></Button></Magnetic>
    <a href="#services" className="group inline-flex items-center gap-2 font-semibold text-text">Our services<span className="transition-transform group-hover:translate-x-1">→</span></a>
  </div>;
}
function Hero() {
  const v = V.hero, head = D.headline;
  if (v === "centered") {
    const mx = D.heroMix;
    return <section id="top" className="relative pt-36 md:pt-44 pb-20 text-center overflow-hidden">
      <div className="hero-aura" />
      <div className="mx-auto max-w-4xl px-6">
        <Reveal><Keycap>{D.kicker}</Keycap></Reveal>
        <Reveal as="h1" delay={0.08} className="font-heading font-bold tracking-[-0.03em] mt-8 leading-[0.98] text-[clamp(2.7rem,7vw,5.4rem)]">
          <span className="block">{mx.lead}</span>
          <span className="font-script font-medium text-primary block leading-[0.92] mt-1 text-[clamp(3.2rem,9vw,6.8rem)]">{mx.accent}</span>
        </Reveal>
        <Reveal delay={0.2}><p className="text-muted text-lg md:text-xl mt-7 max-w-2xl mx-auto leading-relaxed">{D.subhead}</p></Reveal>
        <Reveal delay={0.3}><div className="mt-10 flex flex-col items-center gap-4">
          <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-3">
            <Magnetic><Button size="lg" className="rounded-full" onClick={() => location.href = "#contact"}>Start your application <Icon name="route" className="w-5 h-5" /></Button></Magnetic>
            <a href="#services" className="group inline-flex items-center gap-2 font-semibold text-text">Explore our services <span className="transition-transform group-hover:translate-x-1">→</span></a>
          </div>
          <div className="flex items-center gap-2.5 text-sm text-muted"><span className="text-primary tracking-[0.2em]">★★★★★</span>No obligation · Apply in under 2 minutes</div></div></Reveal>
        <Reveal delay={0.4} className="mt-16"><FramePanel src={D.showcase[0].img} alt={D.company} /></Reveal>
      </div></section>;
  }
  if (v === "cinematic") {
    return <section id="top" className="relative min-h-[100svh] flex flex-col justify-end pb-16 overflow-hidden">
      <div className="absolute inset-0 -z-10"><Img src={D.showcase[0].img} alt={D.company} className="w-full h-full" imgClass="scale-105" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(180deg,rgba(0,0,0,.45) 0%,transparent 22%,transparent 50%,var(--bg) 97%)" }} /></div>
      <div className="mx-auto max-w-6xl px-6 w-full text-white">
        <Reveal><Label>{D.kicker} — {D.cityState}</Label></Reveal>
        <h1 className="font-heading font-extrabold uppercase tracking-[-0.03em] mt-6 text-[clamp(3rem,10vw,8rem)] leading-[0.88]"><Lines text={head} /></h1>
        <div className="grid md:grid-cols-[1fr_auto] gap-8 items-end mt-8">
          <Reveal delay={0.2} className="max-w-xl text-white/80 text-lg leading-relaxed">{D.subhead}</Reveal>
          <Reveal delay={0.3}><HeroCTA /></Reveal></div>
        <Reveal delay={0.4}><div className="flex items-center gap-3 mt-9 text-white/75 text-sm">
          <span className="text-primary tracking-[0.2em]">★★★★★</span>Licensed &amp; insured · {D.routes} coverage · On-time, every lane</div></Reveal>
      </div></section>;
  }
  if (v === "split") {
    return <section id="top" className="relative pt-36 md:pt-44 pb-24 overflow-hidden">
      <div className="hero-aura" />
      <div className="mx-auto max-w-6xl px-6 grid md:grid-cols-[1.08fr_.92fr] gap-x-14 gap-y-10 items-center">
        <div>
          <Reveal><div className="inline-flex items-center gap-2.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted border border-border rounded-full px-4 py-1.5"><span className="w-1.5 h-1.5 rounded-full bg-primary" />{D.kicker}</div></Reveal>
          <h1 className={cn("font-heading font-bold tracking-[-0.03em] mt-6 leading-[0.96]", SERIF ? "text-[clamp(2.8rem,6.4vw,5.2rem)]" : "text-[clamp(2.6rem,6vw,4.8rem)]")}><Lines text={head} /></h1>
          <Reveal delay={0.18}><p className="text-muted text-lg mt-7 max-w-xl leading-relaxed">{D.subhead}</p></Reveal>
          <Reveal delay={0.26} className="mt-9"><HeroCTA /></Reveal>
          <Reveal delay={0.34}><div className="flex items-center gap-3 mt-10 text-sm text-muted">
            <div className="flex">{[0, 1, 2, 3].map(i => <span key={i} className="w-8 h-8 rounded-full border-2 border-bg bg-surface-2 grade-av" style={{ marginLeft: i ? -10 : 0 }} />)}</div>
            <span><b className="text-text">Drivers</b> who refer their friends</span></div></Reveal>
        </div>
        <Reveal delay={0.12} className="relative">
          <Img src={D.showcase[0].img} alt={D.company} parallax className="rounded-[calc(var(--radius)+12px)] border border-border aspect-[4/5] shadow-2xl" />
          <div className="absolute left-5 bottom-5 right-5 flex justify-between items-end text-white">
            <div><div className="text-[11px] uppercase tracking-widest text-white/70">Top weekly pay</div><div className="font-heading font-bold text-2xl">{D.pay}</div></div>
            <div className="text-right"><div className="text-[11px] uppercase tracking-widest text-white/70">Home</div><div className="font-heading font-bold text-2xl">{D.homeShort}</div></div></div>
        </Reveal>
      </div></section>;
  }
  // editorial
  return <section id="top" className="relative pt-36 md:pt-44 pb-16 overflow-hidden">
    <div className="mx-auto max-w-6xl px-6">
      <Reveal><Label>{D.kicker} · {D.cityState}</Label></Reveal>
      <div className="grid md:grid-cols-[1.7fr_1fr] gap-x-12 gap-y-8 items-end mt-8 pb-12 border-b border-border">
        <h1 className={cn("font-heading font-bold tracking-[-0.03em] leading-[0.92]", SERIF ? "text-[clamp(3rem,9vw,7rem)]" : "text-[clamp(2.8rem,8.5vw,6.4rem)]")}><Lines text={head} /></h1>
        <div className="md:pb-3"><Reveal delay={0.2}><p className="text-muted text-lg leading-relaxed">{D.subhead}</p></Reveal>
          <Reveal delay={0.3} className="mt-7"><HeroCTA /></Reveal></div>
      </div>
      <Reveal delay={0.15}><Img src={D.showcase[0].img} alt={D.company} parallax scrim className="mt-10 rounded-[calc(var(--radius)+8px)] border border-border h-[56vh] min-h-[380px]" /></Reveal>
    </div></section>;
}

/* ===== TICKER ===== */
function Ticker() {
  const items = [...D.freight.map(f => f.title), "Licensed & Insured", "On-Time Freight", "24/7 Dispatch"];
  const row = items.flatMap((p, i) => [<span key={"t" + i} className="font-heading font-semibold text-[1.05rem]">{p}</span>,
    <span key={"d" + i} className="text-primary">✦</span>]);
  return <div className="border-y border-border py-5 overflow-hidden bg-surface-2/40 mask-fade">
    <div className="marquee gap-8 items-center text-text/85">{row}{row}</div></div>;
}

/* ===== STATS ===== */
function Stats() {
  if (V.stats === "ledger") {
    return <Section id="stats"><div className="mx-auto max-w-6xl px-6">
      <Stagger className="grid grid-cols-2 md:grid-cols-4 gap-y-10 gap-x-6 border-t border-border pt-12">
        {D.stats.map((s, i) => <Item key={i} className="relative">
          <div className="text-[11px] uppercase tracking-[0.18em] text-muted">{nn(i + 1)}</div>
          <div className="font-heading font-bold tracking-tight text-[clamp(2rem,3.6vw,3rem)] mt-3 leading-none"><Counter value={s.v} /></div>
          <div className="text-muted mt-2 text-sm">{s.l}</div></Item>)}
      </Stagger></div></Section>;
  }
  // strip
  return <Section id="stats"><div className="mx-auto max-w-6xl px-6"><Stagger className="grid grid-cols-2 md:grid-cols-4 rounded-[calc(var(--radius)+8px)] border border-border overflow-hidden bg-surface">
    {D.stats.map((s, i) => <Item key={i} className={cn("p-8 md:p-10", i && "border-t md:border-t-0 md:border-l border-border", i >= 2 && "border-t md:border-t-0")}>
      <div className="font-heading font-bold text-primary tracking-tight text-[clamp(1.9rem,3.2vw,2.7rem)] leading-none"><Counter value={s.v} /></div>
      <div className="text-muted mt-2.5 text-[13px] uppercase tracking-[0.12em]">{s.l}</div></Item>)}
  </Stagger></div></Section>;
}

/* ===== SERVICES (freight lines — credibility for shippers/brokers) ===== */
function Freight() {
  const alt = D.studio.order.indexOf("services") % 2 === 0;
  const sdesc = D.short + " moves dry van, refrigerated and specialized freight across " + D.coverageArea + " — with the equipment and capacity to match the load.";
  if (V.freight === "list") {
    // full-width numbered editorial rows — taller, no cards
    return <Section id="services" alt={alt}><div className="mx-auto max-w-5xl px-6">
      <Head n="01" kicker="What we haul" title={"Freight services built around your supply chain"} desc={sdesc} />
      <Stagger>{D.freight.map((s, i) => <Item key={i}>
        <div className="group grid grid-cols-[auto_1fr_auto] gap-6 items-baseline py-7 border-t border-border last:border-b transition-all hover:px-2">
          <span className="font-heading font-bold text-[clamp(1.4rem,2.2vw,2rem)] text-muted/40 group-hover:text-primary transition-colors">{nn(i + 1)}</span>
          <div><h3 className="font-heading text-xl md:text-2xl font-bold tracking-tight">{s.title}</h3><p className="text-muted mt-2 max-w-2xl leading-relaxed">{s.desc}</p></div>
          <Icon name={s.icon} className="w-6 h-6 text-primary/40 group-hover:text-primary transition-colors hidden md:block" /></div></Item>)}
      </Stagger></div></Section>;
  }
  if (V.freight === "split") {
    // asymmetric: sticky intro left, compact service list right
    return <Section id="services" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-[330px_1fr] gap-12">
      <div className="md:sticky md:top-28 self-start"><Label n="">What we haul</Label>
        <h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.04]", SERIF ? "text-[clamp(1.9rem,3.4vw,2.8rem)]" : "text-[clamp(1.8rem,3vw,2.5rem)]")}>Freight built around your supply chain</h2>
        <p className="text-muted mt-5 leading-relaxed">{sdesc}</p></div>
      <Stagger className="grid sm:grid-cols-2 gap-x-8 gap-y-7 self-start">{D.freight.map((s, i) => <Item key={i}>
        <div className="flex gap-4"><Icon name={s.icon} className="w-6 h-6 text-primary shrink-0 mt-1" />
          <div><h3 className="font-heading text-lg font-bold tracking-tight">{s.title}</h3><p className="text-muted mt-1.5 text-[0.95rem] leading-relaxed">{s.desc}</p></div></div></Item>)}
      </Stagger></div></Section>;
  }
  // cards grid (default)
  return <Section id="services" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head n="" kicker="What we haul" title={"Freight services built around your supply chain"} desc={sdesc} />
    <Stagger className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">{D.freight.map((s, i) => <Item key={i}>
      <Card className="group h-full p-7 transition-all hover:-translate-y-1 hover:shadow-xl">
        <div className="grid place-items-center w-12 h-12 rounded-[var(--radius)] bg-primary/10 text-primary"><Icon name={s.icon} className="w-6 h-6" /></div>
        <h3 className="font-heading text-xl font-bold tracking-tight mt-5">{s.title}</h3>
        <p className="text-muted mt-2.5 leading-relaxed text-[0.95rem]">{s.desc}</p></Card></Item>)}
    </Stagger></div></Section>;
}

/* ===== COVERAGE (network / lanes) ===== */
function Coverage() {
  const alt = D.studio.order.indexOf("coverage") % 2 === 0;
  return <Section id="coverage" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-2 gap-14 items-center">
    <div><Reveal><Label>Coverage</Label></Reveal>
      <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.05]", SERIF ? "text-[clamp(2rem,3.8vw,3rem)]" : "text-[clamp(1.9rem,3.4vw,2.7rem)]")}>A network that reaches {D.routes}</h2></Reveal>
      <Reveal delay={0.12}><p className="text-muted mt-6 leading-relaxed text-[1.05rem]">From {D.cityState}, {D.company} runs freight across {D.coverageArea} — built for predictable transit and real, available capacity.</p></Reveal>
      <Stagger className="mt-8 flex flex-col">{D.coverage.regions.map((r, i) => <Item key={i}>
        <div className="flex items-start gap-4 py-4 border-t border-border last:border-b">
          <Icon name="pin" className="w-5 h-5 text-primary mt-0.5 shrink-0" />
          <div><div className="font-heading font-bold tracking-tight">{r.name}</div><div className="text-muted text-sm mt-0.5">{r.note}</div></div></div></Item>)}
      </Stagger></div>
    <Reveal delay={0.1} className="relative">
      <Img src={D.showcase[2].img} alt={D.company + " coverage"} parallax scrim className="rounded-[calc(var(--radius)+12px)] border border-border aspect-[4/5] shadow-xl" />
      <div className="absolute left-5 right-5 bottom-5 grid grid-cols-2 gap-3">{D.coverage.stats.slice(0, 2).map((s, i) => <div key={i} className="rounded-[var(--radius)] bg-surface/90 backdrop-blur px-4 py-3 border border-border">
        <div className="font-heading font-bold text-xl text-primary"><Counter value={s.v} /></div><div className="text-[11px] uppercase tracking-widest text-muted mt-0.5">{s.l}</div></div>)}</div>
    </Reveal></div></Section>;
}

/* ===== CAREERS (drivers — kept the slick UI, reframed) ===== */
function CareersList({ alt }) {
  return <Section id="careers" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-[280px_1fr] gap-12">
    <div className="md:sticky md:top-28 self-start"><Label n="">Careers</Label>
      <h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.04]", SERIF ? "text-[clamp(1.9rem,3.4vw,2.8rem)]" : "text-[clamp(1.8rem,3vw,2.5rem)]")}>What it means to drive with {D.short}</h2>
      <p className="text-muted mt-5 leading-relaxed">We're growing our driver team. Every detail is built to keep you earning, rolling, and home on time.</p>
      <Button className="mt-7" onClick={() => location.href = "#contact"}>Apply to drive</Button></div>
    <Stagger>{D.benefits.map((s, i) => <Item key={i}>
      <div className="group grid grid-cols-[auto_1fr_auto] gap-6 items-baseline py-7 border-t border-border last:border-b transition-all hover:px-2">
        <span className="font-heading font-bold text-[clamp(1.4rem,2vw,1.9rem)] text-muted/50 group-hover:text-primary transition-colors">{nn(i + 1)}</span>
        <div><h3 className="font-heading text-xl md:text-2xl font-bold tracking-tight">{s.title}</h3><p className="text-muted mt-2 max-w-xl leading-relaxed">{s.desc}</p></div>
        <Icon name={s.icon} className="w-6 h-6 text-primary/40 group-hover:text-primary transition-colors hidden md:block" /></div></Item>)}
    </Stagger></div></Section>;
}
function CareersAccordion({ alt }) {
  const [open, setOpen] = useState(0);
  return <Section id="careers" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head n="" kicker="Careers" title={"Built around the driver"} desc="We're hiring CDL-A drivers. Everything we do keeps you earning, rolling, and home on time." />
    <div className="grid md:grid-cols-[1fr_.85fr] gap-10 items-start">
      <div>{D.benefits.map((s, i) => <div key={i} className="border-t border-border last:border-b">
        <button onClick={() => setOpen(i)} className="w-full flex items-center gap-5 py-5 text-left">
          <span className={cn("font-heading font-bold text-lg transition-colors", open === i ? "text-primary" : "text-muted/50")}>{nn(i + 1)}</span>
          <span className={cn("font-heading text-xl font-bold tracking-tight transition-colors flex-1", open === i ? "text-text" : "text-muted")}>{s.title}</span>
          <Icon name={s.icon} className={cn("w-5 h-5 transition-colors", open === i ? "text-primary" : "text-muted/40")} /></button>
        <AnimatePresence initial={false}>{open === i && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.4, ease: EASE }} className="overflow-hidden">
          <p className="text-muted pb-6 pl-10 max-w-md leading-relaxed">{s.desc}</p></motion.div>}</AnimatePresence></div>)}
        <Button className="mt-8" onClick={() => location.href = "#contact"}>Apply to drive</Button></div>
      <div className="md:sticky md:top-28"><AnimatePresence mode="wait"><motion.div key={open} initial={{ opacity: 0, scale: 1.02 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <Img src={D.showcase[open % 4].img} alt={D.benefits[open].title} className="rounded-[calc(var(--radius)+8px)] border border-border aspect-[5/4]" /></motion.div></AnimatePresence></div>
    </div></div></Section>;
}
function Careers() { const alt = D.studio.order.indexOf("careers") % 2 === 0; return V.careers === "accordion" ? <CareersAccordion alt={alt} /> : <CareersList alt={alt} />; }

/* ===== ABOUT ===== */
function AboutHeading({ light }) {
  return <>
    <Reveal><Label>About {D.short}</Label></Reveal>
    <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.05]", light && "text-white", SERIF ? "text-[clamp(2rem,3.8vw,3rem)]" : "text-[clamp(1.9rem,3.4vw,2.7rem)]")}>{D.aboutTitle}</h2></Reveal>
    <Reveal delay={0.12}><p className={cn("mt-6 leading-relaxed text-[1.05rem]", light ? "text-white/80" : "text-muted")}>{D.aboutP1}</p></Reveal>
    <Reveal delay={0.16}><p className={cn("mt-3 leading-relaxed", light ? "text-white/75" : "text-muted")}>{D.aboutP2}</p></Reveal>
  </>;
}
function SafetyGrid({ light }) {
  return <Stagger className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3.5 mt-8">{D.safety.map((p, i) => <Item key={i}>
    <div className={cn("flex items-start gap-2.5 font-medium text-[0.95rem]", light && "text-white/90")}><Icon name="check" className="w-4 h-4 text-primary mt-1 shrink-0" />{p}</div></Item>)}</Stagger>;
}
function About() {
  const alt = D.studio.order.indexOf("about") % 2 === 0, v = V.about;
  if (v === "centered") {
    return <Section id="about" alt={alt}><div className="mx-auto max-w-3xl px-6 text-center">
      <Reveal><Label center>About {D.short}</Label></Reveal>
      <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.05]", SERIF ? "text-[clamp(2.1rem,4.2vw,3.4rem)]" : "text-[clamp(2rem,3.8vw,3rem)]")}>{D.aboutTitle}</h2></Reveal>
      <Reveal delay={0.12}><p className="text-muted mt-6 leading-relaxed text-lg">{D.aboutP1}</p></Reveal>
      <Reveal delay={0.16}><p className="text-muted mt-3 leading-relaxed">{D.aboutP2}</p></Reveal>
      <Stagger className="flex flex-wrap justify-center gap-2.5 mt-9">{D.safety.map((p, i) => <Item key={i}>
        <span className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-medium"><Icon name="check" className="w-4 h-4 text-primary" />{p}</span></Item>)}</Stagger>
    </div></Section>;
  }
  if (v === "fullbleed") {
    return <section id="about" className="relative py-28 md:py-40 overflow-hidden">
      <div className="absolute inset-0 -z-10"><Img src={D.showcase[1].img} alt={D.company} className="w-full h-full" />
        <div className="absolute inset-0" style={{ background: "linear-gradient(90deg,rgba(8,8,10,.88),rgba(8,8,10,.62) 52%,rgba(8,8,10,.2))" }} /></div>
      <div className="mx-auto max-w-6xl px-6"><div className="max-w-xl text-white"><AboutHeading light /><SafetyGrid light /></div></div></section>;
  }
  const imgRight = v === "splitR";
  return <Section id="about" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-2 gap-14 items-center">
    <Reveal className={cn("relative", imgRight ? "order-1 md:order-2" : "order-2 md:order-1")}>
      <Img src={D.showcase[1].img} alt={D.company} parallax className="rounded-[calc(var(--radius)+12px)] border border-border aspect-[4/5] shadow-xl" />
      <div className={cn("absolute -top-5 hidden md:block", imgRight ? "-left-5" : "-right-5")}><Card className="px-6 py-5 shadow-xl bg-surface"><div className="font-heading font-bold text-2xl text-primary leading-tight">Licensed<br />&amp; Insured</div><div className="text-xs text-muted uppercase tracking-widest mt-1.5">On every load</div></Card></div></Reveal>
    <div className={cn(imgRight ? "order-2 md:order-1" : "order-1 md:order-2")}><AboutHeading /><SafetyGrid /></div>
  </div></Section>;
}

/* ===== PROCESS ===== */
function Process() {
  const alt = D.studio.order.indexOf("process") % 2 === 0;
  if (V.process === "timeline") {
    return <Section id="process" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-[300px_1fr] gap-12">
      <div className="md:sticky md:top-28 self-start"><Label>The process</Label><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-tight", SERIF ? "text-[clamp(1.9rem,3.4vw,2.8rem)]" : "text-[clamp(1.8rem,3vw,2.5rem)]")}>From application to first load</h2></div>
      <div className="relative"><div className="absolute left-[27px] top-3 bottom-3 w-px bg-border" />
        <Stagger>{D.process.map((s, i) => <Item key={i}><div className="relative grid grid-cols-[auto_1fr] gap-6 pb-9 last:pb-0">
          <span className="z-10 grid place-items-center w-14 h-14 rounded-full bg-surface border border-border font-heading font-bold text-primary">{nn(i + 1)}</span>
          <div className="pt-3"><h4 className="font-heading text-xl font-bold">{s.title}</h4><p className="text-muted mt-1.5 leading-relaxed max-w-lg">{s.desc}</p></div></div></Item>)}</Stagger></div></div></Section>;
  }
  return <Section id="process" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head kicker="The process" title="On the road in four steps" center />
    <Stagger className="grid md:grid-cols-4 gap-x-8 gap-y-10">{D.process.map((s, i) => <Item key={i} className="relative">
      <div className="font-heading font-bold text-[3rem] leading-none text-primary/15">{nn(i + 1)}</div>
      <h4 className="font-heading text-lg font-bold mt-2">{s.title}</h4><p className="text-muted mt-2 text-[0.95rem] leading-relaxed">{s.desc}</p>
      {i < 3 && <div className="hidden md:block absolute top-6 right-0 text-muted/30">→</div>}</Item>)}</Stagger></div></Section>;
}

/* ===== SHOWCASE ===== */
function Showcase() {
  const alt = D.studio.order.indexOf("showcase") % 2 === 0;
  if (V.showcase === "marquee") {
    const items = [...D.showcase, ...D.showcase];
    return <Section id="showcase" alt={alt}><div className="mx-auto max-w-6xl px-6"><Head kicker="On the road" title="A closer look" /></div>
      <div className="overflow-hidden mask-fade"><div className="marquee gap-5 py-2">{items.map((s, i) =>
        <div key={i} className="relative shrink-0 w-[360px] aspect-[4/3]"><Img src={s.img} alt={s.title} className="w-full h-full rounded-[calc(var(--radius)+6px)] border border-border" scrim />
          <div className="absolute inset-x-0 bottom-0 p-5"><div className="text-white font-heading font-bold text-lg">{s.title}</div><div className="text-white/70 text-sm">{s.sub}</div></div></div>)}</div></div></Section>;
  }
  if (V.showcase === "frame") {
    return <Section id="showcase" alt={alt}><div className="mx-auto max-w-6xl px-6">
      <Head kicker="On the road" title="The fleet, up close" />
      <Stagger className="grid md:grid-cols-12 gap-4">{D.showcase.map((s, i) => <Item key={i} className={cn(i === 0 ? "md:col-span-7" : i === 1 ? "md:col-span-5" : "md:col-span-4")}>
        <div className="relative group"><Img src={s.img} alt={s.title} className={cn("rounded-[calc(var(--radius)+6px)] border border-border", i === 0 ? "aspect-[16/10]" : "aspect-[4/3]")} scrim />
          <div className="absolute inset-x-0 bottom-0 p-5"><div className="text-white font-heading font-bold">{s.title}</div><div className="text-white/70 text-sm">{s.sub}</div></div></div></Item>)}</Stagger></div></Section>;
  }
  return <Section id="showcase" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head kicker="On the road" title="A closer look at the fleet" />
    <Stagger className="grid md:grid-cols-4 gap-4">{D.showcase.map((s, i) => <Item key={i} className={cn(i === 0 && "md:col-span-2 md:row-span-2")}>
      <div className="relative group h-full"><Img src={s.img} alt={s.title} className={cn("h-full rounded-[calc(var(--radius)+6px)] border border-border", i === 0 ? "min-h-[280px]" : "aspect-[4/3]")} scrim />
        <div className="absolute inset-x-0 bottom-0 p-5"><div className="text-white font-heading font-bold text-lg">{s.title}</div><div className="text-white/70 text-sm">{s.sub}</div></div></div></Item>)}</Stagger></div></Section>;
}

/* ===== TESTIMONIALS ===== */
function Testimonials() {
  const alt = D.studio.order.indexOf("testimonials") % 2 === 0, t = D.testimonials;
  if (V.testimonials === "pull") {
    return <Section id="reviews" alt={alt}><div className="mx-auto max-w-4xl px-6 text-center">
      <Reveal><Label center>Driver voices</Label></Reveal>
      <Reveal delay={0.06}><blockquote className={cn("font-heading font-medium tracking-tight mt-8 leading-[1.18]", SERIF ? "text-[clamp(1.7rem,4vw,2.9rem)] italic" : "text-[clamp(1.5rem,3.4vw,2.5rem)]")}>“{t[0].q}”</blockquote></Reveal>
      <Reveal delay={0.12}><div className="mt-8 text-muted"><span className="font-heading font-bold text-text">{t[0].n}</span> · {t[0].r}</div></Reveal>
      <Stagger className="grid md:grid-cols-2 gap-6 mt-16 text-left">{t.slice(1).map((x, i) => <Item key={i}>
        <Card className="p-7 h-full"><div className="text-primary tracking-[0.2em] text-sm mb-4">★★★★★</div><p className="leading-relaxed">“{x.q}”</p>
          <div className="mt-5 text-sm"><span className="font-semibold">{x.n}</span> <span className="text-muted">· {x.r}</span></div></Card></Item>)}</Stagger>
    </div></Section>;
  }
  return <Section id="reviews" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head kicker="Driver reviews" title="Drivers say it best" center />
    <Stagger className="grid md:grid-cols-3 gap-6">{t.map((x, i) => <Item key={i}>
      <Card className="p-8 h-full"><div className="text-primary tracking-[0.2em] text-sm mb-4">★★★★★</div><blockquote className="leading-relaxed">“{x.q}”</blockquote>
        <figcaption className="mt-6 pt-5 border-t border-border text-sm"><span className="font-semibold">{x.n}</span><div className="text-muted">{x.r}</div></figcaption></Card></Item>)}</Stagger></div></Section>;
}

/* ===== CTA ===== */
function CTA() {
  const [sent, setSent] = useState(false);
  return <section id="contact" className="relative py-24 md:py-32 overflow-hidden"><div className="mx-auto max-w-6xl px-6">
    <div className="relative overflow-hidden rounded-[calc(var(--radius)+18px)] border border-border grid md:grid-cols-2 gap-10 p-8 md:p-14 items-center">
      <div className="absolute inset-0 -z-10"><Img src={D.showcase[2].img} alt="" className="w-full h-full" /><div className="absolute inset-0 cta-scrim" /></div>
      <div className="relative text-white"><Reveal><Label>Get in touch</Label></Reveal>
        <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-tight", SERIF ? "text-[clamp(2rem,4vw,3.2rem)]" : "text-[clamp(1.9rem,3.6vw,2.9rem)]")}>{D.ctaTitle}</h2></Reveal>
        <Reveal delay={0.12}><p className="text-white/80 mt-5 leading-relaxed max-w-md">{D.ctaSub}</p></Reveal>
        <Reveal delay={0.18}><div className="flex flex-col gap-3 mt-8 text-sm text-white/85">
          <span className="flex items-center gap-2.5"><Icon name="check" className="w-4 h-4" />Drivers: a real recruiter calls within one business day</span>
          <span className="flex items-center gap-2.5"><Icon name="pin" className="w-4 h-4" />Shippers: email <b className="font-semibold">{D.email}</b> to request capacity</span>
          <span className="flex items-center gap-2.5"><Icon name="home" className="w-4 h-4" />{D.cityState}</span></div></Reveal></div>
      <Reveal delay={0.1}><form className="grid gap-3 bg-surface/95 backdrop-blur p-7 rounded-[calc(var(--radius)+6px)] border border-border" onSubmit={e => { e.preventDefault(); setSent(true); setTimeout(() => setSent(false), 2600); e.target.reset(); }}>
        <input name="name" required placeholder="Full name" className={inputCls} />
        <input name="phone" type="tel" required placeholder="Phone number" className={inputCls} />
        <input name="email" type="email" placeholder="Email address" className={inputCls} />
        <select name="exp" className={inputCls}><option value="">Driving experience</option><option>0-6 months</option><option>6-12 months</option><option>1-3 years</option><option>3+ years</option></select>
        <Button type="submit" size="lg" className="w-full mt-1">{sent ? "Application sent ✓" : "Apply Now"}</Button>
        <p className="text-xs text-muted text-center mt-1">By submitting you agree to be contacted about driving opportunities.</p></form></Reveal>
    </div></div></section>;
}

/* ===== FOOTER ===== */
function FooterLinks() {
  return <>{D.nav.map(n => <a key={n.href} href={n.href} className="text-sm text-muted hover:text-text transition">{n.label}</a>)}</>;
}
function FooterBottom() {
  return <div className="mt-6 pt-6 border-t border-border flex flex-col md:flex-row justify-between gap-3 text-xs text-muted">
    <span>© {D.year} {D.company}. All rights reserved.</span>
    <span className="max-w-2xl md:text-right">Equal Opportunity Employer — all qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</span></div>;
}
function Footer() {
  const v = V.footer;
  if (v === "minimal") {
    return <footer className="border-t border-border py-14"><div className="mx-auto max-w-4xl px-6 text-center">
      <div className="flex justify-center"><Logo /></div>
      <p className="text-muted text-sm mt-5 max-w-md mx-auto leading-relaxed">{D.company} — {D.routesType}, {D.coverageArea}. Licensed &amp; insured.</p>
      <div className="flex flex-wrap justify-center gap-x-6 gap-y-2 mt-6"><FooterLinks /></div>
      <div className="mt-7 text-xs text-muted">{D.email} · {D.cityState}</div>
      <FooterBottom />
    </div></footer>;
  }
  if (v === "columns") {
    return <footer className="border-t border-border pt-16 pb-10"><div className="mx-auto max-w-6xl px-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
        <div className="col-span-2 md:col-span-1"><Logo /><p className="text-muted text-sm mt-4 leading-relaxed">Licensed &amp; insured carrier in {D.cityState}.</p></div>
        <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Explore</div><div className="flex flex-col gap-2.5"><FooterLinks /></div></div>
        <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Company</div><div className="flex flex-col gap-2.5 text-sm text-muted"><span>{D.routesType}</span><span>{D.coverageArea}</span><span>Licensed &amp; Insured</span></div></div>
        <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Contact</div><div className="flex flex-col gap-2.5 text-sm text-muted"><span>{D.email}</span><span>{D.cityState}</span><a href="#contact" className="text-primary font-semibold">Get in touch →</a></div></div>
      </div>
      <FooterBottom />
    </div></footer>;
  }
  // wordmark (default)
  return <footer className="border-t border-border pt-20 pb-10"><div className="mx-auto max-w-6xl px-6">
    <div className="grid md:grid-cols-[1.5fr_1fr_1fr] gap-10">
      <div><Logo /><p className="text-muted text-sm mt-5 leading-relaxed max-w-xs">{D.company} — an asset-based motor carrier moving freight across {D.cityState} and {D.coverageArea}. {D.routesType}, modern fleet, real accountability.</p></div>
      <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Explore</div><div className="flex flex-col gap-2.5"><FooterLinks /><a href="#contact" className="text-sm text-primary font-semibold">Contact us →</a></div></div>
      <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Get in touch</div><div className="text-sm text-muted space-y-1.5"><div>{D.email}</div><div>{D.cityState}</div><div>Licensed &amp; Insured Carrier</div></div></div>
    </div>
    <div className="mt-16 font-heading font-bold tracking-[-0.04em] leading-none text-[clamp(2.5rem,12vw,9rem)] text-text/[0.06] select-none">{D.short}</div>
    <FooterBottom />
  </div></footer>;
}

const SECTIONS = { services: Freight, coverage: Coverage, about: About, careers: Careers, stats: Stats, process: Process, showcase: Showcase, testimonials: Testimonials };
function App() {
  return <><Nav /><Hero />{D.studio.ticker ? <Ticker /> : null}
    {D.studio.order.map((k, i) => { const C = SECTIONS[k]; return C ? <C key={k + i} /> : null; })}
    <CTA /><Footer /></>;
}
createRoot(document.getElementById("root")).render(<App />);
"""


# ─────────────────────────────────────────────────────────────────────────────
# HTML assembly
# ─────────────────────────────────────────────────────────────────────────────

_GRAIN = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
          "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E"
          "%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")")

_IMPORTMAP = json.dumps({"imports": {
    "react": "https://esm.sh/react@18.3.1",
    "react/jsx-runtime": "https://esm.sh/react@18.3.1/jsx-runtime",
    "react/jsx-dev-runtime": "https://esm.sh/react@18.3.1/jsx-dev-runtime",
    "react-dom": "https://esm.sh/react-dom@18.3.1",
    "react-dom/client": "https://esm.sh/react-dom@18.3.1/client",
    "framer-motion": "https://esm.sh/framer-motion@11.11.17?external=react,react-dom",
}})


def _head(data, d, theme, fh, fb, sf):
    fonts = sorted({fh, fb, sf, "Inter"})
    font_url = "https://fonts.googleapis.com/css2?" + "&".join(_gfont(f) for f in fonts) + "&display=swap"
    tw = {"theme": {"extend": {
        "colors": {"primary": "var(--primary)", "primary-2": "var(--primary-2)", "accent": "var(--accent)",
                   "bg": "var(--bg)", "surface": "var(--surface)", "surface-2": "var(--surface-2)",
                   "text": "var(--text)", "muted": "var(--muted)", "border": "var(--border)", "onp": "var(--on-primary)"},
        "fontFamily": {"heading": [fh, "Georgia" if data["studio"]["fonts"] == "serif" else "system-ui", "sans-serif"],
                       "body": [fb, "system-ui", "sans-serif"], "sans": [fb, "system-ui", "sans-serif"],
                       "script": [sf, "cursive"]}}}}
    root = (":root{--bg:%(bg)s;--surface:%(surface)s;--surface-2:%(surface-2)s;--text:%(text)s;--muted:%(muted)s;"
            "--border:%(border)s;--primary:%(primary)s;--primary-2:%(primary-2)s;--accent:%(accent)s;"
            "--on-primary:%(on-primary)s;--prgb:%(prgb)s;--argb:%(argb)s;--radius:%(radius)s;}" % theme)
    grain = (".grain::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:9999;opacity:%.3f;"
             "background-image:%s;background-size:180px;mix-blend-mode:%s}"
             % (theme["grain"], _GRAIN, "soft-light" if theme["mode"] == "dark" else "multiply")) if theme["grain"] else ""
    css = (root +
           "*{margin:0;padding:0;box-sizing:border-box}html{scroll-behavior:smooth}"
           "body{background:var(--bg);color:var(--text);font-family:'" + fb + "',system-ui,sans-serif;"
           "-webkit-font-smoothing:antialiased;overflow-x:hidden;line-height:1.6}"
           "h1,h2,h3,h4{font-family:'" + fh + "',Georgia,system-ui,sans-serif}"
           "::selection{background:var(--primary);color:var(--on-primary)}"
           # photographic grade — unifies stock photos into one brand
           ".gimg{filter:grayscale(.28) contrast(1.06) brightness(.98) saturate(.92)}"
           ".gframe .grade-ov{position:absolute;inset:0;pointer-events:none;"
           "background:linear-gradient(155deg,rgba(var(--prgb),.30),transparent 55%);mix-blend-mode:soft-light}"
           ".gframe .scrim{position:absolute;inset:0;pointer-events:none;background:linear-gradient(0deg,rgba(8,8,10,.72),transparent 52%)}"
           ".grade-av{filter:grayscale(.3)}"
           ".hero-aura{position:absolute;inset:0;z-index:-1;background:"
           "radial-gradient(55% 50% at 14% 4%,rgba(var(--prgb),.16),transparent 60%),"
           "radial-gradient(40% 45% at 96% 0%,rgba(var(--argb),.10),transparent 55%)}"
           ".cta-scrim{background:linear-gradient(120deg,rgba(8,8,10,.82),rgba(8,8,10,.5))}"
           "@keyframes mq{from{transform:translateX(0)}to{transform:translateX(-50%)}}"
           ".marquee{display:flex;width:max-content;animation:mq 34s linear infinite}"
           ".mask-fade{-webkit-mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent);mask:linear-gradient(90deg,transparent,#000 6%,#000 94%,transparent)}"
           + grain)
    return ("<!DOCTYPE html><html lang=\"en\" class=\"grain\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>" + data["company"] + " — Freight &amp; Logistics | " + data["cityState"] + "</title>"
            "<meta name=\"description\" content=\"" + data["company"] + " is an asset-based motor carrier in "
            + data["cityState"] + " moving dry van, refrigerated and specialized freight across " + data["coverageArea"]
            + ". Licensed, insured and hiring CDL-A drivers.\">"
            "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
            "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
            "<link href=\"" + font_url + "\" rel=\"stylesheet\">"
            "<script src=\"https://cdn.tailwindcss.com\"></script>"
            "<script>tailwind.config=" + json.dumps(tw) + "</script>"
            "<style>" + css + "</style></head>")


def render_site(info, studio=None):
    """Render a single-file React+Tailwind+Framer-Motion site. -> (html, ctx)."""
    data, d, theme, fh, fb, sf = _build_payload(info)
    if studio:
        for pr in PRESETS:
            if pr["id"] == studio:
                theme = dict(random.choice(THEMES[pr["id"]]))
                fh, fb = random.choice(_FONTS[pr["fonts"]])
                data["studio"].update({"id": pr["id"], "label": pr["label"], "variants": pr["v"],
                                       "order": pr["order"], "mode": theme["mode"], "fonts": pr["fonts"]})
                break
    body = (
        "<body><div id=\"root\"></div>"
        + _company_data_script(_company_data(d))
        + "<script>window.__DATA__=" + json.dumps(data) + ";</script>"
        + "<script type=\"importmap\">" + _IMPORTMAP + "</script>"
        + "<script src=\"https://unpkg.com/@babel/standalone@7.25.6/babel.min.js\"></script>"
        + "<script type=\"text/babel\" data-type=\"module\" data-presets=\"react\">" + _APP_JSX + "</script>"
        + "</body></html>"
    )
    return _head(data, d, theme, fh, fb, sf) + body, d


# ─────────────────────────────────────────────────────────────────────────────
# Static prerender — snapshot the client-rendered DOM so crawlers, link-preview
# bots and no-JS viewers (e.g. Indeed verification, a broker doing "view source")
# see a fully-formed carrier site instead of an empty #root. The live React /
# Tailwind / Babel scripts stay in place as progressive enhancement; a real
# browser simply re-renders on top of the captured markup.
# ─────────────────────────────────────────────────────────────────────────────

def static_snapshot(html, timeout_ms=20000):
    """Render `html` in headless Chrome, settle scroll-reveal animations, then
    bake the rendered #root markup and Tailwind's generated CSS back into the
    *pristine* original HTML — so crawlers/no-JS viewers get real content while
    the original (known-good) script ordering still re-renders live in browsers.
    Returns None on any failure so the caller falls back to the live HTML.

    We deliberately do NOT serialise document.outerHTML: that captures the
    Babel-injected module scripts and re-mounts React against them, which breaks
    the import map on reload. Re-injecting into the original markup keeps exactly
    one import map / one app script, so the page behaves like a fresh first load.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_content(html, wait_until="domcontentloaded", timeout=timeout_ms)
            # wait for Babel to transpile the JSX and React to mount the app
            page.wait_for_function(
                "() => { const r = document.getElementById('root'); return r && r.children.length > 0; }",
                timeout=timeout_ms,
            )
            page.wait_for_timeout(1400)  # let Tailwind inject utilities + fonts settle
            # scroll through so every whileInView reveal fires, then return to top
            for y in range(0, 9000, 800):
                page.evaluate("window.scrollTo(0, %d)" % y)
                page.wait_for_timeout(70)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(350)
            # force any element still mid-transition to its visible resting state
            page.evaluate(
                "document.querySelectorAll('[style]').forEach(function(e){"
                "var s=e.style;"
                "if(s.opacity!==''&&parseFloat(s.opacity)<1)s.opacity='1';"
                "if(s.transform&&/translate|scale/.test(s.transform))s.transform='none';"
                "});"
            )
            root_html = page.evaluate("document.getElementById('root').innerHTML")
            # Tailwind Play + framer inject <style> blocks; ours is the only one
            # carrying the :root design tokens, so keep everything else.
            extra_css = page.evaluate(
                "Array.from(document.querySelectorAll('style'))"
                ".map(function(s){return s.textContent||''})"
                ".filter(function(c){return c && c.indexOf('--bg:')===-1}).join('\\n')"
            )
        finally:
            browser.close()

    if not root_html or 'id="services"' not in root_html:
        return None
    out = html.replace('<div id="root"></div>', '<div id="root">' + root_html + "</div>", 1)
    if extra_css:
        out = out.replace("</head>", '<style data-prerender>' + extra_css + "</style></head>", 1)
    return out
