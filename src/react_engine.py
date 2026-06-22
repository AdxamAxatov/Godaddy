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
import random

from studio_engine import _build_data, _company_data, _ICON_PATHS
from website_generator import _company_data_script


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


# brand hue + harmony per studio (intentional mood; never random rainbow)
_SEEDS = {
    "press":  [(14, "analogous", 2, 0.05, "light"), (350, "analogous", 2, 0.05, "light")],   # terracotta / oxblood, warm
    "lumen":  [(150, "split", 6, 0.03, "light"), (200, "analogous", 6, 0.03, "light")],       # green+gold / teal, calm
    "apex":   [(24, "monochrome", 4, 0.05, "dark"), (214, "analogous", 4, 0.05, "dark")],     # copper / steel, automotive
    "nebula": [(222, "triadic", 12, 0.05, "dark"), (250, "split", 12, 0.05, "dark")],         # electric blue / violet
    "atlas":  [(226, "split", 12, 0.0, "light"), (178, "triadic", 12, 0.0, "light")],         # indigo+green / teal, SaaS
    "forge":  [(32, "analogous", 2, 0.06, "dark"), (18, "analogous", 2, 0.05, "light")],      # amber / rust, industrial
}
THEMES = {k: [_theory_theme(*s) for s in v] for k, v in _SEEDS.items()}


