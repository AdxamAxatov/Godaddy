"""
Studio engine — premium, never-repeating single-file website generator.

Every call to `render_site(info)` randomly selects one fully self-contained
"design studio" (its own CSS, layout, type scale and motion system) and a
procedurally generated colour palette, so two generations rarely look alike
while staying a single static index.html that drops into the existing
zip -> cPanel pipeline.

Public API:
    render_site(info: dict) -> (html: str, ctx: dict)
        ctx carries the chosen image filenames (hero_img/about_img/about_img2/
        coverage_img) so the caller can copy them into the zip's images/ dir.

The module reuses website_generator's image pools, no-repeat picker, owner-name
resolver and the breakout-safe company-data <script> embed, so /appeal and the
CSV-autofill flow keep working unchanged.
"""

import colorsys
import random
from string import Template

from website_generator import (
    _resolve_owner_name,
    _company_data_script,
    _ASSETS_DIR,
    _HERO_IMAGES,
    _ABOUT_IMAGES,
    _COVERAGE_IMAGES,
    _pick_unique,
    _load_img_state,
    _save_img_state,
)


# ─────────────────────────────────────────────────────────────────────────────
# Colour: procedural HSL palette generation (effectively infinite identities)
# ─────────────────────────────────────────────────────────────────────────────

def _hex(h, s, l):
    """HSL (h 0-360, s/l 0-100) -> #RRGGBB."""
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, max(0, min(1, l / 100.0)),
                                  max(0, min(1, s / 100.0)))
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def _rgb(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l / 100.0, s / 100.0)
    return "%d,%d,%d" % (round(r * 255), round(g * 255), round(b * 255))


# Curated brand hue families so palettes always feel intentional, never muddy.
_HUE_FAMILIES = [
    (215, "blue"), (228, "indigo"), (255, "violet"), (160, "emerald"),
    (188, "teal"), (12, "ember"), (28, "amber"), (345, "crimson"),
    (200, "azure"), (142, "green"), (270, "purple"), (96, "lime"),
]