# studio presets — each a distinct art direction
PRESETS = [
    {"id": "press", "label": "editorial magazine", "fonts": "serif",
     "v": {"nav": "rule", "hero": "editorial", "stats": "ledger", "services": "list",
           "process": "numbered", "showcase": "frame", "testimonials": "pull"},
     "order": ["stats", "about", "services", "showcase", "process", "testimonials"]},
    {"id": "lumen", "label": "luxury minimal", "fonts": "serif",
     "v": {"nav": "solid", "hero": "split", "stats": "ledger", "services": "accordion",
           "process": "timeline", "showcase": "marquee", "testimonials": "pull"},
     "order": ["about", "stats", "services", "showcase", "process", "testimonials"]},
    {"id": "apex", "label": "automotive premium", "fonts": "display",
     "v": {"nav": "solid", "hero": "cinematic", "stats": "strip", "services": "list",
           "process": "timeline", "showcase": "grid", "testimonials": "pull"},
     "order": ["stats", "showcase", "services", "about", "process", "testimonials"]},
    {"id": "nebula", "label": "futuristic enterprise", "fonts": "grotesk",
     "v": {"nav": "floating", "hero": "centered", "stats": "strip", "services": "accordion",
           "process": "timeline", "showcase": "grid", "testimonials": "cards"},
     "order": ["stats", "services", "showcase", "about", "process", "testimonials"]},
    {"id": "atlas", "label": "modern SaaS", "fonts": "grotesk",
     "v": {"nav": "floating", "hero": "centered", "stats": "strip", "services": "list",
           "process": "numbered", "showcase": "grid", "testimonials": "cards"},
     "order": ["stats", "services", "about", "showcase", "process", "testimonials"]},
    {"id": "forge", "label": "dark industrial", "fonts": "display",
     "v": {"nav": "rule", "hero": "editorial", "stats": "ledger", "services": "list",
           "process": "numbered", "showcase": "frame", "testimonials": "cards"},
     "order": ["stats", "services", "showcase", "about", "process", "testimonials"]},
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


def _build_payload(info):
    d = _build_data(info)
    preset = random.choice(PRESETS)
    theme = dict(random.choice(THEMES[preset["id"]]))
    fh, fb = random.choice(_FONTS[preset["fonts"]])
    sf = random.choice(_SCRIPTS)
    hero_mix = random.choice(_HERO_MIX)

    imgs = [d["hero_src"], d["about_src"], d["coverage_src"], d["about2_src"]]
    showcase = [{"img": imgs[i], "title": _SHOWCASE[i][0], "sub": _SHOWCASE[i][1]} for i in range(4)]
    mono = "".join(w[0] for w in d["short"].split()[:2]).upper() or d["short"][:2].upper()

    data = {
        "company": d["company"], "short": d["short"], "logoMain": d["logo_main"],
        "logoAccent": d["logo_accent"], "monogram": mono, "domain": d["domain"],
        "email": d["email"], "cityState": d["city_state"], "city": d["city"],
        "state": d["state"], "year": d["year"], "jobTitle": d["job_title"],
        "pay": d["pay_range"], "homeTime": d["home_time"], "homeShort": d["home_time_short"],
        "minExp": d["min_experience"], "routes": d["routes"], "routesType": d["routes_type"],
        "headline": d["headline"], "subhead": d["subhead"], "kicker": d["kicker"],
        "aboutTitle": d["about_title"], "aboutP1": d["about_p1"], "aboutP2": d["about_p2"],
        "ctaTitle": d["cta_title"], "ctaSub": d["cta_sub"],
        "nav": [{"label": t, "href": h} for t, h in d["nav"]],
        "stats": [{"v": v, "l": l} for v, l in d["stats"]],
        "services": [{"icon": ic, "title": t, "desc": de} for ic, t, de in d["services"]],
        "process": [{"title": t, "desc": de} for t, de in d["process"]],
        "testimonials": [{"q": q, "n": n, "r": r} for q, n, r in d["testimonials"]],
        "perks": d["perks"], "showcase": showcase,
        "heroMix": hero_mix,
        "studio": {"id": preset["id"], "label": preset["label"], "variants": preset["v"],
                   "order": preset["order"], "mode": theme["mode"], "fonts": preset["fonts"]},
        "icons": _ICON_PATHS,
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
        <Button size="sm" className="hidden md:inline-flex" onClick={() => location.href = "#apply"}>Apply</Button>{burger}</nav></header>;
  } else if (V.nav === "rule") {
    bar = <header className={cn("fixed top-0 inset-x-0 z-50 transition-all", sc ? "bg-bg/90 backdrop-blur-xl" : "")}>
      <div className="mx-auto max-w-6xl px-6 h-[68px] flex items-center justify-between border-b border-border/0" style={{ borderColor: sc ? "var(--border)" : "transparent" }}>
        <Logo /><nav className="hidden md:flex items-center gap-8">{links}<a href="#apply" className="text-sm font-semibold text-primary">Apply →</a></nav>{burger}</div></header>;
  } else {
    bar = <header className={cn("fixed top-0 inset-x-0 z-50 transition-all", sc ? "bg-bg/85 backdrop-blur-xl border-b border-border" : "border-b border-transparent")}>
      <div className="mx-auto max-w-6xl px-6 h-[72px] flex items-center justify-between"><Logo /><nav className="hidden md:flex items-center gap-8">{links}</nav>
        <div className="hidden md:flex"><Button size="sm" onClick={() => location.href = "#apply"}>Apply Now</Button></div>{burger}</div></header>;
  }
  return <>{bar}<AnimatePresence>{open && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
    className="md:hidden fixed inset-0 z-40 bg-bg/97 backdrop-blur-xl flex flex-col items-center justify-center gap-7">
    {D.nav.map(n => <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="font-heading text-2xl font-bold">{n.label}</a>)}
    <Button onClick={() => { setOpen(false); location.href = "#apply"; }}>Apply Now</Button></motion.div>}</AnimatePresence></>;
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
    <Magnetic><Button size="lg" onClick={() => location.href = "#apply"}>Start your application <Icon name="route" className="w-5 h-5" /></Button></Magnetic>
    <a href="#why" className="group inline-flex items-center gap-2 font-semibold text-text">Why {D.short}<span className="transition-transform group-hover:translate-x-1">→</span></a>
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
            <Magnetic><Button size="lg" className="rounded-full" onClick={() => location.href = "#apply"}>Start your application <Icon name="route" className="w-5 h-5" /></Button></Magnetic>
            <a href="#why" className="group inline-flex items-center gap-2 font-semibold text-text">See why drivers stay <span className="transition-transform group-hover:translate-x-1">→</span></a>
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
          <span className="text-primary tracking-[0.2em]">★★★★★</span>Trusted by professional drivers · USDOT-certified carrier · {D.routes} coverage</div></Reveal>
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
  const items = [...D.perks, "Weekly Direct Deposit", "USDOT Certified", "No-Touch Freight"];
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

/* ===== SERVICES ===== */
function ServicesList({ alt }) {
  return <Section id="services" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-[280px_1fr] gap-12">
    <div className="md:sticky md:top-28 self-start"><Label n="">Benefits</Label>
      <h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.04]", SERIF ? "text-[clamp(1.9rem,3.4vw,2.8rem)]" : "text-[clamp(1.8rem,3vw,2.5rem)]")}>What it means to drive with {D.short}</h2>
      <p className="text-muted mt-5 leading-relaxed">Every detail is built to keep you earning, rolling, and home on time.</p></div>
    <Stagger>{D.services.map((s, i) => <Item key={i}>
      <div className="group grid grid-cols-[auto_1fr_auto] gap-6 items-baseline py-7 border-t border-border last:border-b transition-all hover:px-2">
        <span className="font-heading font-bold text-[clamp(1.4rem,2vw,1.9rem)] text-muted/50 group-hover:text-primary transition-colors">{nn(i + 1)}</span>
        <div><h3 className="font-heading text-xl md:text-2xl font-bold tracking-tight">{s.title}</h3><p className="text-muted mt-2 max-w-xl leading-relaxed">{s.desc}</p></div>
        <Icon name={s.icon} className="w-6 h-6 text-primary/40 group-hover:text-primary transition-colors hidden md:block" /></div></Item>)}
    </Stagger></div></Section>;
}
function ServicesAccordion({ alt }) {
  const [open, setOpen] = useState(0);
  return <Section id="services" alt={alt}><div className="mx-auto max-w-6xl px-6">
    <Head n="" kicker="Benefits" title={"Built around the driver"} desc="Everything we do keeps you earning, rolling, and home on time." />
    <div className="grid md:grid-cols-[1fr_.85fr] gap-10 items-start">
      <div>{D.services.map((s, i) => <div key={i} className="border-t border-border last:border-b">
        <button onClick={() => setOpen(i)} className="w-full flex items-center gap-5 py-5 text-left">
          <span className={cn("font-heading font-bold text-lg transition-colors", open === i ? "text-primary" : "text-muted/50")}>{nn(i + 1)}</span>
          <span className={cn("font-heading text-xl font-bold tracking-tight transition-colors flex-1", open === i ? "text-text" : "text-muted")}>{s.title}</span>
          <Icon name={s.icon} className={cn("w-5 h-5 transition-colors", open === i ? "text-primary" : "text-muted/40")} /></button>
        <AnimatePresence initial={false}>{open === i && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.4, ease: EASE }} className="overflow-hidden">
          <p className="text-muted pb-6 pl-10 max-w-md leading-relaxed">{s.desc}</p></motion.div>}</AnimatePresence></div>)}</div>
      <div className="md:sticky md:top-28"><AnimatePresence mode="wait"><motion.div key={open} initial={{ opacity: 0, scale: 1.02 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.45, ease: EASE }}>
        <Img src={D.showcase[open % 4].img} alt={D.services[open].title} className="rounded-[calc(var(--radius)+8px)] border border-border aspect-[5/4]" /></motion.div></AnimatePresence></div>
    </div></div></Section>;
}
function Services() { const alt = D.studio.order.indexOf("services") % 2 === 0; return V.services === "accordion" ? <ServicesAccordion alt={alt} /> : <ServicesList alt={alt} />; }

/* ===== ABOUT ===== */
function About() {
  const alt = D.studio.order.indexOf("about") % 2 === 0;
  return <Section id="why" alt={alt}><div className="mx-auto max-w-6xl px-6 grid md:grid-cols-2 gap-14 items-center">
    <Reveal className="relative order-2 md:order-1"><Img src={D.showcase[1].img} alt={D.company} parallax className="rounded-[calc(var(--radius)+12px)] border border-border aspect-[4/5] shadow-xl" />
      <div className="absolute -top-5 -right-5 hidden md:block"><Card className="px-6 py-5 shadow-xl bg-surface"><div className="font-heading font-bold text-3xl text-primary"><Counter value={D.routes} /></div><div className="text-xs text-muted uppercase tracking-widest mt-1">Coverage</div></Card></div></Reveal>
    <div className="order-1 md:order-2"><Reveal><Label>Why {D.short}</Label></Reveal>
      <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-[1.05]", SERIF ? "text-[clamp(2rem,3.8vw,3rem)]" : "text-[clamp(1.9rem,3.4vw,2.7rem)]")}>{D.aboutTitle}</h2></Reveal>
      <Reveal delay={0.12}><p className="text-muted mt-6 leading-relaxed text-[1.05rem]">{D.aboutP1}</p></Reveal>
      <Reveal delay={0.16}><p className="text-muted mt-3 leading-relaxed">{D.aboutP2}</p></Reveal>
      <Stagger className="grid grid-cols-2 gap-x-6 gap-y-3.5 mt-8">{D.perks.slice(0, 6).map((p, i) => <Item key={i}>
        <div className="flex items-center gap-3 font-medium text-[0.95rem] border-l-2 border-primary/30 pl-3 py-0.5">{p}</div></Item>)}</Stagger>
    </div></div></Section>;
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
  return <section id="apply" className="relative py-24 md:py-32 overflow-hidden"><div className="mx-auto max-w-6xl px-6">
    <div className="relative overflow-hidden rounded-[calc(var(--radius)+18px)] border border-border grid md:grid-cols-2 gap-10 p-8 md:p-14 items-center">
      <div className="absolute inset-0 -z-10"><Img src={D.showcase[2].img} alt="" className="w-full h-full" /><div className="absolute inset-0 cta-scrim" /></div>
      <div className="relative text-white"><Reveal><Label>Apply now</Label></Reveal>
        <Reveal delay={0.06}><h2 className={cn("font-heading font-bold tracking-[-0.02em] mt-5 leading-tight", SERIF ? "text-[clamp(2rem,4vw,3.2rem)]" : "text-[clamp(1.9rem,3.6vw,2.9rem)]")}>{D.ctaTitle}</h2></Reveal>
        <Reveal delay={0.12}><p className="text-white/80 mt-5 leading-relaxed max-w-md">{D.ctaSub}</p></Reveal>
        <Reveal delay={0.18}><div className="flex flex-col gap-3 mt-8 text-sm text-white/85">
          <span className="flex items-center gap-2.5"><Icon name="check" className="w-4 h-4" />Two-minute application — no obligation</span>
          <span className="flex items-center gap-2.5"><Icon name="check" className="w-4 h-4" />A real recruiter calls within one business day</span></div></Reveal></div>
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
function Footer() {
  return <footer className="border-t border-border pt-20 pb-10"><div className="mx-auto max-w-6xl px-6">
    <div className="grid md:grid-cols-[1.5fr_1fr_1fr] gap-10">
      <div><Logo /><p className="text-muted text-sm mt-5 leading-relaxed max-w-xs">{D.company} — hiring {D.jobTitle}s across {D.cityState}. {D.routesType}, top weekly pay, real home time.</p></div>
      <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Explore</div><div className="flex flex-col gap-2.5">{D.nav.map(n => <a key={n.href} href={n.href} className="text-sm text-muted hover:text-text transition">{n.label}</a>)}<a href="#apply" className="text-sm text-primary font-semibold">Apply Now →</a></div></div>
      <div><div className="text-[11px] uppercase tracking-[0.18em] text-muted mb-4">Get in touch</div><div className="text-sm text-muted space-y-1.5"><div>{D.email}</div><div>{D.cityState}</div><div>USDOT Certified Carrier</div></div></div>
    </div>
    <div className="mt-16 font-heading font-bold tracking-[-0.04em] leading-none text-[clamp(2.5rem,12vw,9rem)] text-text/[0.06] select-none">{D.short}</div>
    <div className="mt-6 pt-6 border-t border-border flex flex-col md:flex-row justify-between gap-3 text-xs text-muted">
      <span>© {D.year} {D.company}. All rights reserved.</span>
      <span className="max-w-2xl md:text-right">Equal Opportunity Employer — all qualified applicants receive consideration without regard to race, color, religion, sex, national origin, disability or veteran status.</span></div>
  </div></footer>;
}

const SECTIONS = { stats: Stats, services: Services, about: About, process: Process, showcase: Showcase, testimonials: Testimonials };
function App() {
  return <><Nav /><Hero /><Ticker />
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
            "<title>" + data["company"] + " — CDL-A Driver Jobs | " + data["cityState"] + "</title>"
            "<meta name=\"description\" content=\"" + data["company"] + " is hiring CDL-A drivers in "
            + data["cityState"] + ". " + data["routesType"] + ", top weekly pay, real home time.\">"
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