def _make_palette(mode="light", hue=None):
    """Return a token dict for a studio. mode: 'light' | 'dark'."""
    base, fam = random.choice(_HUE_FAMILIES) if hue is None else (hue, "custom")
    base += random.randint(-8, 8)
    p_s = random.randint(68, 86)
    p_l = random.randint(48, 56)
    primary = _hex(base, p_s, p_l)
    primary2 = _hex(base + random.choice([-26, 24, 32]), p_s, min(60, p_l + 6))
    accent = _hex(base + random.choice([150, 168, -150]), 70, 56)
    on_primary = "#0B0B0F" if p_l > 62 else "#FFFFFF"
    prgb = _rgb(base, p_s, p_l)

    if mode == "dark":
        return {
            "mode": "dark", "family": fam,
            "bg": _hex(base, 24, 6), "bg2": _hex(base, 22, 9),
            "surface": _hex(base, 20, 11), "surface2": _hex(base, 18, 15),
            "text": _hex(base, 16, 96), "muted": _hex(base, 12, 66),
            "border": _hex(base, 20, 20), "border2": _hex(base, 22, 26),
            "primary": primary, "primary2": primary2, "accent": accent,
            "on_primary": on_primary, "prgb": prgb,
            "shadow": "0 24px 60px -20px rgba(0,0,0,0.65)",
        }
    return {
        "mode": "light", "family": fam,
        "bg": _hex(base, 32, 98), "bg2": _hex(base, 30, 96),
        "surface": "#FFFFFF", "surface2": _hex(base, 34, 97),
        "text": _hex(base, 28, 11), "muted": _hex(base, 12, 42),
        "border": _hex(base, 24, 89), "border2": _hex(base, 22, 84),
        "primary": primary, "primary2": primary2, "accent": accent,
        "on_primary": on_primary, "prgb": prgb,
        "shadow": "0 24px 60px -24px rgba(" + prgb + ",0.30)",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Typography: curated premium Google font pairings
# ─────────────────────────────────────────────────────────────────────────────

def _font_url(*families):
    parts = "&".join("family=" + f for f in families)
    return "https://fonts.googleapis.com/css2?" + parts + "&display=swap"

# (heading, body, url, kind)  kind: 'grotesk' | 'serif' | 'display' | 'mono-ui'
_FONT_PAIRS = [
    ("Space Grotesk", "Inter", _font_url("Space+Grotesk:wght@500;600;700",
     "Inter:wght@400;500;600"), "grotesk"),
    ("Sora", "Inter", _font_url("Sora:wght@600;700;800", "Inter:wght@400;500"), "grotesk"),
    ("Clash Grotesk", "Inter", _font_url("Inter:wght@400;500;600;700"), "grotesk"),
    ("Manrope", "Manrope", _font_url("Manrope:wght@400;500;600;700;800"), "grotesk"),
    ("Plus Jakarta Sans", "Inter", _font_url("Plus+Jakarta+Sans:wght@500;600;700;800",
     "Inter:wght@400;500"), "grotesk"),
    ("Archivo", "Inter", _font_url("Archivo:wght@600;700;800;900", "Inter:wght@400;500"), "display"),
    ("Bricolage Grotesque", "Inter", _font_url("Bricolage+Grotesque:wght@600;700;800",
     "Inter:wght@400;500"), "display"),
    ("Fraunces", "Inter", _font_url("Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700",
     "Inter:wght@400;500"), "serif"),
    ("Playfair Display", "Inter", _font_url("Playfair+Display:wght@600;700;800",
     "Inter:wght@400;500"), "serif"),
    ("Libre Caslon Display", "Inter", _font_url("Libre+Caslon+Display",
     "Inter:wght@400;500;600"), "serif"),
    ("Syne", "Inter", _font_url("Syne:wght@600;700;800", "Inter:wght@400;500"), "display"),
    ("Familjen Grotesk", "Inter", _font_url("Familjen+Grotesk:wght@500;600;700",
     "Inter:wght@400;500"), "grotesk"),
    ("IBM Plex Sans", "IBM Plex Sans", _font_url("IBM+Plex+Sans:wght@400;500;600;700"), "grotesk"),
    ("Outfit", "Inter", _font_url("Outfit:wght@500;600;700;800", "Inter:wght@400;500"), "grotesk"),
]

_MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, monospace"


def _pick_fonts(kinds=None):
    pool = _FONT_PAIRS if not kinds else [f for f in _FONT_PAIRS if f[3] in kinds] or _FONT_PAIRS
    h, b, url, kind = random.choice(pool)
    return {"font_heading": h, "font_body": b, "font_url": url, "font_kind": kind}


# ─────────────────────────────────────────────────────────────────────────────
# Copy pools
# ─────────────────────────────────────────────────────────────────────────────

_HEADLINES = [
    "Drive for {company}.\nGet Home. Get Paid.",
    "Your Best Miles\nStart Here",
    "Real Routes.\nReal Home Time.",
    "More Money.\nMore Miles. More Home.",
    "The Driving Job\nYou've Earned",
    "Built for Drivers\nWho Mean Business",
    "Where CDL-A Drivers\nBuild Careers",
    "Steady Freight.\nStraight Talk.",
]
_SUBHEADS = [
    "{company} is hiring CDL-A company drivers for {routes_type}. Consistent miles, modern equipment, and home time you can plan your life around.",
    "Join {company} and drive newer trucks, run dependable lanes, and get paid every single week — with dispatch that actually answers the phone.",
    "We pay drivers what they're worth and get them home when we promise. {routes_type} out of {city}, no-touch freight, no games.",
    "At {company}, you're a name, not a truck number. Top weekly pay, real benefits, and the respect every professional driver deserves.",
]
_KICKERS = [
    "Now Hiring CDL-A Drivers", "{routes_type}", "{city_state}",
    "Apply in Under 2 Minutes", "Drivers Wanted", "Join the Fleet",
]
_ABOUT_TITLES = [
    "A carrier that runs on respect",
    "Why drivers stay with {company}",
    "We treat drivers like the pros they are",
    "Trucking done the right way",
]
_ABOUT_P1 = [
    "{company} was built by people who understand the road. We know that consistent miles, honest pay, and real home time aren't perks — they're the job.",
    "Out of {city_state}, {company} keeps freight moving with a fleet of well-maintained trucks and a dispatch team that has your back around the clock.",
    "We're not the biggest carrier out there, and that's the point. At {company} you get personal dispatch, predictable routes, and a paycheck you can count on.",
]
_ABOUT_P2 = [
    "From your first orientation to your thousandth mile, you'll have modern equipment, clear communication, and a team that treats you like family.",
    "No lease traps, no surprise deductions, no runaround. Just steady freight, weekly direct deposit, and the home time we put in writing.",
    "Our drivers refer their friends because they actually like working here — and that says more than any recruiting pitch ever could.",
]
_CTA_TITLES = [
    "Ready to roll with {company}?",
    "Your next mile starts here",
    "Let's get you on the road",
    "Apply today. Drive this week.",
]
_CTA_SUBS = [
    "Fill out the form and a recruiter will call you within one business day. No pressure, just a real conversation about the job.",
    "Two minutes now could change your whole driving career. Tell us about yourself and we'll handle the rest.",
    "Spots fill fast on our best lanes. Get your application in and let's talk numbers.",
]

_SERVICES_POOL = [
    ("money", "Top Weekly Pay", "Industry-leading pay with weekly direct deposit. Know exactly what you're making, every single week."),
    ("home", "Real Home Time", "Home time we put in writing and actually honor. Plan your life around a schedule you can trust."),
    ("truck", "Modern Equipment", "Late-model trucks, well maintained and driver-spec'd. Comfortable miles in a rig you'll be proud to drive."),
    ("route", "Consistent Miles", "Dependable lanes and steady freight mean a full week of miles — no sitting, no waiting, no excuses."),
    ("shield", "Full Benefits", "Medical, dental and vision plus retirement options. Real coverage for you and your family."),
    ("clock", "24/7 Dispatch", "A dispatch team that answers the phone day or night. When you need an answer, you get one."),
    ("medal", "Safety Bonuses", "We reward the pros who do it right with safety, fuel, and performance bonuses on top of base pay."),
    ("heart", "Driver Respect", "No truck numbers, no runaround. You're a professional and we treat you like one, every mile."),
    ("bolt", "Quick Pay Options", "Fast settlements and transparent statements. Your money, when you've earned it."),
]
_PROCESS_STEPS = [
    ("Apply Online", "Fill out our short application in under two minutes — no lengthy forms, no commitment."),
    ("Quick Phone Call", "A real recruiter calls to talk through pay, lanes and home time, and answer every question."),
    ("Fast Orientation", "Streamlined orientation gets you road-ready quickly, with everything you need to succeed."),
    ("Hit the Road", "Pick up your truck, meet your dispatcher, and start earning on lanes built for drivers."),
]
_TESTIMONIALS = [
    ("Best move I've made in fifteen years of driving. Pay is exactly what they promised and I'm home when they say.", "Marcus T.", "Company Driver, 2 yrs"),
    ("Dispatch actually picks up the phone. After my last carrier, that alone is worth it. Trucks are clean and new too.", "Dana R.", "OTR Driver, 18 mo"),
    ("They run me steady miles and the paycheck never surprises me. Already got two buddies to come over.", "Curtis W.", "Regional Driver, 3 yrs"),
    ("Finally a carrier that treats you like a person. Home time is real and the equipment is top notch.", "Yolanda B.", "Company Driver, 1 yr"),
    ("Straightforward people, honest pay, good freight. Exactly what I was looking for and hard to find these days.", "Hector M.", "OTR Driver, 4 yrs"),
    ("Orientation was quick and I was earning by the end of the week. No nonsense, just a solid driving job.", "Renee P.", "Regional Driver, 8 mo"),
]


def _fmt(s, d):
    try:
        return s.format(**d)
    except (KeyError, IndexError):
        return s


# ─────────────────────────────────────────────────────────────────────────────
# Inline line-icons (premium, stroke = currentColor)
# ─────────────────────────────────────────────────────────────────────────────

_ICON_PATHS = {
    "money": '<rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M5 9v.01M19 15v.01"/>',
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "truck": '<path d="M1 6h13v10H1z"/><path d="M14 9h4l3 3v4h-7"/><circle cx="5.5" cy="18" r="1.8"/><circle cx="17.5" cy="18" r="1.8"/>',
    "route": '<circle cx="6" cy="19" r="2.2"/><circle cx="18" cy="5" r="2.2"/><path d="M8.2 19H15a4 4 0 0 0 0-8H9a4 4 0 0 1 0-8h6.8"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8.2-8 9-4.5-.8-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "medal": '<circle cx="12" cy="9" r="6"/><path d="M9 14l-1.8 7L12 18l4.8 3L15 14"/>',
    "heart": '<path d="M12 21C5 14 3 9.2 6 6.2c2-2 5-1 6 1 1-2 4-3 6-1 3 3 1 7.8-6 14.8z"/>',
    "bolt": '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
}


def _icon(name):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true">' + _ICON_PATHS.get(name, _ICON_PATHS["bolt"]) + '</svg>')


# ─────────────────────────────────────────────────────────────────────────────
# Shared vanilla-JS runtime (reveals, count-up, header, mobile nav, form, tilt)
# ─────────────────────────────────────────────────────────────────────────────

_BASE_JS = """
(function(){
  var hdr=document.querySelector('[data-hdr]');
  if(hdr){var onScroll=function(){hdr.classList.toggle('scrolled',window.scrollY>24);};onScroll();window.addEventListener('scroll',onScroll,{passive:true});}
  var tgl=document.querySelector('[data-menu-toggle]'),nav=document.querySelector('[data-mobile-nav]');
  if(tgl&&nav){tgl.addEventListener('click',function(){var o=nav.classList.toggle('open');tgl.classList.toggle('open',o);document.body.style.overflow=o?'hidden':'';});
    nav.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){nav.classList.remove('open');tgl.classList.remove('open');document.body.style.overflow='';});});}
  var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:0.12,rootMargin:'0px 0px -40px 0px'});
  document.querySelectorAll('[data-rev]').forEach(function(el,i){el.style.transitionDelay=(Math.min(i,6)*60)+'ms';io.observe(el);});
  function countUp(el){var raw=el.getAttribute('data-count'),m=raw.match(/[0-9][0-9,\\.]*/);if(!m){el.textContent=raw;return;}
    var num=parseFloat(m[0].replace(/,/g,'')),pre=raw.slice(0,m.index),post=raw.slice(m.index+m[0].length),t0=null,dur=1500;
    function tick(ts){if(!t0)t0=ts;var p=Math.min((ts-t0)/dur,1),e=1-Math.pow(1-p,3),v=num*e;
      el.textContent=pre+(num%1!==0?v.toFixed(1):Math.round(v).toLocaleString())+post;if(p<1)requestAnimationFrame(tick);}
    requestAnimationFrame(tick);}
  var cio=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){countUp(e.target);cio.unobserve(e.target);}});},{threshold:0.6});
  document.querySelectorAll('[data-count]').forEach(function(el){cio.observe(el);});
  document.querySelectorAll('[data-tilt]').forEach(function(c){c.addEventListener('mousemove',function(ev){var r=c.getBoundingClientRect(),x=(ev.clientX-r.left)/r.width-0.5,y=(ev.clientY-r.top)/r.height-0.5;c.style.transform='perspective(800px) rotateX('+(-y*5)+'deg) rotateY('+(x*5)+'deg) translateY(-4px)';});c.addEventListener('mouseleave',function(){c.style.transform='';});});
  document.querySelectorAll('[data-magnet]').forEach(function(b){b.addEventListener('mousemove',function(ev){var r=b.getBoundingClientRect();b.style.transform='translate('+((ev.clientX-r.left)/r.width-0.5)*10+'px,'+((ev.clientY-r.top)/r.height-0.5)*10+'px)';});b.addEventListener('mouseleave',function(){b.style.transform='';});});
  document.querySelectorAll('form[data-form]').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault();var b=f.querySelector('[type=submit]');if(b){var o=b.textContent;b.textContent='Application sent ✓';b.disabled=true;setTimeout(function(){b.textContent=o;b.disabled=false;},2600);}f.reset();});});
})();
"""


# ─────────────────────────────────────────────────────────────────────────────
# Context builder — shared data for every studio
# ─────────────────────────────────────────────────────────────────────────────

def _build_data(info):
    company = info.get("company_name", "Our Company")
    short = info.get("company_short") or company.split()[0]
    city_state = info.get("city_state", "")
    city = city_state.split(",")[0].strip() if "," in city_state else city_state
    state = ""
    if "," in city_state:
        tail = city_state.split(",")[1].strip().split()
        state = tail[0] if tail else ""

    d = {
        "company": company, "short": short, "domain": info.get("domain", ""),
        "email": info.get("email", "") or ("careers@" + info.get("domain", "company.com")),
        "address": info.get("address", ""), "city_state": city_state,
        "city": city or "the region", "state": state,
        "job_title": info.get("job_title", "CDL-A Driver"),
        "pay_range": info.get("pay_range", "$1,400 - $1,700 / wk"),
        "home_time": info.get("home_time", "Home every 2 weeks"),
        "home_time_short": info.get("home_time_short", "2 Weeks Out"),
        "min_experience": info.get("min_experience", "6 Mo. Exp"),
        "routes": info.get("routes", "48 States"),
        "routes_type": info.get("routes_type", "OTR Routes"),
        "year": "2026",
    }
    d["owner_name"] = _resolve_owner_name(d["email"], d["domain"])

    # logo split: last word accented
    parts = short.split()
    if len(parts) >= 2:
        d["logo_main"], d["logo_accent"] = " ".join(parts[:-1]), parts[-1]
    else:
        d["logo_main"], d["logo_accent"] = short, ""

    # copy
    d["headline"] = _fmt(random.choice(_HEADLINES), d)
    d["subhead"] = _fmt(random.choice(_SUBHEADS), d)
    d["kicker"] = _fmt(random.choice(_KICKERS), d)
    d["about_title"] = _fmt(random.choice(_ABOUT_TITLES), d)
    d["about_p1"] = _fmt(random.choice(_ABOUT_P1), d)
    d["about_p2"] = _fmt(random.choice(_ABOUT_P2), d)
    d["cta_title"] = _fmt(random.choice(_CTA_TITLES), d)
    d["cta_sub"] = _fmt(random.choice(_CTA_SUBS), d)

    # structured data
    stats_all = [
        (d["pay_range"], "Weekly Pay"), (d["home_time_short"], "Home Time"),
        (d["min_experience"], "To Qualify"), (d["routes"], "Coverage"),
        ("100%", "No-Touch Freight"), ("24/7", "Dispatch Support"),
    ]
    d["stats"] = stats_all[:4]
    svc = _SERVICES_POOL[:]
    random.shuffle(svc)
    d["services"] = svc[:6]
    d["process"] = _PROCESS_STEPS[:]
    test = _TESTIMONIALS[:]
    random.shuffle(test)
    d["testimonials"] = test[:3]
    perks = info.get("perks", []) or [
        "Weekly Direct Deposit", "Paid Orientation", "Newer Equipment",
        "Medical / Dental / Vision", "Rider & Pet Program", "Referral Bonuses",
    ]
    d["perks"] = perks[:8]
    d["nav"] = [("Careers", "#services"), ("Why Us", "#why"),
                ("Process", "#process"), ("Reviews", "#reviews")]

    # images
    st = _load_img_state()
    d["hero_img"] = _pick_unique(_HERO_IMAGES, 1, "hero", st, "hero_1.jpg")[0]
    ab = _pick_unique(_ABOUT_IMAGES, 2, "about", st, "about_11.jpg")
    d["about_img"], d["about_img2"] = ab[0], ab[1]
    d["coverage_img"] = _pick_unique(_COVERAGE_IMAGES, 1, "coverage", st, "coverage_21.jpg")[0]
    _save_img_state(st)
    d["hero_src"] = "images/" + d["hero_img"]
    d["about_src"] = "images/" + d["about_img"]
    d["about2_src"] = "images/" + d["about_img2"]
    d["coverage_src"] = "images/" + d["coverage_img"]
    return d


def _company_data(d):
    return {
        "company_name": d["company"], "domain": d["domain"], "email": d["email"],
        "address": d["address"], "city_state": d["city_state"],
        "owner_name": d["owner_name"], "job_title": d["job_title"],
        "pay_range": d["pay_range"], "home_time": d["home_time"],
        "min_experience": d["min_experience"], "routes_type": d["routes_type"],
        "perks": d["perks"],
    }


def _head(d, css):
    """Shared <head> with palette :root vars + studio css."""
    p = d["pal"]
    root = (":root{"
            "--bg:%(bg)s;--bg2:%(bg2)s;--surface:%(surface)s;--surface2:%(surface2)s;"
            "--text:%(text)s;--muted:%(muted)s;--border:%(border)s;--border2:%(border2)s;"
            "--primary:%(primary)s;--primary2:%(primary2)s;--accent:%(accent)s;"
            "--on-primary:%(on_primary)s;--prgb:%(prgb)s;--shadow:%(shadow)s;}" % p)
    base = ("*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}"
            "html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}"
            "img{max-width:100%;display:block}a{text-decoration:none;color:inherit}"
            "ul{list-style:none}button{font:inherit;cursor:pointer}"
            "::selection{background:var(--primary);color:var(--on-primary)}"
            "body{font-family:'" + d["font_body"] + "',system-ui,sans-serif;background:var(--bg);"
            "color:var(--text);line-height:1.65;overflow-x:hidden;-webkit-font-smoothing:antialiased}"
            "h1,h2,h3,h4{font-family:'" + d["font_heading"] + "',system-ui,sans-serif;line-height:1.07}"
            "[data-rev]{opacity:0;transform:translateY(26px);transition:opacity .7s cubic-bezier(.16,1,.3,1),transform .7s cubic-bezier(.16,1,.3,1)}"
            "[data-rev].in{opacity:1;transform:none}"
            ".wrap{max-width:1200px;margin:0 auto;padding:0 24px;width:100%}")
    return ("<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"UTF-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>" + d["company"] + " — CDL-A Driver Jobs | " + d["city_state"] + "</title>"
            "<meta name=\"description\" content=\"" + d["company"] + " is hiring CDL-A drivers in "
            + d["city_state"] + ". " + d["routes_type"] + ", top weekly pay, real home time.\">"
            "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">"
            "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
            "<link href=\"" + d["font_url"] + "\" rel=\"stylesheet\">"
            "<style>" + root + base + css + "</style></head>")


def _apply_form(d, cls=""):
    return (
        '<form data-form class="' + cls + '">'
        '<div class="ff"><input name="name" placeholder="Full name" required></div>'
        '<div class="ff"><input name="phone" type="tel" placeholder="Phone number" required></div>'
        '<div class="ff"><input name="email" type="email" placeholder="Email address"></div>'
        '<div class="ff"><select name="exp"><option value="">Driving experience</option>'
        '<option>0-6 months</option><option>6-12 months</option><option>1-3 years</option>'
        '<option>3+ years</option></select></div>'
        '<button type="submit">Apply Now</button>'
        '<p class="ff-note">By submitting you agree to be contacted about driving opportunities. '
        'We respect your privacy.</p></form>')


def _assemble(d, head, body):
    html = head + "<body>" + body + "<script>" + _BASE_JS + "</script></body></html>"
    # guarantee the breakout-safe company-data embed is present
    return html.replace("</body>", _company_data_script(_company_data(d)) + "</body>", 1)


# ─────────────────────────────────────────────────────────────────────────────
# Small shared markup helpers
# ─────────────────────────────────────────────────────────────────────────────

def _nav_links(d, acls="navlink"):
    return "".join('<a class="%s" href="%s">%s</a>' % (acls, href, txt) for txt, href in d["nav"])


def _mobile_nav(d):
    links = "".join('<a href="%s">%s</a>' % (href, txt) for txt, href in d["nav"])
    links += '<a href="#apply">Apply Now</a>'
    return ('<button class="burger" data-menu-toggle aria-label="Menu">'
            '<span></span><span></span><span></span></button>'
            '<div class="mobnav" data-mobile-nav>' + links + '</div>')


# ─────────────────────────────────────────────────────────────────────────────
# STUDIO 1 — AURORA  (light · glassmorphism · modern SaaS · gradient mesh)
# ─────────────────────────────────────────────────────────────────────────────

def studio_aurora(info):
    d = _build_data(info)
    d["pal"] = _make_palette("light")
    d.update(_pick_fonts(["grotesk", "display"]))

    stats = "".join(
        '<div class="bento b%d" data-rev><div class="bv" data-count="%s">%s</div>'
        '<div class="bl">%s</div></div>' % (i, v, v, l)
        for i, (v, l) in enumerate(d["stats"]))
    services = "".join(
        '<article class="gcard" data-tilt data-rev><div class="gico">%s</div>'
        '<h3>%s</h3><p>%s</p></article>' % (_icon(ic), t, desc)
        for ic, t, desc in d["services"])
    process = "".join(
        '<div class="pstep" data-rev><span class="pnum">%02d</span>'
        '<h4>%s</h4><p>%s</p></div>' % (i + 1, t, desc)
        for i, (t, desc) in enumerate(d["process"]))
    testimonials = "".join(
        '<figure class="tcard" data-rev><div class="stars">★★★★★</div>'
        '<blockquote>“%s”</blockquote><figcaption><strong>%s</strong><span>%s</span>'
        '</figcaption></figure>' % (q, n, r)
        for q, n, r in d["testimonials"])
    perks = "".join('<li data-rev>%s%s</li>' % (_icon("check"), p) for p in d["perks"])

    css = """
    .btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:15px 30px;border-radius:999px;font-family:'$font_heading';font-weight:700;font-size:.95rem;border:1px solid transparent;transition:transform .25s,box-shadow .25s}
    .btn-p{background:linear-gradient(120deg,var(--primary),var(--primary2));color:var(--on-primary);box-shadow:0 12px 30px -8px rgba(var(--prgb),.5)}
    .btn-p:hover{transform:translateY(-3px);box-shadow:0 20px 44px -10px rgba(var(--prgb),.6)}
    .btn-g{background:rgba(255,255,255,.6);color:var(--text);border-color:var(--border2);backdrop-filter:blur(10px)}
    .btn-g:hover{transform:translateY(-3px)}
    header{position:fixed;top:18px;left:0;right:0;z-index:100;display:flex;justify-content:center;transition:top .3s}
    .navbar{display:flex;align-items:center;gap:28px;padding:11px 12px 11px 24px;border-radius:999px;background:rgba(255,255,255,.7);backdrop-filter:blur(18px) saturate(160%);border:1px solid rgba(255,255,255,.7);box-shadow:0 10px 40px -12px rgba(var(--prgb),.22);width:min(1120px,calc(100% - 32px))}
    .logo{font-family:'$font_heading';font-weight:800;font-size:1.3rem;letter-spacing:-.5px;margin-right:auto}
    .logo span{background:linear-gradient(120deg,var(--primary),var(--primary2));-webkit-background-clip:text;background-clip:text;color:transparent}
    .navlink{font-size:.9rem;font-weight:600;color:var(--muted);transition:color .2s}.navlink:hover{color:var(--text)}
    .nav-cta{padding:10px 22px;border-radius:999px;background:linear-gradient(120deg,var(--primary),var(--primary2));color:var(--on-primary);font-weight:700;font-size:.9rem}
    .burger{display:none;flex-direction:column;gap:5px;background:none;border:none}.burger span{width:24px;height:2px;background:var(--text);border-radius:2px;transition:.3s}
    .burger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}.burger.open span:nth-child(2){opacity:0}.burger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
    .mobnav{display:none;position:fixed;inset:0;z-index:99;background:rgba(255,255,255,.97);backdrop-filter:blur(20px);flex-direction:column;align-items:center;justify-content:center;gap:30px}
    .mobnav.open{display:flex}.mobnav a{font-family:'$font_heading';font-size:1.5rem;font-weight:700}
    .hero{position:relative;padding:190px 0 110px;overflow:hidden}
    .mesh{position:absolute;inset:0;z-index:-1;background:
      radial-gradient(60% 50% at 15% 0%,rgba(var(--prgb),.28),transparent 60%),
      radial-gradient(50% 50% at 90% 10%,rgba(var(--prgb),.16),transparent 55%),
      radial-gradient(45% 45% at 70% 90%,rgba(var(--prgb),.14),transparent 60%)}
    .mesh::after{content:'';position:absolute;inset:0;background-image:radial-gradient(circle at 1px 1px,rgba(var(--prgb),.10) 1px,transparent 0);background-size:34px 34px;-webkit-mask:radial-gradient(70% 60% at 50% 20%,#000,transparent);mask:radial-gradient(70% 60% at 50% 20%,#000,transparent)}
    .hero-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:56px;align-items:center}
    .pill{display:inline-flex;align-items:center;gap:9px;padding:7px 16px;border-radius:999px;background:rgba(255,255,255,.7);border:1px solid var(--border2);backdrop-filter:blur(8px);font-size:.8rem;font-weight:600;color:var(--muted);margin-bottom:24px}
    .pill b{color:var(--primary)}.dot{width:7px;height:7px;border-radius:50%;background:var(--primary);box-shadow:0 0 0 4px rgba(var(--prgb),.18);animation:pl 2s infinite}
    @keyframes pl{50%{opacity:.4}}
    .hero h1{font-size:clamp(2.6rem,5.6vw,4.4rem);font-weight:800;letter-spacing:-2px;white-space:pre-line}
    .hero h1 em{font-style:normal;background:linear-gradient(120deg,var(--primary),var(--primary2));-webkit-background-clip:text;background-clip:text;color:transparent}
    .hero p.sub{font-size:1.12rem;color:var(--muted);max-width:520px;margin:22px 0 34px}
    .hero-cta{display:flex;gap:14px;flex-wrap:wrap}
    .trust{display:flex;gap:24px;margin-top:34px;flex-wrap:wrap;align-items:center;color:var(--muted);font-size:.85rem;font-weight:600}
    .trust .av{display:flex}.trust .av i{width:30px;height:30px;border-radius:50%;border:2px solid var(--bg);margin-left:-9px;background:linear-gradient(120deg,var(--primary),var(--primary2))}
    .hero-visual{position:relative}
    .hero-visual img{border-radius:24px;box-shadow:var(--shadow);width:100%;aspect-ratio:4/5;object-fit:cover}
    .float{position:absolute;background:rgba(255,255,255,.78);backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,.8);border-radius:16px;padding:14px 18px;box-shadow:0 16px 40px -12px rgba(var(--prgb),.3);animation:fl 5s ease-in-out infinite}
    @keyframes fl{50%{transform:translateY(-12px)}}
    .float.f1{top:30px;left:-28px}.float.f2{bottom:40px;right:-22px;animation-delay:1.5s}
    .float .fv{font-family:'$font_heading';font-weight:800;font-size:1.3rem;color:var(--primary)}.float .fl{font-size:.72rem;color:var(--muted);font-weight:600}
    .section{padding:104px 0}
    .shead{text-align:center;max-width:640px;margin:0 auto 60px}
    .klabel{font-size:.74rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--primary)}
    .shead h2{font-size:clamp(2rem,4vw,3rem);font-weight:800;letter-spacing:-1px;margin:12px 0}
    .shead p{color:var(--muted);font-size:1.05rem}
    .bento-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
    .bento{background:var(--surface);border:1px solid var(--border);border-radius:22px;padding:34px 26px;text-align:center;box-shadow:0 1px 0 rgba(255,255,255,.6) inset}
    .bento.b0{background:linear-gradient(135deg,var(--primary),var(--primary2));color:var(--on-primary);border:none}
    .bv{font-family:'$font_heading';font-weight:800;font-size:2.1rem;letter-spacing:-1px}
    .bl{font-size:.82rem;text-transform:uppercase;letter-spacing:1px;opacity:.8;margin-top:6px}
    .cards{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
    .gcard{background:var(--surface);border:1px solid var(--border);border-radius:22px;padding:32px;transition:transform .3s,box-shadow .3s;transform-style:preserve-3d}
    .gcard:hover{box-shadow:var(--shadow)}
    .gico{width:54px;height:54px;border-radius:15px;display:grid;place-items:center;background:linear-gradient(135deg,rgba(var(--prgb),.16),rgba(var(--prgb),.06));color:var(--primary);margin-bottom:18px}
    .gico svg{width:26px;height:26px}.gcard h3{font-size:1.18rem;font-weight:700;margin-bottom:9px}.gcard p{color:var(--muted);font-size:.95rem}
    .why{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center}
    .why-img{position:relative}.why-img img{border-radius:22px;box-shadow:var(--shadow);aspect-ratio:1/1;object-fit:cover}
    .why h2{font-size:clamp(1.9rem,3.6vw,2.7rem);font-weight:800;letter-spacing:-1px;margin-bottom:18px}
    .why p{color:var(--muted);margin-bottom:14px}
    .perks{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}
    .perks li{display:flex;align-items:center;gap:10px;font-weight:600;font-size:.93rem}
    .perks svg{width:20px;height:20px;color:var(--primary);flex-shrink:0}
    .pgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;counter-reset:s}
    .pstep{background:var(--surface);border:1px solid var(--border);border-radius:20px;padding:30px 24px;position:relative}
    .pnum{font-family:'$font_heading';font-weight:800;font-size:2.4rem;background:linear-gradient(120deg,var(--primary),var(--primary2));-webkit-background-clip:text;background-clip:text;color:transparent}
    .pstep h4{font-size:1.1rem;margin:8px 0}.pstep p{color:var(--muted);font-size:.9rem}
    .tgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
    .tcard{background:var(--surface);border:1px solid var(--border);border-radius:22px;padding:30px}
    .stars{color:var(--primary);letter-spacing:2px;margin-bottom:14px}
    .tcard blockquote{font-size:1.02rem;line-height:1.6;margin-bottom:18px}
    .tcard figcaption strong{display:block}.tcard figcaption span{font-size:.85rem;color:var(--muted)}
    .cta{position:relative;border-radius:34px;overflow:hidden;padding:70px;background:linear-gradient(135deg,var(--primary),var(--primary2));color:var(--on-primary);display:grid;grid-template-columns:1fr 1fr;gap:50px;align-items:center}
    .cta::before{content:'';position:absolute;inset:0;background:radial-gradient(circle at 80% 20%,rgba(255,255,255,.18),transparent 50%)}
    .cta>*{position:relative}.cta h2{font-size:clamp(1.9rem,3.6vw,2.8rem);font-weight:800;letter-spacing:-1px}.cta p{opacity:.9;margin-top:14px}
    form{display:grid;gap:12px;background:rgba(255,255,255,.14);backdrop-filter:blur(10px);padding:26px;border-radius:22px;border:1px solid rgba(255,255,255,.25)}
    .ff input,.ff select{width:100%;padding:13px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.92);color:#111;font:inherit;font-size:.92rem}
    form button{padding:15px;border-radius:12px;border:none;background:#0b0b0f;color:#fff;font-family:'$font_heading';font-weight:700}
    .ff-note{font-size:.72rem;opacity:.8;text-align:center}
    footer{padding:64px 0 30px;border-top:1px solid var(--border)}
    .foot{display:flex;justify-content:space-between;gap:30px;flex-wrap:wrap;align-items:center}
    .foot .logo{font-size:1.2rem}.foot-links{display:flex;gap:22px;color:var(--muted);font-size:.9rem;font-weight:600}
    .copy{margin-top:30px;color:var(--muted);font-size:.82rem;text-align:center;border-top:1px solid var(--border);padding-top:24px}
    @media(max-width:920px){.hero-grid,.why,.cta{grid-template-columns:1fr;gap:40px}.bento-grid,.pgrid{grid-template-columns:repeat(2,1fr)}.cards,.tgrid{grid-template-columns:1fr}.navlink,.nav-cta{display:none}.burger{display:flex}.hero-visual{max-width:420px;margin:0 auto}.cta{padding:44px 26px}}
    @media(max-width:560px){.bento-grid,.perks{grid-template-columns:1fr}}
    """

    body = (
        '<header data-hdr><nav class="navbar"><div class="logo">$logo_main<span>$logo_accent</span></div>'
        + _nav_links(d) +
        '<a class="nav-cta" href="#apply">Apply Now</a>'
        '<button class="burger" data-menu-toggle aria-label="Menu"><span></span><span></span><span></span></button></nav>'
        '<div class="mobnav" data-mobile-nav>' + _nav_links(d, "") + '<a href="#apply">Apply Now</a></div></header>'
        '<section class="hero"><div class="mesh"></div><div class="wrap hero-grid">'
        '<div class="hero-copy"><span class="pill"><span class="dot"></span>$kicker · <b>$city_state</b></span>'
        '<h1>$headline</h1><p class="sub">$subhead</p>'
        '<div class="hero-cta"><a class="btn btn-p" data-magnet href="#apply">Start Your Application</a>'
        '<a class="btn btn-g" href="#why">Why $short</a></div>'
        '<div class="trust"><span class="av"><i></i><i></i><i></i><i></i></span>Trusted by drivers who don’t settle</div></div>'
        '<div class="hero-visual" data-rev><img src="$hero_src" alt="$company truck">'
        '<div class="float f1"><div class="fv">$pay_range</div><div class="fl">Weekly Pay</div></div>'
        '<div class="float f2"><div class="fv">$home_time_short</div><div class="fl">Home Time</div></div></div></div></section>'
        '<section class="section"><div class="wrap"><div class="bento-grid">' + stats + '</div></div></section>'
        '<section class="section" id="services"><div class="wrap"><div class="shead"><span class="klabel">What You Get</span>'
        '<h2>Built around the driver</h2><p>Everything we do is designed to keep you earning, rolling, and home on time.</p></div>'
        '<div class="cards">' + services + '</div></div></section>'
        '<section class="section" id="why"><div class="wrap why"><div class="why-img" data-rev><img src="$about_src" alt="$company"></div>'
        '<div data-rev><span class="klabel">Why $short</span><h2>$about_title</h2><p>$about_p1</p><p>$about_p2</p>'
        '<ul class="perks">' + perks + '</ul></div></div></section>'
        '<section class="section" id="process"><div class="wrap"><div class="shead"><span class="klabel">Getting Started</span>'
        '<h2>On the road in four steps</h2></div><div class="pgrid">' + process + '</div></div></section>'
        '<section class="section" id="reviews"><div class="wrap"><div class="shead"><span class="klabel">Driver Reviews</span>'
        '<h2>Drivers say it best</h2></div><div class="tgrid">' + testimonials + '</div></div></section>'
        '<section class="section" id="apply"><div class="wrap"><div class="cta"><div><h2>$cta_title</h2><p>$cta_sub</p></div>'
        + _apply_form(d) + '</div></div></section>'
        '<footer><div class="wrap"><div class="foot"><div class="logo">$logo_main<span>$logo_accent</span></div>'
        '<div class="foot-links">' + _nav_links(d, "") + '</div></div>'
        '<div class="copy">© $year $company · $city_state · Equal Opportunity Employer. '
        'All qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</div></div></footer>'
    )
    return _assemble(d, _head(d, Template(css).safe_substitute(d)), Template(body).safe_substitute(d)), d


# ─────────────────────────────────────────────────────────────────────────────
# STUDIO 2 — MONOLITH  (dark · cinematic · automotive / industrial premium)
# ─────────────────────────────────────────────────────────────────────────────

def studio_monolith(info):
    d = _build_data(info)
    d["pal"] = _make_palette("dark")
    d.update(_pick_fonts(["display", "grotesk"]))

    stats = "".join(
        '<div class="mstat" data-rev><div class="mv" data-count="%s">%s</div><div class="ml">%s</div></div>'
        % (v, v, l) for v, l in d["stats"])
    services = "".join(
        '<div class="srow" data-rev><span class="sidx">%02d</span><div class="sico">%s</div>'
        '<div class="sbody"><h3>%s</h3><p>%s</p></div></div>' % (i + 1, _icon(ic), t, desc)
        for i, (ic, t, desc) in enumerate(d["services"]))
    process = "".join(
        '<div class="tl-item" data-rev><div class="tl-dot">%02d</div><div><h4>%s</h4><p>%s</p></div></div>'
        % (i + 1, t, desc) for i, (t, desc) in enumerate(d["process"]))
    testimonials = "".join(
        '<figure class="mt" data-rev><blockquote>“%s”</blockquote>'
        '<figcaption><b>%s</b><span>%s</span></figcaption></figure>' % (q, n, r)
        for q, n, r in d["testimonials"])
    perks = "".join('<li data-rev>%s%s</li>' % (_icon("check"), p) for p in d["perks"])

    css = """
    body{background:var(--bg)}
    .btn{display:inline-flex;align-items:center;gap:10px;padding:16px 34px;font-family:'$font_heading';font-weight:700;font-size:.92rem;letter-spacing:.3px;border:1px solid transparent;transition:.25s;text-transform:uppercase}
    .btn-p{background:var(--primary);color:var(--on-primary)}.btn-p:hover{background:var(--primary2);transform:translateY(-2px)}
    .btn-o{border-color:var(--border2);color:var(--text)}.btn-o:hover{border-color:var(--primary);color:var(--primary)}
    header{position:fixed;top:0;width:100%;z-index:100;transition:.3s;border-bottom:1px solid transparent}
    header.scrolled{background:rgba(var(--prgb),.04);backdrop-filter:blur(16px);border-bottom-color:var(--border)}
    .nav{display:flex;align-items:center;justify-content:space-between;height:78px}
    .logo{font-family:'$font_heading';font-weight:800;font-size:1.4rem;letter-spacing:.5px;text-transform:uppercase}.logo span{color:var(--primary)}
    .navlink{font-size:.82rem;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-left:30px;transition:.2s}.navlink:hover{color:var(--text)}
    .nav-cta{margin-left:30px;padding:11px 24px;background:var(--primary);color:var(--on-primary);font-weight:700;font-size:.8rem;letter-spacing:1px;text-transform:uppercase}
    .burger{display:none;flex-direction:column;gap:5px;background:none;border:none}.burger span{width:26px;height:2px;background:var(--text);transition:.3s}
    .burger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}.burger.open span:nth-child(2){opacity:0}.burger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
    .mobnav{display:none;position:fixed;inset:0;z-index:99;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;gap:28px}.mobnav.open{display:flex}.mobnav a{font-family:'$font_heading';font-size:1.4rem;font-weight:700;text-transform:uppercase}
    .hero{position:relative;min-height:100vh;display:flex;align-items:flex-end;padding-bottom:70px;overflow:hidden}
    .hero-bg{position:absolute;inset:0;z-index:-2}.hero-bg img{width:100%;height:100%;object-fit:cover;filter:grayscale(.3) contrast(1.05)}
    .hero-bg::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(var(--prgb),.12) 0%,transparent 30%,var(--bg) 96%),linear-gradient(90deg,var(--bg) 5%,transparent 55%)}
    .hero-kick{display:inline-flex;align-items:center;gap:10px;font-size:.8rem;letter-spacing:3px;text-transform:uppercase;color:var(--primary);font-weight:700;margin-bottom:22px}
    .hero-kick::before{content:'';width:40px;height:1px;background:var(--primary)}
    .hero h1{font-family:'$font_heading';font-size:clamp(3rem,9vw,7rem);font-weight:800;line-height:.95;letter-spacing:-2px;text-transform:uppercase;white-space:pre-line}
    .hero p{color:var(--muted);font-size:1.15rem;max-width:540px;margin:26px 0 36px}
    .hero-cta{display:flex;gap:14px;flex-wrap:wrap}
    .section{padding:120px 0}.section.alt{background:var(--bg2)}
    .shead{max-width:680px;margin-bottom:64px}
    .klabel{font-size:.78rem;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--primary)}
    .shead h2{font-family:'$font_heading';font-size:clamp(2.2rem,5vw,3.6rem);font-weight:800;text-transform:uppercase;letter-spacing:-1px;margin-top:14px}
    .shead p{color:var(--muted);margin-top:14px;font-size:1.05rem}
    .mstats{display:grid;grid-template-columns:repeat(4,1fr)}
    .mstat{padding:38px 28px;border-left:1px solid var(--border)}.mstat:first-child{border-left:none}
    .mv{font-family:'$font_heading';font-size:clamp(2.2rem,4vw,3.2rem);font-weight:800;color:var(--primary);letter-spacing:-1px}
    .ml{font-size:.82rem;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-top:8px}
    .srow{display:grid;grid-template-columns:auto auto 1fr;gap:26px;align-items:center;padding:30px 0;border-top:1px solid var(--border);transition:.3s}
    .srow:hover{padding-left:14px}.srow:last-child{border-bottom:1px solid var(--border)}
    .sidx{font-family:'$font_heading';font-weight:800;font-size:1rem;color:var(--muted)}
    .sico{width:52px;height:52px;border:1px solid var(--border2);border-radius:50%;display:grid;place-items:center;color:var(--primary)}.sico svg{width:24px;height:24px}
    .sbody h3{font-family:'$font_heading';font-size:1.4rem;font-weight:700;text-transform:uppercase}.sbody p{color:var(--muted);margin-top:5px;max-width:620px}
    .why{display:grid;grid-template-columns:1.1fr .9fr;gap:60px;align-items:center}
    .why-img img{aspect-ratio:4/5;object-fit:cover;filter:grayscale(.2)}
    .why h2{font-family:'$font_heading';font-size:clamp(2rem,4vw,3rem);font-weight:800;text-transform:uppercase;letter-spacing:-1px;margin-bottom:20px}
    .why p{color:var(--muted);margin-bottom:14px}
    .perks{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin-top:24px}.perks li{display:flex;gap:10px;align-items:center;font-weight:600;font-size:.92rem;color:var(--text)}.perks svg{width:18px;height:18px;color:var(--primary)}
    .timeline{position:relative;max-width:760px}.timeline::before{content:'';position:absolute;left:23px;top:10px;bottom:10px;width:1px;background:var(--border)}
    .tl-item{display:grid;grid-template-columns:auto 1fr;gap:26px;padding:18px 0;position:relative}
    .tl-dot{width:48px;height:48px;border-radius:50%;background:var(--surface);border:1px solid var(--border2);display:grid;place-items:center;font-family:'$font_heading';font-weight:800;color:var(--primary);z-index:1}
    .tl-item h4{font-family:'$font_heading';font-size:1.2rem;text-transform:uppercase}.tl-item p{color:var(--muted);margin-top:5px}
    .tgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}
    .mt{padding:34px;border:1px solid var(--border);background:var(--surface)}
    .mt blockquote{font-family:'$font_heading';font-size:1.15rem;line-height:1.45;margin-bottom:20px}
    .mt figcaption b{color:var(--primary)}.mt figcaption span{display:block;font-size:.84rem;color:var(--muted);margin-top:3px}
    .cta{position:relative;padding:110px 0;text-align:center;overflow:hidden}
    .cta-bg{position:absolute;inset:0;z-index:-1}.cta-bg img{width:100%;height:100%;object-fit:cover;filter:grayscale(.5)}
    .cta-bg::after{content:'';position:absolute;inset:0;background:rgba(var(--prgb),.10);backdrop-filter:blur(2px);box-shadow:inset 0 0 200px 60px var(--bg)}
    .cta-inner{position:relative;max-width:620px;margin:0 auto}
    .cta h2{font-family:'$font_heading';font-size:clamp(2.2rem,5vw,3.6rem);font-weight:800;text-transform:uppercase;letter-spacing:-1px}
    .cta p{color:var(--muted);margin:18px 0 32px}
    form{display:grid;gap:12px;max-width:520px;margin:0 auto;text-align:left}
    .ff input,.ff select{width:100%;padding:15px 18px;background:var(--surface);border:1px solid var(--border2);color:var(--text);font:inherit;font-size:.93rem}
    .ff input:focus,.ff select:focus{outline:none;border-color:var(--primary)}
    form button{padding:16px;background:var(--primary);color:var(--on-primary);border:none;font-family:'$font_heading';font-weight:700;text-transform:uppercase;letter-spacing:1px}
    .ff-note{font-size:.72rem;color:var(--muted);text-align:center}
    footer{padding:60px 0 28px;border-top:1px solid var(--border)}
    .foot{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}.foot-links{display:flex;gap:22px;color:var(--muted);font-size:.82rem;text-transform:uppercase;letter-spacing:1px}
    .copy{margin-top:28px;color:var(--muted);font-size:.78rem;text-align:center;border-top:1px solid var(--border);padding-top:22px}
    @media(max-width:920px){.navlink,.nav-cta{display:none}.burger{display:flex}.mstats{grid-template-columns:repeat(2,1fr)}.mstat{border-left:none;border-top:1px solid var(--border)}.why{grid-template-columns:1fr;gap:40px}.tgrid{grid-template-columns:1fr}.srow{grid-template-columns:auto 1fr}.sico{display:none}}
    """

    body = (
        '<header data-hdr><div class="wrap nav"><div class="logo">$logo_main<span> $logo_accent</span></div>'
        '<nav class="navlinks">' + _nav_links(d) + '<a class="nav-cta" href="#apply">Apply</a></nav>'
        '<button class="burger" data-menu-toggle aria-label="Menu"><span></span><span></span><span></span></button></div>'
        '<div class="mobnav" data-mobile-nav>' + _nav_links(d, "") + '<a href="#apply">Apply</a></div></header>'
        '<section class="hero"><div class="hero-bg"><img src="$hero_src" alt="$company"></div>'
        '<div class="wrap"><span class="hero-kick">$kicker</span><h1>$headline</h1><p>$subhead</p>'
        '<div class="hero-cta"><a class="btn btn-p" data-magnet href="#apply">Apply Now</a>'
        '<a class="btn btn-o" href="#services">See the Benefits</a></div></div></section>'
        '<section class="section"><div class="wrap mstats">' + stats + '</div></section>'
        '<section class="section alt" id="services"><div class="wrap"><div class="shead"><span class="klabel">The Benefits</span>'
        '<h2>What it means to drive here</h2></div>' + services + '</div></section>'
        '<section class="section" id="why"><div class="wrap why"><div data-rev><span class="klabel">Why $short</span>'
        '<h2>$about_title</h2><p>$about_p1</p><p>$about_p2</p><ul class="perks">' + perks + '</ul></div>'
        '<div class="why-img" data-rev><img src="$about_src" alt="$company"></div></div></section>'
        '<section class="section alt" id="process"><div class="wrap"><div class="shead"><span class="klabel">The Process</span>'
        '<h2>From application to first load</h2></div><div class="timeline">' + process + '</div></div></section>'
        '<section class="section" id="reviews"><div class="wrap"><div class="shead"><span class="klabel">Driver Voices</span>'
        '<h2>Straight from the cab</h2></div><div class="tgrid">' + testimonials + '</div></div></section>'
        '<section class="cta" id="apply"><div class="cta-bg"><img src="$coverage_src" alt=""></div>'
        '<div class="wrap cta-inner"><h2>$cta_title</h2><p>$cta_sub</p>' + _apply_form(d) + '</div></section>'
        '<footer><div class="wrap"><div class="foot"><div class="logo">$logo_main<span> $logo_accent</span></div>'
        '<div class="foot-links">' + _nav_links(d, "") + '</div></div>'
        '<div class="copy">© $year $company — $city_state. Equal Opportunity Employer. '
        'All qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</div></div></footer>'
    )
    return _assemble(d, _head(d, Template(css).safe_substitute(d)), Template(body).safe_substitute(d)), d


# ─────────────────────────────────────────────────────────────────────────────
# STUDIO 3 — EDITORIAL  (light · Swiss / magazine · serif display · hairlines)
# ─────────────────────────────────────────────────────────────────────────────

def studio_editorial(info):
    d = _build_data(info)
    d["pal"] = _make_palette("light")
    d.update(_pick_fonts(["serif"]))

    stats = "".join(
        '<div class="estat" data-rev><span class="ev" data-count="%s">%s</span><span class="el">%s</span></div>'
        % (v, v, l) for v, l in d["stats"])
    services = "".join(
        '<div class="eitem" data-rev><span class="enum">%02d</span><div><h3>%s</h3><p>%s</p></div>'
        '<div class="eico">%s</div></div>' % (i + 1, t, desc, _icon(ic))
        for i, (ic, t, desc) in enumerate(d["services"]))
    process = "".join(
        '<div class="estep" data-rev><span class="enum">%02d</span><h4>%s</h4><p>%s</p></div>'
        % (i + 1, t, desc) for i, (t, desc) in enumerate(d["process"]))
    testimonials = "".join(
        '<figure class="equote" data-rev><blockquote>“%s”</blockquote>'
        '<figcaption>— %s, <span>%s</span></figcaption></figure>' % (q, n, r)
        for q, n, r in d["testimonials"])
    perks = "".join('<li data-rev><span>·</span>%s</li>' % p for p in d["perks"])

    css = """
    body{background:var(--bg)}
    .btn{display:inline-block;padding:14px 30px;font-family:'$font_body';font-weight:600;font-size:.92rem;border:1px solid var(--text);transition:.25s}
    .btn-p{background:var(--text);color:var(--bg)}.btn-p:hover{background:var(--primary);border-color:var(--primary);color:var(--on-primary)}
    .btn-o{color:var(--text)}.btn-o:hover{background:var(--text);color:var(--bg)}
    header{position:fixed;top:0;width:100%;z-index:100;background:var(--bg);border-bottom:1px solid var(--text);transition:.3s}
    .nav{display:flex;align-items:center;justify-content:space-between;height:72px}
    .logo{font-family:'$font_heading';font-weight:700;font-size:1.5rem;letter-spacing:-.5px}.logo span{font-style:italic;color:var(--primary)}
    .navlink{font-size:.82rem;font-weight:600;letter-spacing:.5px;color:var(--text);margin-left:28px;position:relative}
    .navlink::after{content:'';position:absolute;left:0;bottom:-4px;width:0;height:1px;background:var(--text);transition:.25s}.navlink:hover::after{width:100%}
    .nav-cta{margin-left:28px;padding:9px 20px;background:var(--text);color:var(--bg);font-size:.8rem;font-weight:600}
    .burger{display:none;flex-direction:column;gap:5px;background:none;border:none}.burger span{width:26px;height:2px;background:var(--text);transition:.3s}
    .burger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}.burger.open span:nth-child(2){opacity:0}.burger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
    .mobnav{display:none;position:fixed;inset:0;z-index:99;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;gap:26px}.mobnav.open{display:flex}.mobnav a{font-family:'$font_heading';font-size:1.6rem}
    .hero{padding:140px 0 70px;border-bottom:1px solid var(--text)}
    .hero-top{display:grid;grid-template-columns:1.6fr 1fr;gap:50px;align-items:end;padding-bottom:46px}
    .hero-kick{font-size:.8rem;letter-spacing:3px;text-transform:uppercase;color:var(--primary);font-weight:700;display:block;margin-bottom:20px}
    .hero h1{font-family:'$font_heading';font-size:clamp(2.8rem,7vw,5.6rem);font-weight:700;line-height:1;letter-spacing:-2px;white-space:pre-line}
    .hero-meta{border-left:1px solid var(--text);padding-left:26px}
    .hero-meta p{color:var(--muted);font-size:1.02rem;margin-bottom:22px}
    .hero-cta{display:flex;gap:12px;flex-wrap:wrap}
    .hero-img{height:54vh;min-height:380px;overflow:hidden;border:1px solid var(--text)}
    .hero-img img{width:100%;height:100%;object-fit:cover;filter:grayscale(.15)}
    .estats{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--text)}
    .estat{padding:34px 24px;border-left:1px solid var(--border2);display:flex;flex-direction:column}.estat:first-child{border-left:none}
    .ev{font-family:'$font_heading';font-weight:700;font-size:2.2rem;letter-spacing:-1px}
    .el{font-size:.78rem;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-top:8px}
    .section{padding:100px 0;border-bottom:1px solid var(--text)}
    .shead{display:grid;grid-template-columns:auto 1fr;gap:30px;align-items:baseline;margin-bottom:56px}
    .shead .klabel{font-size:.78rem;letter-spacing:3px;text-transform:uppercase;color:var(--primary);font-weight:700}
    .shead h2{font-family:'$font_heading';font-size:clamp(2rem,4.4vw,3.3rem);font-weight:700;letter-spacing:-1px}
    .eitem{display:grid;grid-template-columns:auto 1fr auto;gap:30px;align-items:center;padding:32px 0;border-top:1px solid var(--border2)}.eitem:last-child{border-bottom:1px solid var(--border2)}
    .enum{font-family:'$font_heading';font-size:1.2rem;color:var(--primary);font-weight:700}
    .eitem h3{font-family:'$font_heading';font-size:1.5rem;font-weight:600;margin-bottom:4px}.eitem p{color:var(--muted);max-width:560px}
    .eico{width:46px;height:46px;color:var(--primary)}.eico svg{width:30px;height:30px}
    .why{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center}
    .why-img img{aspect-ratio:3/4;object-fit:cover;border:1px solid var(--text);filter:grayscale(.15)}
    .why h2{font-family:'$font_heading';font-size:clamp(1.9rem,4vw,2.9rem);font-weight:700;letter-spacing:-1px;margin-bottom:20px}
    .dropcap::first-letter{font-family:'$font_heading';float:left;font-size:3.6rem;line-height:.8;padding:6px 10px 0 0;color:var(--primary)}
    .why p{color:var(--muted);margin-bottom:14px}
    .perks{columns:2;margin-top:22px}.perks li{display:flex;gap:10px;font-size:.94rem;font-weight:500;margin-bottom:9px;break-inside:avoid}.perks span{color:var(--primary);font-weight:700}
    .esteps{display:grid;grid-template-columns:repeat(4,1fr);gap:0}
    .estep{padding:0 26px;border-left:1px solid var(--border2)}.estep:first-child{padding-left:0;border-left:none}
    .estep .enum{font-size:2rem;display:block;margin-bottom:12px}.estep h4{font-family:'$font_heading';font-size:1.2rem;margin-bottom:8px}.estep p{color:var(--muted);font-size:.92rem}
    .equotes{display:grid;grid-template-columns:repeat(3,1fr);gap:0}
    .equote{padding:0 30px;border-left:1px solid var(--border2)}.equote:first-child{padding-left:0;border-left:none}
    .equote blockquote{font-family:'$font_heading';font-size:1.3rem;font-style:italic;line-height:1.4;margin-bottom:18px}
    .equote figcaption{font-size:.9rem;font-weight:600}.equote figcaption span{color:var(--muted);font-weight:400}
    .cta{display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:center}
    .cta h2{font-family:'$font_heading';font-size:clamp(2rem,4.4vw,3.2rem);font-weight:700;letter-spacing:-1px}.cta p{color:var(--muted);margin-top:16px}
    form{display:grid;gap:12px}
    .ff input,.ff select{width:100%;padding:14px 16px;border:1px solid var(--text);background:var(--surface);font:inherit;font-size:.93rem;color:var(--text)}
    .ff input:focus,.ff select:focus{outline:none;border-color:var(--primary)}
    form button{padding:15px;background:var(--text);color:var(--bg);border:none;font-family:'$font_body';font-weight:600}
    .ff-note{font-size:.72rem;color:var(--muted)}
    footer{padding:54px 0 28px}
    .foot{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}.foot .logo{font-size:1.3rem}.foot-links{display:flex;gap:22px;font-size:.85rem;font-weight:600}
    .copy{margin-top:30px;color:var(--muted);font-size:.78rem;border-top:1px solid var(--border2);padding-top:22px}
    @media(max-width:920px){.navlink,.nav-cta{display:none}.burger{display:flex}.hero-top{grid-template-columns:1fr;gap:30px}.hero-meta{border-left:none;padding-left:0}.estats,.esteps{grid-template-columns:repeat(2,1fr)}.estat{border-left:none}.estat:nth-child(odd){border-right:1px solid var(--border2)}.eitem{grid-template-columns:auto 1fr}.eico{display:none}.why,.cta{grid-template-columns:1fr;gap:36px}.equotes{grid-template-columns:1fr;gap:30px}.equote{padding-left:0;border-left:none;border-top:1px solid var(--border2);padding-top:24px}}
    """

    body = (
        '<header data-hdr><div class="wrap nav"><div class="logo">$logo_main<span> $logo_accent</span></div>'
        '<nav>' + _nav_links(d) + '<a class="nav-cta" href="#apply">Apply</a></nav>'
        '<button class="burger" data-menu-toggle aria-label="Menu"><span></span><span></span><span></span></button></div>'
        '<div class="mobnav" data-mobile-nav>' + _nav_links(d, "") + '<a href="#apply">Apply</a></div></header>'
        '<section class="hero"><div class="wrap"><div class="hero-top"><div><span class="hero-kick">$kicker</span><h1>$headline</h1></div>'
        '<div class="hero-meta"><p>$subhead</p><div class="hero-cta"><a class="btn btn-p" href="#apply">Apply Today</a>'
        '<a class="btn btn-o" href="#why">Read More</a></div></div></div>'
        '<div class="hero-img" data-rev><img src="$hero_src" alt="$company"></div></div></section>'
        '<section><div class="wrap"><div class="estats">' + stats + '</div></div></section>'
        '<section class="section" id="services"><div class="wrap"><div class="shead"><span class="klabel">Benefits</span>'
        '<h2>The case for driving with $short</h2></div>' + services + '</div></section>'
        '<section class="section" id="why"><div class="wrap why"><div class="why-img" data-rev><img src="$about_src" alt="$company"></div>'
        '<div data-rev><span class="klabel">About</span><h2>$about_title</h2><p class="dropcap">$about_p1</p><p>$about_p2</p>'
        '<ul class="perks">' + perks + '</ul></div></div></section>'
        '<section class="section" id="process"><div class="wrap"><div class="shead"><span class="klabel">Process</span>'
        '<h2>Four steps to the seat</h2></div><div class="esteps">' + process + '</div></div></section>'
        '<section class="section" id="reviews"><div class="wrap"><div class="shead"><span class="klabel">Testimony</span>'
        '<h2>In their words</h2></div><div class="equotes">' + testimonials + '</div></div></section>'
        '<section class="section" id="apply"><div class="wrap cta"><div><span class="klabel">Apply</span><h2>$cta_title</h2><p>$cta_sub</p></div>'
        + _apply_form(d) + '</div></section>'
        '<footer><div class="wrap"><div class="foot"><div class="logo">$logo_main<span> $logo_accent</span></div>'
        '<div class="foot-links">' + _nav_links(d, "") + '</div></div>'
        '<div class="copy">© $year $company · $city_state · Equal Opportunity Employer. '
        'All qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</div></div></footer>'
    )
    return _assemble(d, _head(d, Template(css).safe_substitute(d)), Template(body).safe_substitute(d)), d


# ─────────────────────────────────────────────────────────────────────────────
# STUDIO 4 — VANGUARD  (bold typography · brutalist-modern · hard shadows)
# ─────────────────────────────────────────────────────────────────────────────

def studio_vanguard(info):
    d = _build_data(info)
    d["pal"] = _make_palette(random.choice(["light", "light", "dark"]))
    d.update(_pick_fonts(["display", "grotesk"]))

    stats = "".join(
        '<div class="vbox" data-rev><div class="vv" data-count="%s">%s</div><div class="vl">%s</div></div>'
        % (v, v, l) for v, l in d["stats"])
    services = "".join(
        '<article class="vcard" data-rev><div class="vico">%s</div><h3>%s</h3><p>%s</p></article>'
        % (_icon(ic), t, desc) for ic, t, desc in d["services"])
    process = "".join(
        '<div class="vstep" data-rev><span class="vsnum">%02d</span><div><h4>%s</h4><p>%s</p></div></div>'
        % (i + 1, t, desc) for i, (t, desc) in enumerate(d["process"]))
    testimonials = "".join(
        '<figure class="vt" data-rev><blockquote>“%s”</blockquote>'
        '<figcaption><b>%s</b> / %s</figcaption></figure>' % (q, n, r)
        for q, n, r in d["testimonials"])
    perks = "".join('<li data-rev>%s</li>' % p for p in d["perks"])

    css = """
    body{background:var(--bg)}
    .btn{display:inline-block;padding:16px 32px;font-family:'$font_heading';font-weight:800;font-size:.95rem;text-transform:uppercase;letter-spacing:.5px;border:3px solid var(--text);transition:.18s;box-shadow:6px 6px 0 var(--text)}
    .btn:hover{transform:translate(-3px,-3px);box-shadow:9px 9px 0 var(--text)}
    .btn-p{background:var(--primary);color:var(--on-primary)}.btn-d{background:var(--text);color:var(--bg)}.btn-w{background:var(--surface);color:var(--text)}
    header{position:fixed;top:0;width:100%;z-index:100;background:var(--bg);border-bottom:3px solid var(--text);transition:.3s}
    .nav{display:flex;align-items:center;justify-content:space-between;height:74px}
    .logo{font-family:'$font_heading';font-weight:900;font-size:1.5rem;text-transform:uppercase;letter-spacing:-1px;background:var(--primary);color:var(--on-primary);padding:6px 12px;box-shadow:4px 4px 0 var(--text)}
    .navlink{font-family:'$font_heading';font-size:.82rem;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-left:26px}.navlink:hover{color:var(--primary)}
    .nav-cta{margin-left:26px;padding:10px 20px;background:var(--text);color:var(--bg);font-family:'$font_heading';font-weight:800;text-transform:uppercase;font-size:.8rem;box-shadow:3px 3px 0 var(--primary)}
    .burger{display:none;flex-direction:column;gap:5px;background:none;border:none}.burger span{width:28px;height:3px;background:var(--text)}
    .burger.open span:nth-child(1){transform:rotate(45deg) translate(6px,6px)}.burger.open span:nth-child(2){opacity:0}.burger.open span:nth-child(3){transform:rotate(-45deg) translate(6px,-6px)}
    .mobnav{display:none;position:fixed;inset:0;z-index:99;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;gap:26px}.mobnav.open{display:flex}.mobnav a{font-family:'$font_heading';font-size:1.7rem;font-weight:900;text-transform:uppercase}
    .hero{padding:150px 0 90px;position:relative;overflow:hidden}
    .hero::before{content:'';position:absolute;top:90px;right:-80px;width:360px;height:360px;background:var(--primary);transform:rotate(15deg);z-index:0;opacity:.5}
    .hero-grid{position:relative;z-index:1;display:grid;grid-template-columns:1.2fr .8fr;gap:50px;align-items:center}
    .hero-kick{display:inline-block;font-family:'$font_heading';font-weight:800;font-size:.82rem;letter-spacing:2px;text-transform:uppercase;background:var(--text);color:var(--bg);padding:7px 14px;margin-bottom:24px}
    .hero h1{font-family:'$font_heading';font-size:clamp(3rem,8.5vw,6.5rem);font-weight:900;line-height:.92;letter-spacing:-3px;text-transform:uppercase;white-space:pre-line}
    .hero h1 em{font-style:normal;color:var(--primary);-webkit-text-stroke:2px var(--text)}
    .hero p{font-size:1.15rem;max-width:500px;margin:26px 0 34px;font-weight:500}
    .hero-cta{display:flex;gap:16px;flex-wrap:wrap}
    .hero-img{border:3px solid var(--text);box-shadow:12px 12px 0 var(--primary)}.hero-img img{aspect-ratio:4/5;object-fit:cover}
    .section{padding:100px 0;border-top:3px solid var(--text)}
    .shead{margin-bottom:54px;max-width:720px}
    .klabel{display:inline-block;font-family:'$font_heading';font-weight:800;font-size:.78rem;letter-spacing:2px;text-transform:uppercase;background:var(--primary);color:var(--on-primary);padding:5px 12px}
    .shead h2{font-family:'$font_heading';font-size:clamp(2.2rem,6vw,4rem);font-weight:900;text-transform:uppercase;letter-spacing:-2px;margin-top:16px}
    .vstats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
    .vbox{border:3px solid var(--text);background:var(--surface);padding:30px 22px;box-shadow:7px 7px 0 var(--text);transition:.2s}
    .vbox:hover{transform:translate(-3px,-3px);box-shadow:10px 10px 0 var(--primary)}
    .vbox:nth-child(2){background:var(--primary);color:var(--on-primary)}
    .vv{font-family:'$font_heading';font-weight:900;font-size:2.2rem;letter-spacing:-1px}.vl{font-family:'$font_heading';font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:1px;margin-top:6px}
    .vcards{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
    .vcard{border:3px solid var(--text);background:var(--surface);padding:30px;box-shadow:7px 7px 0 var(--text);transition:.2s}
    .vcard:hover{transform:translate(-4px,-4px);box-shadow:11px 11px 0 var(--primary)}
    .vico{width:54px;height:54px;border:3px solid var(--text);background:var(--primary);color:var(--on-primary);display:grid;place-items:center;margin-bottom:18px}.vico svg{width:26px;height:26px}
    .vcard h3{font-family:'$font_heading';font-size:1.3rem;font-weight:800;text-transform:uppercase;margin-bottom:8px}.vcard p{color:var(--muted);font-size:.94rem}
    .why{display:grid;grid-template-columns:1fr 1fr;gap:50px;align-items:center}
    .why-img{border:3px solid var(--text);box-shadow:12px 12px 0 var(--primary)}.why-img img{aspect-ratio:1/1;object-fit:cover}
    .why h2{font-family:'$font_heading';font-size:clamp(2rem,5vw,3.4rem);font-weight:900;text-transform:uppercase;letter-spacing:-2px;margin-bottom:20px}.why p{margin-bottom:14px;font-weight:500}
    .perks{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}
    .perks li{border:3px solid var(--text);padding:12px 14px;font-family:'$font_heading';font-weight:700;font-size:.86rem;text-transform:uppercase;background:var(--surface);box-shadow:4px 4px 0 var(--text)}
    .vsteps{display:grid;grid-template-columns:repeat(2,1fr);gap:22px}
    .vstep{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:center;border:3px solid var(--text);padding:26px;background:var(--surface);box-shadow:7px 7px 0 var(--text)}
    .vsnum{font-family:'$font_heading';font-weight:900;font-size:2.6rem;color:var(--primary);-webkit-text-stroke:2px var(--text)}
    .vstep h4{font-family:'$font_heading';font-size:1.2rem;font-weight:800;text-transform:uppercase}.vstep p{color:var(--muted);font-size:.92rem;margin-top:4px}
    .vts{display:grid;grid-template-columns:repeat(3,1fr);gap:22px}
    .vt{border:3px solid var(--text);padding:28px;background:var(--surface);box-shadow:7px 7px 0 var(--text)}
    .vt blockquote{font-family:'$font_heading';font-size:1.12rem;font-weight:700;line-height:1.35;margin-bottom:16px}
    .vt figcaption{font-size:.86rem;font-weight:600;text-transform:uppercase}.vt figcaption b{color:var(--primary)}
    .cta{border:3px solid var(--text);background:var(--primary);color:var(--on-primary);box-shadow:14px 14px 0 var(--text);padding:60px;display:grid;grid-template-columns:1fr 1fr;gap:46px;align-items:center}
    .cta h2{font-family:'$font_heading';font-size:clamp(2.2rem,5vw,3.6rem);font-weight:900;text-transform:uppercase;letter-spacing:-2px}.cta p{margin-top:14px;font-weight:500}
    form{display:grid;gap:12px;background:var(--bg);padding:26px;border:3px solid var(--text)}
    .ff input,.ff select{width:100%;padding:14px 16px;border:3px solid var(--text);background:var(--surface);font:inherit;font-size:.93rem;color:var(--text);font-weight:600}
    .ff input:focus,.ff select:focus{outline:none;border-color:var(--primary)}
    form button{padding:16px;background:var(--text);color:var(--bg);border:none;font-family:'$font_heading';font-weight:800;text-transform:uppercase;letter-spacing:1px;box-shadow:5px 5px 0 var(--primary)}
    .ff-note{font-size:.72rem;color:var(--muted)}
    footer{padding:56px 0 28px;border-top:3px solid var(--text)}
    .foot{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}.foot-links{display:flex;gap:20px;font-family:'$font_heading';font-weight:700;text-transform:uppercase;font-size:.82rem}
    .copy{margin-top:28px;color:var(--muted);font-size:.78rem;border-top:3px solid var(--text);padding-top:22px}
    @media(max-width:920px){.navlink,.nav-cta{display:none}.burger{display:flex}.hero-grid,.why,.cta{grid-template-columns:1fr;gap:38px}.vstats,.vcards,.vts{grid-template-columns:1fr}.vsteps{grid-template-columns:1fr}.cta{padding:36px 24px}}
    """

    body = (
        '<header data-hdr><div class="wrap nav"><div class="logo">$short</div>'
        '<nav>' + _nav_links(d) + '<a class="nav-cta" href="#apply">Apply</a></nav>'
        '<button class="burger" data-menu-toggle aria-label="Menu"><span></span><span></span><span></span></button></div>'
        '<div class="mobnav" data-mobile-nav>' + _nav_links(d, "") + '<a href="#apply">Apply</a></div></header>'
        '<section class="hero"><div class="wrap hero-grid"><div><span class="hero-kick">$kicker</span>'
        '<h1>$headline</h1><p>$subhead</p><div class="hero-cta"><a class="btn btn-d" data-magnet href="#apply">Apply Now</a>'
        '<a class="btn btn-w" href="#services">The Perks</a></div></div>'
        '<div class="hero-img" data-rev><img src="$hero_src" alt="$company"></div></div></section>'
        '<section class="section"><div class="wrap vstats">' + stats + '</div></section>'
        '<section class="section" id="services"><div class="wrap"><div class="shead"><span class="klabel">The Perks</span>'
        '<h2>No fluff. Just the good stuff.</h2></div><div class="vcards">' + services + '</div></div></section>'
        '<section class="section" id="why"><div class="wrap why"><div class="why-img" data-rev><img src="$about_src" alt="$company"></div>'
        '<div data-rev><span class="klabel">Why $short</span><h2>$about_title</h2><p>$about_p1</p><p>$about_p2</p>'
        '<ul class="perks">' + perks + '</ul></div></div></section>'
        '<section class="section" id="process"><div class="wrap"><div class="shead"><span class="klabel">Process</span>'
        '<h2>Get hired fast</h2></div><div class="vsteps">' + process + '</div></div></section>'
        '<section class="section" id="reviews"><div class="wrap"><div class="shead"><span class="klabel">Reviews</span>'
        '<h2>Drivers don’t lie</h2></div><div class="vts">' + testimonials + '</div></div></section>'
        '<section class="section" id="apply"><div class="wrap"><div class="cta"><div><h2>$cta_title</h2><p>$cta_sub</p></div>'
        + _apply_form(d) + '</div></div></section>'
        '<footer><div class="wrap"><div class="foot"><div class="logo">$short</div>'
        '<div class="foot-links">' + _nav_links(d, "") + '</div></div>'
        '<div class="copy">© $year $company — $city_state. Equal Opportunity Employer. '
        'All qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</div></div></footer>'
    )
    return _assemble(d, _head(d, Template(css).safe_substitute(d)), Template(body).safe_substitute(d)), d


# ─────────────────────────────────────────────────────────────────────────────
# STUDIO 5 — NOCTURNE  (dark · high-tech dashboard · neon glow · mono labels)
# ─────────────────────────────────────────────────────────────────────────────

def studio_nocturne(info):
    d = _build_data(info)
    d["pal"] = _make_palette("dark")
    d.update(_pick_fonts(["grotesk"]))

    stats = "".join(
        '<div class="tile" data-rev><div class="tlabel">%s</div><div class="tval" data-count="%s">%s</div>'
        '<div class="tbar"><i></i></div></div>' % (l, v, v) for v, l in d["stats"])
    services = "".join(
        '<article class="ncard" data-rev><div class="nico">%s</div><h3>%s</h3><p>%s</p>'
        '<span class="ncorner"></span></article>' % (_icon(ic), t, desc)
        for ic, t, desc in d["services"])
    process = "".join(
        '<div class="nstep" data-rev><div class="ndot">%02d</div><h4>%s</h4><p>%s</p></div>'
        % (i + 1, t, desc) for i, (t, desc) in enumerate(d["process"]))
    testimonials = "".join(
        '<figure class="nt" data-rev><div class="stars">★★★★★</div>'
        '<blockquote>“%s”</blockquote><figcaption><b>%s</b><span>%s</span></figcaption></figure>'
        % (q, n, r) for q, n, r in d["testimonials"])
    perks = "".join('<li data-rev>%s%s</li>' % (_icon("check"), p) for p in d["perks"])

    css = """
    body{background:var(--bg);background-image:linear-gradient(rgba(var(--prgb),.05) 1px,transparent 1px),linear-gradient(90deg,rgba(var(--prgb),.05) 1px,transparent 1px);background-size:48px 48px}
    .btn{display:inline-flex;align-items:center;gap:9px;padding:15px 30px;border-radius:10px;font-family:'$font_heading';font-weight:700;font-size:.92rem;border:1px solid transparent;transition:.25s}
    .btn-p{background:var(--primary);color:var(--on-primary);box-shadow:0 0 0 1px rgba(var(--prgb),.4),0 0 30px -4px rgba(var(--prgb),.7)}
    .btn-p:hover{box-shadow:0 0 0 1px rgba(var(--prgb),.6),0 0 44px 0 rgba(var(--prgb),.85);transform:translateY(-2px)}
    .btn-o{border-color:var(--border2);color:var(--text);background:rgba(var(--prgb),.04)}.btn-o:hover{border-color:var(--primary);color:var(--primary)}
    header{position:fixed;top:0;width:100%;z-index:100;transition:.3s;border-bottom:1px solid transparent}
    header.scrolled{background:rgba(var(--prgb),.05);backdrop-filter:blur(16px);border-bottom-color:var(--border)}
    .nav{display:flex;align-items:center;justify-content:space-between;height:74px}
    .logo{font-family:'$font_heading';font-weight:800;font-size:1.3rem;letter-spacing:-.5px}.logo span{color:var(--primary)}
    .navlink{font-family:$font_mono;font-size:.78rem;letter-spacing:.5px;color:var(--muted);margin-left:28px;transition:.2s}.navlink:hover{color:var(--primary)}
    .nav-cta{margin-left:28px;padding:10px 22px;border-radius:9px;background:var(--primary);color:var(--on-primary);font-weight:700;font-size:.85rem;box-shadow:0 0 24px -6px rgba(var(--prgb),.8)}
    .burger{display:none;flex-direction:column;gap:5px;background:none;border:none}.burger span{width:25px;height:2px;background:var(--text);transition:.3s}
    .burger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}.burger.open span:nth-child(2){opacity:0}.burger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
    .mobnav{display:none;position:fixed;inset:0;z-index:99;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;gap:26px}.mobnav.open{display:flex}.mobnav a{font-family:'$font_heading';font-size:1.4rem;font-weight:700}
    .hero{position:relative;padding:180px 0 110px;overflow:hidden}
    .glow{position:absolute;top:-10%;left:50%;transform:translateX(-50%);width:680px;height:680px;background:radial-gradient(circle,rgba(var(--prgb),.32),transparent 60%);filter:blur(40px);z-index:-1}
    .hero-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:54px;align-items:center}
    .chip{display:inline-flex;align-items:center;gap:9px;font-family:$font_mono;font-size:.76rem;color:var(--primary);border:1px solid var(--border2);background:rgba(var(--prgb),.06);padding:7px 14px;border-radius:999px;margin-bottom:24px}
    .chip .led{width:7px;height:7px;border-radius:50%;background:var(--primary);box-shadow:0 0 10px 1px var(--primary);animation:pl 1.6s infinite}@keyframes pl{50%{opacity:.35}}
    .hero h1{font-size:clamp(2.6rem,5.8vw,4.4rem);font-weight:800;letter-spacing:-2px;white-space:pre-line}
    .hero h1 em{font-style:normal;color:var(--primary);text-shadow:0 0 30px rgba(var(--prgb),.6)}
    .hero p{color:var(--muted);font-size:1.1rem;max-width:500px;margin:22px 0 34px}
    .hero-cta{display:flex;gap:14px;flex-wrap:wrap}
    .hero-panel{border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:14px;box-shadow:var(--shadow)}
    .hero-panel img{border-radius:12px;aspect-ratio:5/4;object-fit:cover;width:100%}
    .hpbar{display:flex;gap:6px;padding:8px 6px 12px}.hpbar i{width:10px;height:10px;border-radius:50%;background:var(--border2)}.hpbar i:first-child{background:var(--primary)}
    .section{padding:104px 0}
    .shead{text-align:center;max-width:640px;margin:0 auto 58px}
    .klabel{font-family:$font_mono;font-size:.76rem;letter-spacing:2px;text-transform:uppercase;color:var(--primary)}
    .shead h2{font-size:clamp(2rem,4vw,3rem);font-weight:800;letter-spacing:-1px;margin:14px 0}
    .shead p{color:var(--muted)}
    .tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
    .tile{border:1px solid var(--border);border-radius:16px;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:26px;position:relative;overflow:hidden}
    .tile::after{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--primary),transparent);opacity:.6}
    .tlabel{font-family:$font_mono;font-size:.72rem;letter-spacing:1px;text-transform:uppercase;color:var(--muted)}
    .tval{font-family:'$font_heading';font-weight:800;font-size:2rem;color:var(--text);margin:10px 0 14px;letter-spacing:-1px}
    .tbar{height:5px;border-radius:3px;background:var(--border)}.tbar i{display:block;height:100%;width:78%;border-radius:3px;background:linear-gradient(90deg,var(--primary),var(--primary2));box-shadow:0 0 12px 0 rgba(var(--prgb),.7)}
    .ncards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
    .ncard{position:relative;border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:30px;transition:.3s;overflow:hidden}
    .ncard:hover{border-color:var(--primary);box-shadow:0 0 40px -10px rgba(var(--prgb),.5)}
    .nico{width:52px;height:52px;border-radius:13px;display:grid;place-items:center;background:rgba(var(--prgb),.1);color:var(--primary);margin-bottom:18px;border:1px solid var(--border2)}.nico svg{width:25px;height:25px}
    .ncard h3{font-size:1.16rem;font-weight:700;margin-bottom:8px}.ncard p{color:var(--muted);font-size:.94rem}
    .ncorner{position:absolute;top:0;right:0;width:46px;height:46px;background:linear-gradient(225deg,rgba(var(--prgb),.25),transparent 70%)}
    .why{display:grid;grid-template-columns:1fr 1fr;gap:54px;align-items:center}
    .why-img{border:1px solid var(--border);border-radius:18px;overflow:hidden;box-shadow:var(--shadow);position:relative}.why-img img{aspect-ratio:1/1;object-fit:cover}
    .why-img::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,transparent 60%,rgba(var(--prgb),.18))}
    .why h2{font-size:clamp(1.9rem,3.6vw,2.7rem);font-weight:800;letter-spacing:-1px;margin-bottom:18px}.why p{color:var(--muted);margin-bottom:14px}
    .perks{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}.perks li{display:flex;gap:10px;align-items:center;font-weight:600;font-size:.92rem}.perks svg{width:18px;height:18px;color:var(--primary)}
    .nsteps{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}
    .nstep{border:1px solid var(--border);border-radius:16px;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:28px 22px}
    .ndot{width:46px;height:46px;border-radius:12px;display:grid;place-items:center;font-family:'$font_heading';font-weight:800;color:var(--primary);background:rgba(var(--prgb),.1);border:1px solid var(--border2);margin-bottom:14px}
    .nstep h4{font-size:1.08rem;margin-bottom:7px}.nstep p{color:var(--muted);font-size:.9rem}
    .ntg{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
    .nt{border:1px solid var(--border);border-radius:18px;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:30px}
    .stars{color:var(--primary);letter-spacing:2px;margin-bottom:14px;text-shadow:0 0 12px rgba(var(--prgb),.5)}
    .nt blockquote{font-size:1rem;line-height:1.6;margin-bottom:18px}.nt figcaption b{color:var(--text)}.nt figcaption span{display:block;font-size:.83rem;color:var(--muted);margin-top:3px}
    .cta{position:relative;border:1px solid var(--border2);border-radius:28px;overflow:hidden;background:linear-gradient(180deg,var(--surface),var(--bg2));padding:64px;display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:center}
    .cta::before{content:'';position:absolute;top:-40%;left:50%;transform:translateX(-50%);width:600px;height:400px;background:radial-gradient(circle,rgba(var(--prgb),.25),transparent 60%);filter:blur(30px)}
    .cta>*{position:relative}.cta h2{font-size:clamp(1.9rem,3.6vw,2.8rem);font-weight:800;letter-spacing:-1px}.cta p{color:var(--muted);margin-top:14px}
    form{display:grid;gap:12px}
    .ff input,.ff select{width:100%;padding:14px 16px;border-radius:11px;border:1px solid var(--border2);background:var(--bg);color:var(--text);font:inherit;font-size:.92rem}
    .ff input:focus,.ff select:focus{outline:none;border-color:var(--primary);box-shadow:0 0 0 3px rgba(var(--prgb),.18)}
    form button{padding:15px;border-radius:11px;border:none;background:var(--primary);color:var(--on-primary);font-family:'$font_heading';font-weight:700;box-shadow:0 0 26px -6px rgba(var(--prgb),.8)}
    .ff-note{font-size:.72rem;color:var(--muted);text-align:center}
    footer{padding:60px 0 28px;border-top:1px solid var(--border)}
    .foot{display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}.foot-links{display:flex;gap:22px;color:var(--muted);font-family:$font_mono;font-size:.8rem}
    .copy{margin-top:28px;color:var(--muted);font-size:.78rem;text-align:center;border-top:1px solid var(--border);padding-top:22px}
    @media(max-width:920px){.navlink,.nav-cta{display:none}.burger{display:flex}.hero-grid,.why,.cta{grid-template-columns:1fr;gap:40px}.tiles,.nsteps{grid-template-columns:repeat(2,1fr)}.ncards,.ntg{grid-template-columns:1fr}.cta{padding:40px 24px}}
    @media(max-width:560px){.tiles,.nsteps,.perks{grid-template-columns:1fr}}
    """
    d["font_mono"] = _MONO

    body = (
        '<header data-hdr><div class="wrap nav"><div class="logo">$logo_main<span>$logo_accent</span></div>'
        '<nav>' + _nav_links(d) + '<a class="nav-cta" href="#apply">Apply Now</a></nav>'
        '<button class="burger" data-menu-toggle aria-label="Menu"><span></span><span></span><span></span></button></div>'
        '<div class="mobnav" data-mobile-nav>' + _nav_links(d, "") + '<a href="#apply">Apply Now</a></div></header>'
        '<section class="hero"><div class="glow"></div><div class="wrap hero-grid"><div>'
        '<span class="chip"><span class="led"></span>$kicker · $city_state</span>'
        '<h1>$headline</h1><p>$subhead</p><div class="hero-cta"><a class="btn btn-p" data-magnet href="#apply">Start Application</a>'
        '<a class="btn btn-o" href="#services">Explore Benefits</a></div></div>'
        '<div class="hero-panel" data-rev><div class="hpbar"><i></i><i></i><i></i></div><img src="$hero_src" alt="$company"></div></div></section>'
        '<section class="section"><div class="wrap"><div class="tiles">' + stats + '</div></div></section>'
        '<section class="section" id="services"><div class="wrap"><div class="shead"><span class="klabel">// benefits</span>'
        '<h2>Engineered for drivers</h2><p>Every system tuned to keep you moving and earning.</p></div>'
        '<div class="ncards">' + services + '</div></div></section>'
        '<section class="section" id="why"><div class="wrap why"><div class="why-img" data-rev><img src="$about_src" alt="$company"></div>'
        '<div data-rev><span class="klabel">// about</span><h2>$about_title</h2><p>$about_p1</p><p>$about_p2</p>'
        '<ul class="perks">' + perks + '</ul></div></div></section>'
        '<section class="section" id="process"><div class="wrap"><div class="shead"><span class="klabel">// process</span>'
        '<h2>Four steps to launch</h2></div><div class="nsteps">' + process + '</div></div></section>'
        '<section class="section" id="reviews"><div class="wrap"><div class="shead"><span class="klabel">// reviews</span>'
        '<h2>Signal from the fleet</h2></div><div class="ntg">' + testimonials + '</div></div></section>'
        '<section class="section" id="apply"><div class="wrap"><div class="cta"><div><span class="klabel">// apply</span>'
        '<h2>$cta_title</h2><p>$cta_sub</p></div>' + _apply_form(d) + '</div></div></section>'
        '<footer><div class="wrap"><div class="foot"><div class="logo">$logo_main<span>$logo_accent</span></div>'
        '<div class="foot-links">' + _nav_links(d, "") + '</div></div>'
        '<div class="copy">© $year $company · $city_state · Equal Opportunity Employer. '
        'All qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</div></div></footer>'
    )
    return _assemble(d, _head(d, Template(css).safe_substitute(d)), Template(body).safe_substitute(d)), d


# ─────────────────────────────────────────────────────────────────────────────
# Registry + public entry point
# ─────────────────────────────────────────────────────────────────────────────

STUDIOS = [
    studio_aurora,
    studio_monolith,
    studio_editorial,
    studio_vanguard,
    studio_nocturne,
]


def render_site(info, studio=None):
    """Render a complete premium single-file site.

    Returns (html, ctx). ctx contains hero_img/about_img/about_img2/coverage_img
    filenames so the caller can copy them into the zip's images/ directory.
    """
    fn = studio or random.choice(STUDIOS)
    if isinstance(fn, str):
        fn = {f.__name__: f for f in STUDIOS}.get(fn, random.choice(STUDIOS))
    return fn(info)
