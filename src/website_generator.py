"""
Website generator for trucking company single-page sites.
Produces index.html + images/ folder as a zip file.
Also generates an Indeed job description (markdown).
"""

import random
import os
import zipfile
import tempfile
from pathlib import Path

# ── Color schemes ──────────────────────────────────────
# Each scheme: (name, css_vars dict)
COLOR_SCHEMES = [
    {
        "name": "navy-blue",
        "navy": "#0F172A", "dark_slate": "#1E293B",
        "primary": "#1D4ED8", "primary_light": "#3B82F6", "primary_hover": "#1E40AF",
        "accent_bg": "#DBEAFE", "accent_bg_light": "#EFF6FF",
        "gray_50": "#F8FAFC", "body_bg": "#FFFFFF",
    },
    {
        "name": "emerald-gold",
        "navy": "#022C22", "dark_slate": "#064E3B",
        "primary": "#0D9668", "primary_light": "#34D399", "primary_hover": "#065F46",
        "accent_bg": "#D1FAE5", "accent_bg_light": "#ECFDF5",
        "gray_50": "#F9FAFB", "body_bg": "#FFFFFF",
    },
    {
        "name": "slate-red",
        "navy": "#1C1917", "dark_slate": "#292524",
        "primary": "#DC2626", "primary_light": "#F87171", "primary_hover": "#B91C1C",
        "accent_bg": "#FEE2E2", "accent_bg_light": "#FEF2F2",
        "gray_50": "#FAFAF9", "body_bg": "#FFFFFF",
    },
    {
        "name": "charcoal-amber",
        "navy": "#1A1A2E", "dark_slate": "#16213E",
        "primary": "#D97706", "primary_light": "#FBBF24", "primary_hover": "#B45309",
        "accent_bg": "#FEF3C7", "accent_bg_light": "#FFFBEB",
        "gray_50": "#F9FAFB", "body_bg": "#FFFFFF",
    },
    {
        "name": "deep-teal",
        "navy": "#0C1B2A", "dark_slate": "#153147",
        "primary": "#0891B2", "primary_light": "#22D3EE", "primary_hover": "#0E7490",
        "accent_bg": "#CFFAFE", "accent_bg_light": "#ECFEFF",
        "gray_50": "#F8FAFC", "body_bg": "#FFFFFF",
    },
    {
        "name": "indigo-violet",
        "navy": "#1E1B4B", "dark_slate": "#312E81",
        "primary": "#6366F1", "primary_light": "#818CF8", "primary_hover": "#4F46E5",
        "accent_bg": "#E0E7FF", "accent_bg_light": "#EEF2FF",
        "gray_50": "#F8FAFC", "body_bg": "#FFFFFF",
    },
    {
        "name": "forest-lime",
        "navy": "#14200D", "dark_slate": "#1A2E05",
        "primary": "#4D7C0F", "primary_light": "#84CC16", "primary_hover": "#3F6212",
        "accent_bg": "#ECFCCB", "accent_bg_light": "#F7FEE7",
        "gray_50": "#FAFAF9", "body_bg": "#FFFFFF",
    },
    {
        "name": "midnight-rose",
        "navy": "#1C1025", "dark_slate": "#2D1B3D",
        "primary": "#BE185D", "primary_light": "#F472B6", "primary_hover": "#9D174D",
        "accent_bg": "#FCE7F3", "accent_bg_light": "#FDF2F8",
        "gray_50": "#FAF9FA", "body_bg": "#FFFFFF",
    },
    {
        "name": "steel-orange",
        "navy": "#18181B", "dark_slate": "#27272A",
        "primary": "#EA580C", "primary_light": "#FB923C", "primary_hover": "#C2410C",
        "accent_bg": "#FFEDD5", "accent_bg_light": "#FFF7ED",
        "gray_50": "#FAFAFA", "body_bg": "#FFFFFF",
    },
    {
        "name": "ocean-blue",
        "navy": "#0C1222", "dark_slate": "#162032",
        "primary": "#2563EB", "primary_light": "#60A5FA", "primary_hover": "#1D4ED8",
        "accent_bg": "#DBEAFE", "accent_bg_light": "#EFF6FF",
        "gray_50": "#F8FAFC", "body_bg": "#FFFFFF",
    },
]

# ── Font pairings ──────────────────────────────────────
# (heading_font, body_font, google_fonts_url)
FONT_PAIRS = [
    ("Titillium Web", "Source Sans 3",
     "https://fonts.googleapis.com/css2?family=Titillium+Web:wght@300;400;600;700;900&family=Source+Sans+3:wght@300;400;600;700&display=swap"),
    ("Rajdhani", "Inter",
     "https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap"),
    ("Outfit", "DM Sans",
     "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&family=DM+Sans:wght@300;400;500;600;700&display=swap"),
    ("Bebas Neue", "Plus Jakarta Sans",
     "https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap"),
    ("Sora", "Manrope",
     "https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=Manrope:wght@300;400;500;600;700;800&display=swap"),
    ("Archivo", "Nunito Sans",
     "https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800;900&family=Nunito+Sans:wght@300;400;500;600;700&display=swap"),
    ("Bricolage Grotesque", "Figtree",
     "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@400;500;600;700;800&family=Figtree:wght@300;400;500;600;700&display=swap"),
    ("Urbanist", "Lexend",
     "https://fonts.googleapis.com/css2?family=Urbanist:wght@300;400;500;600;700;800;900&family=Lexend:wght@300;400;500;600;700&display=swap"),
    ("Space Grotesk", "Work Sans",
     "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Work+Sans:wght@300;400;500;600;700&display=swap"),
    ("Rubik", "Karla",
     "https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700;800;900&family=Karla:wght@300;400;500;600;700;800&display=swap"),
    ("Poppins", "Lato",
     "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&family=Lato:wght@300;400;700;900&display=swap"),
    ("Montserrat", "Open Sans",
     "https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800;900&family=Open+Sans:wght@300;400;500;600;700&display=swap"),
]

# ── Hero tagline variations ────────────────────────────
HERO_TAGLINES = [
    ("Freight That <span class='accent'>Moves</span> When You Do", "Now Hiring CDL-A Drivers"),
    ("Your Freight. <span class='accent'>Our Priority.</span>", "Hiring Experienced Drivers"),
    ("Miles That <span class='accent'>Matter</span>", "Join Our Team Today"),
    ("Delivering <span class='accent'>Reliability</span> Coast to Coast", "CDL-A Drivers Wanted"),
    ("Built to <span class='accent'>Haul.</span> Ready to Roll.", "Now Hiring"),
    ("Keeping America <span class='accent'>Moving</span>", "Drivers Needed — Apply Now"),
    ("On Time. <span class='accent'>Every Time.</span>", "We're Hiring CDL-A Drivers"),
    ("The Road Starts <span class='accent'>Here</span>", "Join Our Growing Fleet"),
    ("Driven by <span class='accent'>Results</span>", "Hiring OTR Drivers"),
    ("Where <span class='accent'>Freight</span> Meets Trust", "Apply Today"),
]

# ── "How We Work" step variations ──────────────────────
HOW_WE_WORK_SETS = [
    [
        ("Submit Your Load", "Share your pickup, delivery, and timeline details. We'll match your freight with the right driver and route."),
        ("We Move It", "Your load is assigned, picked up on schedule, and tracked in real time. Our dispatch team stays on top of every mile."),
        ("Delivered On Time", "Safe, on-time delivery is the standard — not the exception. No surprises, just results."),
    ],
    [
        ("Tell Us What You Need", "Give us the details — origin, destination, timeline. We handle the rest from there."),
        ("We Handle the Logistics", "Your freight gets matched with an available driver and moved on your schedule. Real-time tracking included."),
        ("Proof of Delivery", "On-time drop-off, every time. We confirm delivery and keep you in the loop from start to finish."),
    ],
    [
        ("Request a Quote", "Send us your load details and we'll get back to you with a competitive rate — fast."),
        ("Scheduled & Dispatched", "Once confirmed, your freight is assigned to a professional driver and dispatched immediately."),
        ("Safe Delivery Guaranteed", "We don't cut corners. Your cargo arrives safely, on time, and in the condition it left."),
    ],
    [
        ("Get In Touch", "Call or email us with your freight requirements. We respond quickly and work around your schedule."),
        ("On the Road", "A qualified driver picks up your load and keeps dispatch informed every step of the way."),
        ("Mission Complete", "Delivery confirmed, paperwork handled. That's how we do business — clean and simple."),
    ],
]

# ── About section variations ───────────────────────────
ABOUT_TITLES = [
    "Built on Consistency, Driven by People",
    "Reliable Service, Real Relationships",
    "Moving Freight the Right Way",
    "Where Hard Work Meets the Highway",
    "A Carrier You Can Count On",
    "Straightforward Trucking, No Shortcuts",
]

COVERAGE_TITLES = [
    "All 48 States, Consistent Lanes",
    "Coast to Coast Coverage",
    "Nationwide Routes, Local Values",
    "From Point A to Anywhere",
    "Covering Every Mile That Matters",
]


def _pick_random(pool, count=1):
    """Pick random items from a pool without replacement."""
    return random.sample(pool, min(count, len(pool)))


def generate_website(info: dict) -> str:
    """
    Generate a trucking company website and return the path to the zip file.

    info dict keys:
        company_name: str
        company_short: str (abbreviated name for logo)
        domain: str
        email: str
        address: str (full street address)
        city_state: str (e.g. "Round Lake, IL 60073")
        phone: str (optional)
        service_type: str (e.g. "OTR Trucking — Dry Van — 48 States")
        job_title: str
        pay_range: str (e.g. "$1,300 – $1,600 / week")
        home_time: str (e.g. "Home every 2 weeks for 2 days")
        home_time_short: str (e.g. "2 Weeks Out")
        home_time_detail: str (e.g. "Home 2 Days")
        routes: str (e.g. "48 States")
        routes_type: str (e.g. "OTR Routes")
        min_experience: str (e.g. "6 Mo. Exp")
        fourth_card_label: str (e.g. "Min. Required")
        fourth_card_value: str (e.g. "6 Mo. Exp")
        perks: list[str]
        hero_desc: str (optional — custom hero description)
    """
    # Pick random style
    scheme = random.choice(COLOR_SCHEMES)
    heading_font, body_font, fonts_url = random.choice(FONT_PAIRS)
    tagline, badge = random.choice(HERO_TAGLINES)
    steps = random.choice(HOW_WE_WORK_SETS)
    about_title = random.choice(ABOUT_TITLES)
    coverage_title = random.choice(COVERAGE_TITLES)

    company = info["company_name"]
    short = info.get("company_short", company.split()[0])
    domain = info["domain"]
    email = info["email"]
    address = info["address"]
    city_state = info["city_state"]
    service = info.get("service_type", "OTR Trucking — Dry Van — 48 States")
    job_title = info["job_title"]
    pay_range = info["pay_range"]

    # Hero description
    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    state_only = city_state.split(",")[1].strip().split()[0] if "," in city_state else ""
    hero_desc = info.get("hero_desc", f"{company} keeps goods moving across all 48 states with reliable service — out of {city_only}, {state_only}.")

    # Build perks HTML
    perks_html = ""
    for p in info.get("perks", []):
        perks_html += f'        <div class="perk">{p}</div>\n'

    # Build logo parts
    logo_parts = short.split(None, 1)
    if len(logo_parts) == 2:
        logo_html = f'{logo_parts[0]}<span> {logo_parts[1].upper()}</span>'
    else:
        logo_html = f'{short}<span> {domain.split(".")[0].upper()}</span>'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company} — {service} | {city_state}</title>
  <meta name="description" content="{company} — {service} based in {city_state}. Now hiring experienced drivers.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{fonts_url}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: '{body_font}', sans-serif;
      color: #334155;
      background: {scheme["body_bg"]};
      overflow-x: hidden;
      line-height: 1.65;
    }}
    h1, h2, h3, h4, h5 {{ font-family: '{heading_font}', sans-serif; }}
    a {{ text-decoration: none; color: inherit; }}
    img {{ max-width: 100%; display: block; }}
    ul {{ list-style: none; }}

    :root {{
      --navy: {scheme["navy"]};
      --dark-slate: {scheme["dark_slate"]};
      --primary: {scheme["primary"]};
      --primary-light: {scheme["primary_light"]};
      --primary-hover: {scheme["primary_hover"]};
      --accent-bg: {scheme["accent_bg"]};
      --accent-bg-light: {scheme["accent_bg_light"]};
      --gray-50: {scheme["gray_50"]};
      --gray-100: #F1F5F9;
      --gray-400: #94A3B8;
      --gray-500: #64748B;
      --gray-700: #334155;
      --gray-900: #0F172A;
      --white: #FFFFFF;
    }}

    .reveal {{
      opacity: 0; transform: translateY(30px);
      transition: opacity 0.6s ease-out, transform 0.6s ease-out;
    }}
    .reveal.show {{ opacity: 1; transform: translateY(0); }}
    .reveal-left {{
      opacity: 0; transform: translateX(-30px);
      transition: opacity 0.6s ease-out, transform 0.6s ease-out;
    }}
    .reveal-left.show {{ opacity: 1; transform: translateX(0); }}
    .reveal-right {{
      opacity: 0; transform: translateX(30px);
      transition: opacity 0.6s ease-out, transform 0.6s ease-out;
    }}
    .reveal-right.show {{ opacity: 1; transform: translateX(0); }}
    .delay-1 {{ transition-delay: 0.1s; }}
    .delay-2 {{ transition-delay: 0.2s; }}
    .delay-3 {{ transition-delay: 0.3s; }}

    header {{
      position: fixed; top: 0; width: 100%; z-index: 1000;
      background: rgba(255,255,255,0.95); backdrop-filter: blur(12px);
      border-bottom: 1px solid transparent;
      transition: border-color 0.3s, box-shadow 0.3s; height: 68px;
    }}
    header.scrolled {{ border-bottom-color: #E2E8F0; box-shadow: 0 1px 12px rgba(0,0,0,0.06); }}
    .nav-inner {{
      max-width: 1200px; margin: 0 auto; padding: 0 32px;
      height: 100%; display: flex; align-items: center; justify-content: space-between;
    }}
    .logo {{
      font-family: '{heading_font}', sans-serif; font-weight: 900;
      font-size: 1.5rem; color: var(--navy); letter-spacing: -0.5px;
    }}
    .logo span {{ color: var(--primary); }}
    .nav-menu {{ display: flex; gap: 32px; align-items: center; }}
    .nav-menu a {{
      font-size: 0.88rem; font-weight: 600; color: var(--gray-500);
      letter-spacing: 0.3px; transition: color 0.3s;
    }}
    .nav-menu a:hover {{ color: var(--primary); }}
    .nav-cta {{
      background: var(--primary) !important; color: var(--white) !important;
      padding: 9px 22px; border-radius: 6px;
      font-size: 0.85rem !important; font-weight: 700 !important;
      transition: background 0.3s !important;
    }}
    .nav-cta:hover {{ background: var(--primary-hover) !important; }}

    .burger {{
      display: none; cursor: pointer; flex-direction: column; gap: 5px; z-index: 1001;
    }}
    .burger div {{
      width: 24px; height: 2px; background: var(--navy);
      border-radius: 2px; transition: all 0.3s;
    }}
    .burger.open div:nth-child(1) {{ transform: rotate(45deg) translate(5px, 5px); }}
    .burger.open div:nth-child(2) {{ opacity: 0; }}
    .burger.open div:nth-child(3) {{ transform: rotate(-45deg) translate(5px, -5px); }}

    .mobile-menu {{
      display: none; position: fixed; inset: 0; background: var(--white);
      z-index: 999; flex-direction: column; align-items: center;
      justify-content: center; gap: 32px;
    }}
    .mobile-menu.open {{ display: flex; }}
    .mobile-menu a {{
      font-family: '{heading_font}', sans-serif; font-size: 1.4rem;
      font-weight: 700; color: var(--navy); letter-spacing: 1px; transition: color 0.3s;
    }}
    .mobile-menu a:hover {{ color: var(--primary); }}

    .hero {{
      position: relative; min-height: 100vh; display: flex; align-items: center;
      background: url('images/hero-bg.jpg') center/cover no-repeat;
      padding: 120px 32px 80px;
    }}
    .hero::before {{
      content: ''; position: absolute; inset: 0;
      background: linear-gradient(135deg, rgba({_hex_to_rgb(scheme["navy"])},0.88) 0%, rgba({_hex_to_rgb(scheme["dark_slate"])},0.75) 100%);
    }}
    .hero-inner {{
      position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; width: 100%;
    }}
    .hero-badge {{
      display: inline-flex; align-items: center; gap: 8px;
      background: rgba({_hex_to_rgb(scheme["primary"])},0.15);
      border: 1px solid rgba({_hex_to_rgb(scheme["primary"])},0.3);
      color: var(--accent-bg); font-size: 0.78rem; font-weight: 600;
      padding: 6px 16px; border-radius: 50px; margin-bottom: 24px;
      letter-spacing: 1px; text-transform: uppercase;
    }}
    .hero-badge::before {{
      content: ''; width: 8px; height: 8px; background: #22C55E;
      border-radius: 50%; animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }} }}
    .hero h1 {{
      font-size: clamp(2.8rem, 6vw, 4.5rem); font-weight: 900; color: var(--white);
      line-height: 1.08; margin-bottom: 20px; max-width: 700px; letter-spacing: -1px;
    }}
    .hero h1 .accent {{ color: var(--primary-light); }}
    .hero-sub {{
      font-size: 1.15rem; color: var(--gray-400); max-width: 520px;
      line-height: 1.7; margin-bottom: 36px;
    }}
    .hero-actions {{ display: flex; gap: 14px; flex-wrap: wrap; }}
    .btn {{
      display: inline-block; padding: 14px 32px; border-radius: 6px;
      font-family: '{heading_font}', sans-serif; font-weight: 700;
      font-size: 0.95rem; letter-spacing: 0.3px; cursor: pointer;
      transition: all 0.3s; border: none; text-align: center;
    }}
    .btn-fill {{ background: var(--primary); color: var(--white); }}
    .btn-fill:hover {{ background: var(--primary-hover); transform: translateY(-2px); box-shadow: 0 6px 20px rgba({_hex_to_rgb(scheme["primary"])},0.35); }}
    .btn-ghost {{ background: transparent; color: var(--white); border: 1px solid rgba(255,255,255,0.2); }}
    .btn-ghost:hover {{ border-color: var(--primary-light); color: var(--primary-light); }}

    .hero-stats {{
      display: flex; gap: 48px; margin-top: 60px; padding-top: 32px;
      border-top: 1px solid rgba(255,255,255,0.08);
    }}
    .hero-stat-num {{
      font-family: '{heading_font}', sans-serif; font-size: 2rem;
      font-weight: 900; color: var(--white);
    }}
    .hero-stat-label {{
      font-size: 0.82rem; color: var(--gray-400); margin-top: 2px;
      text-transform: uppercase; letter-spacing: 1px;
    }}

    .section {{ padding: 100px 32px; }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    .section-header {{ text-align: center; max-width: 600px; margin: 0 auto 64px; }}
    .section-label {{
      font-family: '{heading_font}', sans-serif; font-size: 0.75rem;
      font-weight: 700; letter-spacing: 3px; text-transform: uppercase;
      color: var(--primary); margin-bottom: 12px;
    }}
    .section-heading {{
      font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 900;
      color: var(--gray-900); margin-bottom: 14px; letter-spacing: -0.5px; line-height: 1.15;
    }}
    .section-desc {{ font-size: 1.05rem; color: var(--gray-500); line-height: 1.7; }}

    .how-section {{ background: var(--gray-50); }}
    .steps-row {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }}
    .step-box {{
      background: var(--white); border: 1px solid #E2E8F0; border-radius: 10px;
      padding: 36px 28px; position: relative;
      transition: border-color 0.3s, box-shadow 0.3s, transform 0.3s;
    }}
    .step-box:hover {{
      border-color: var(--primary); box-shadow: 0 8px 30px rgba({_hex_to_rgb(scheme["primary"])},0.08);
      transform: translateY(-4px);
    }}
    .step-number {{
      font-family: '{heading_font}', sans-serif; font-size: 3rem;
      font-weight: 900; color: var(--accent-bg); line-height: 1; margin-bottom: 16px;
    }}
    .step-box:hover .step-number {{ color: var(--primary); transition: color 0.3s; }}
    .step-box h3 {{ font-size: 1.2rem; font-weight: 700; color: var(--gray-900); margin-bottom: 10px; }}
    .step-box p {{ font-size: 0.95rem; color: var(--gray-500); line-height: 1.6; }}

    .about-section {{ background: var(--white); }}
    .split-row {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 64px;
      align-items: center; margin-bottom: 80px;
    }}
    .split-row:last-child {{ margin-bottom: 0; }}
    .split-row.flip .split-img {{ order: 2; }}
    .split-row.flip .split-text {{ order: 1; }}
    .split-img img {{ border-radius: 10px; width: 100%; box-shadow: 0 4px 24px rgba(0,0,0,0.06); }}
    .split-text .section-label {{ text-align: left; }}
    .split-text h3 {{
      font-size: 1.9rem; font-weight: 900; color: var(--gray-900);
      margin-bottom: 16px; letter-spacing: -0.3px; line-height: 1.2;
    }}
    .split-text p {{ font-size: 1rem; color: var(--gray-500); margin-bottom: 24px; line-height: 1.7; }}
    .check-list {{ display: flex; flex-direction: column; gap: 12px; }}
    .check-list li {{
      display: flex; align-items: center; gap: 12px;
      font-size: 0.95rem; color: var(--gray-700); font-weight: 500;
    }}
    .check-dot {{
      width: 22px; height: 22px; border-radius: 6px;
      background: var(--accent-bg); color: var(--primary);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.7rem; font-weight: 900; flex-shrink: 0;
    }}

    .careers-section {{ background: var(--navy); }}
    .careers-section .section-heading {{ color: var(--white); }}
    .careers-section .section-desc {{ color: var(--gray-400); }}
    .job-title-bar {{ text-align: center; margin-bottom: 48px; }}
    .job-title-bar h3 {{ font-size: 1.4rem; color: var(--white); font-weight: 700; margin-bottom: 4px; }}
    .job-title-bar .salary {{
      font-size: 1.2rem; color: var(--primary-light); font-weight: 700;
      font-family: '{heading_font}', sans-serif;
    }}
    .cards-row {{
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;
      max-width: 960px; margin: 0 auto 48px;
    }}
    .info-card {{
      background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
      border-radius: 8px; padding: 24px 18px; text-align: center;
      transition: border-color 0.3s, transform 0.3s;
    }}
    .info-card:hover {{ border-color: var(--primary); transform: translateY(-3px); }}
    .info-card .ic-val {{
      font-family: '{heading_font}', sans-serif; font-size: 1.25rem;
      font-weight: 900; color: var(--primary-light); margin-bottom: 4px;
    }}
    .info-card .ic-lbl {{ font-size: 0.82rem; color: var(--gray-400); }}

    .perks-columns {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 12px 40px;
      max-width: 660px; margin: 0 auto 40px;
    }}
    .perk {{
      display: flex; align-items: center; gap: 10px;
      font-size: 0.93rem; color: rgba(255,255,255,0.75);
    }}
    .perk::before {{
      content: ''; width: 6px; height: 6px; border-radius: 50%;
      background: var(--primary-light); flex-shrink: 0;
    }}
    .eeo-text {{
      text-align: center; font-size: 0.78rem; color: rgba(255,255,255,0.25);
      max-width: 680px; margin: 0 auto; line-height: 1.6;
      padding-top: 28px; border-top: 1px solid rgba(255,255,255,0.06);
    }}

    .contact-section {{ background: var(--gray-50); }}
    .contact-layout {{
      display: grid; grid-template-columns: 1fr 1.1fr; gap: 48px;
      max-width: 1000px; margin: 0 auto;
    }}
    .contact-details h3 {{ font-size: 1.4rem; color: var(--gray-900); margin-bottom: 28px; }}
    .c-item {{ display: flex; gap: 14px; margin-bottom: 22px; align-items: flex-start; }}
    .c-icon {{
      width: 40px; height: 40px; border-radius: 8px;
      background: var(--accent-bg); color: var(--primary);
      display: flex; align-items: center; justify-content: center;
      font-size: 1rem; font-weight: 700; flex-shrink: 0;
    }}
    .c-item h4 {{
      font-family: '{heading_font}', sans-serif; font-size: 0.9rem;
      font-weight: 700; color: var(--gray-900); margin-bottom: 2px;
    }}
    .c-item p {{ font-size: 0.9rem; color: var(--gray-500); }}
    .quote-form {{
      background: var(--white); padding: 32px; border-radius: 10px; border: 1px solid #E2E8F0;
    }}
    .quote-form h3 {{ font-size: 1.2rem; color: var(--gray-900); margin-bottom: 24px; }}
    .field {{ margin-bottom: 14px; }}
    .field label {{
      display: block; font-size: 0.82rem; font-weight: 700;
      color: var(--gray-700); margin-bottom: 5px; letter-spacing: 0.3px;
    }}
    .field input, .field textarea, .field select {{
      width: 100%; padding: 11px 14px; border: 1px solid #E2E8F0;
      border-radius: 6px; font-family: '{body_font}', sans-serif;
      font-size: 0.95rem; color: var(--gray-700); background: var(--gray-50);
      outline: none; transition: border-color 0.3s;
    }}
    .field input:focus, .field textarea:focus, .field select:focus {{ border-color: var(--primary); }}
    .field textarea {{ resize: vertical; min-height: 90px; }}
    .field-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .quote-form .btn-fill {{ width: 100%; padding: 13px; font-size: 0.95rem; }}

    footer {{
      background: var(--navy); padding: 44px 32px 24px; color: var(--gray-400);
    }}
    .footer-row {{
      max-width: 1200px; margin: 0 auto; display: flex;
      justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;
    }}
    .f-logo {{
      font-family: '{heading_font}', sans-serif; font-weight: 900;
      font-size: 1.2rem; color: var(--white);
    }}
    .f-logo span {{ color: var(--primary); }}
    .f-links {{ display: flex; gap: 24px; }}
    .f-links a {{ font-size: 0.85rem; color: var(--gray-400); transition: color 0.3s; }}
    .f-links a:hover {{ color: var(--primary-light); }}
    .f-bottom {{
      text-align: center; font-size: 0.78rem; color: rgba(255,255,255,0.2);
      margin-top: 32px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.06);
      max-width: 1200px; margin-left: auto; margin-right: auto;
    }}

    @media (max-width: 900px) {{
      .nav-menu {{ display: none; }}
      .burger {{ display: flex; }}
      .steps-row {{ grid-template-columns: 1fr; max-width: 420px; margin: 0 auto; }}
      .split-row {{ grid-template-columns: 1fr; gap: 32px; }}
      .split-row.flip .split-img {{ order: 0; }}
      .split-row.flip .split-text {{ order: 0; }}
      .cards-row {{ grid-template-columns: 1fr 1fr; }}
      .contact-layout {{ grid-template-columns: 1fr; }}
      .hero-stats {{ gap: 28px; flex-wrap: wrap; }}
      .section {{ padding: 72px 20px; }}
    }}
    @media (max-width: 550px) {{
      .cards-row {{ grid-template-columns: 1fr; max-width: 300px; margin-left: auto; margin-right: auto; }}
      .perks-columns {{ grid-template-columns: 1fr; }}
      .field-row {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 2.2rem; }}
      .hero-stats {{ flex-direction: column; gap: 16px; }}
      .footer-row {{ flex-direction: column; text-align: center; }}
      .f-links {{ flex-wrap: wrap; justify-content: center; }}
    }}
  </style>
</head>
<body>

  <header id="header">
    <div class="nav-inner">
      <a href="#" class="logo">{logo_html}</a>
      <nav class="nav-menu">
        <a href="#process">Process</a>
        <a href="#about">About</a>
        <a href="#careers">Careers</a>
        <a href="#contact" class="nav-cta">Get a Quote</a>
      </nav>
      <div class="burger" id="burger" role="button" tabindex="0" aria-label="Menu">
        <div></div><div></div><div></div>
      </div>
    </div>
  </header>

  <div class="mobile-menu" id="mobMenu">
    <a href="#process" onclick="toggleMenu()">Process</a>
    <a href="#about" onclick="toggleMenu()">About</a>
    <a href="#careers" onclick="toggleMenu()">Careers</a>
    <a href="#contact" onclick="toggleMenu()">Contact</a>
  </div>

  <section class="hero">
    <div class="hero-inner">
      <div class="hero-badge reveal">{badge}</div>
      <h1 class="reveal">{tagline}</h1>
      <p class="hero-sub reveal">{hero_desc}</p>
      <div class="hero-actions reveal">
        <a href="#contact" class="btn btn-fill">Request a Quote</a>
        <a href="#careers" class="btn btn-ghost">View Open Positions</a>
      </div>
      <div class="hero-stats reveal">
        <div>
          <div class="hero-stat-num">48</div>
          <div class="hero-stat-label">States Covered</div>
        </div>
        <div>
          <div class="hero-stat-num">24/7</div>
          <div class="hero-stat-label">Dispatch Support</div>
        </div>
        <div>
          <div class="hero-stat-num">OTR</div>
          <div class="hero-stat-label">{info.get("service_short", "Dry Van Service")}</div>
        </div>
      </div>
    </div>
  </section>

  <section class="section how-section" id="process">
    <div class="container">
      <div class="section-header reveal">
        <div class="section-label">Our Process</div>
        <h2 class="section-heading">How We Work</h2>
        <p class="section-desc">From first call to final delivery — straightforward logistics built on communication and accountability.</p>
      </div>
      <div class="steps-row">
        <div class="step-box reveal delay-1">
          <div class="step-number">01</div>
          <h3>{steps[0][0]}</h3>
          <p>{steps[0][1]}</p>
        </div>
        <div class="step-box reveal delay-2">
          <div class="step-number">02</div>
          <h3>{steps[1][0]}</h3>
          <p>{steps[1][1]}</p>
        </div>
        <div class="step-box reveal delay-3">
          <div class="step-number">03</div>
          <h3>{steps[2][0]}</h3>
          <p>{steps[2][1]}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="section about-section" id="about">
    <div class="container">
      <div class="split-row">
        <div class="split-img reveal-left">
          <img src="images/about-fleet.jpg" alt="{company} fleet">
        </div>
        <div class="split-text reveal-right">
          <div class="section-label">About Us</div>
          <h3>{about_title}</h3>
          <p>{company} is a {city_state}-based carrier focused on {service.lower()} across the continental U.S. We invest in our equipment and our people — because both need to perform every day.</p>
          <ul class="check-list">
            <li><span class="check-dot">&#10003;</span> Reliable, newer equipment</li>
            <li><span class="check-dot">&#10003;</span> Experienced, professional drivers</li>
            <li><span class="check-dot">&#10003;</span> 24/7 dispatch and support</li>
            <li><span class="check-dot">&#10003;</span> No-touch dry van freight</li>
          </ul>
        </div>
      </div>
      <div class="split-row flip">
        <div class="split-img reveal-right">
          <img src="images/coverage-routes.jpg" alt="Route coverage">
        </div>
        <div class="split-text reveal-left">
          <div class="section-label">Coverage</div>
          <h3>{coverage_title}</h3>
          <p>Whether it's a cross-country haul or a regional lane, {company} has the coverage and the freight to keep your business — and our drivers — moving without gaps.</p>
          <ul class="check-list">
            <li><span class="check-dot">&#10003;</span> Full lower-48 coverage</li>
            <li><span class="check-dot">&#10003;</span> Steady, year-round freight volume</li>
            <li><span class="check-dot">&#10003;</span> Dedicated lane options available</li>
            <li><span class="check-dot">&#10003;</span> On-time delivery track record</li>
          </ul>
        </div>
      </div>
    </div>
  </section>

  <section class="section careers-section" id="careers">
    <div class="container">
      <div class="section-header reveal">
        <div class="section-label">Careers</div>
        <h2 class="section-heading">Drive With {short}</h2>
        <p class="section-desc">We're hiring experienced drivers who want solid pay, real home time, and a team that has their back.</p>
      </div>
      <div class="job-title-bar reveal">
        <h3>{job_title}</h3>
        <div class="salary">{pay_range}</div>
      </div>
      <div class="cards-row reveal">
        <div class="info-card">
          <div class="ic-val">{info.get("pay_short", pay_range.split("/")[0].strip())}</div>
          <div class="ic-lbl">Weekly Pay</div>
        </div>
        <div class="info-card">
          <div class="ic-val">{info.get("home_time_short", "2 Weeks Out")}</div>
          <div class="ic-lbl">{info.get("home_time_detail", "Home 2 Days")}</div>
        </div>
        <div class="info-card">
          <div class="ic-val">{info.get("routes", "48 States")}</div>
          <div class="ic-lbl">{info.get("routes_type", "OTR Routes")}</div>
        </div>
        <div class="info-card">
          <div class="ic-val">{info.get("fourth_card_value", "6 Mo. Exp")}</div>
          <div class="ic-lbl">{info.get("fourth_card_label", "Min. Required")}</div>
        </div>
      </div>
      <div class="perks-columns reveal">
{perks_html}      </div>
      <p class="eeo-text reveal">{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, veteran status, sexual orientation, gender identity, or any other protected status.</p>
    </div>
  </section>

  <section class="section contact-section" id="contact">
    <div class="container">
      <div class="section-header reveal">
        <div class="section-label">Contact</div>
        <h2 class="section-heading">Let's Talk Freight</h2>
        <p class="section-desc">Need a quote or want to apply? Reach out — we respond fast.</p>
      </div>
      <div class="contact-layout">
        <div class="contact-details reveal-left">
          <h3>Get In Touch</h3>
          <div class="c-item">
            <div class="c-icon">&#9993;</div>
            <div>
              <h4>Email</h4>
              <p>{email}</p>
            </div>
          </div>
          <div class="c-item">
            <div class="c-icon">&#9872;</div>
            <div>
              <h4>Address</h4>
              <p>{address}<br>{city_state}</p>
            </div>
          </div>
          <div class="c-item">
            <div class="c-icon">&#9742;</div>
            <div>
              <h4>Hours</h4>
              <p>Dispatch available 24/7</p>
            </div>
          </div>
        </div>
        <div class="quote-form reveal-right">
          <h3>Request a Quote</h3>
          <form id="contactForm">
            <div class="field-row">
              <div class="field">
                <label>Full Name</label>
                <input type="text" placeholder="Your name" required>
              </div>
              <div class="field">
                <label>Company</label>
                <input type="text" placeholder="Company name">
              </div>
            </div>
            <div class="field-row">
              <div class="field">
                <label>Email</label>
                <input type="email" placeholder="you@email.com" required>
              </div>
              <div class="field">
                <label>Phone</label>
                <input type="tel" placeholder="(555) 000-0000">
              </div>
            </div>
            <div class="field">
              <label>Inquiry Type</label>
              <select>
                <option value="">Select one</option>
                <option value="quote">Freight Quote</option>
                <option value="apply">Driver Application</option>
                <option value="general">General Inquiry</option>
              </select>
            </div>
            <div class="field">
              <label>Message</label>
              <textarea placeholder="Tell us what you need..."></textarea>
            </div>
            <button type="submit" class="btn btn-fill">Send Message</button>
          </form>
        </div>
      </div>
    </div>
  </section>

  <footer>
    <div class="footer-row">
      <div class="f-logo">{logo_html}</div>
      <div class="f-links">
        <a href="#process">Process</a>
        <a href="#about">About</a>
        <a href="#careers">Careers</a>
        <a href="#contact">Contact</a>
      </div>
    </div>
    <div class="f-bottom">&copy; 2026 {company}. All rights reserved. | {city_state}</div>
  </footer>

  <script>
    const burger = document.getElementById('burger');
    const mobMenu = document.getElementById('mobMenu');
    function toggleMenu() {{
      burger.classList.toggle('open');
      mobMenu.classList.toggle('open');
      document.body.style.overflow = mobMenu.classList.contains('open') ? 'hidden' : '';
    }}
    burger.addEventListener('click', toggleMenu);
    window.addEventListener('scroll', () => {{
      document.getElementById('header').classList.toggle('scrolled', window.scrollY > 40);
    }});
    const io = new IntersectionObserver((entries) => {{
      entries.forEach(e => {{ if (e.isIntersecting) e.target.classList.add('show'); }});
    }}, {{ threshold: 0.12 }});
    document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => io.observe(el));
    document.getElementById('contactForm').addEventListener('submit', e => {{
      e.preventDefault();
      alert('Thanks! We\\'ll get back to you shortly.');
      e.target.reset();
    }});
  </script>

</body>
</html>'''

    # Create temp dir, write files, zip
    tmp_dir = tempfile.mkdtemp()
    site_dir = os.path.join(tmp_dir, domain.replace(".", "_"))
    os.makedirs(os.path.join(site_dir, "images"), exist_ok=True)

    # Write HTML
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # Create placeholder images
    for img_name in ["hero-bg.jpg", "about-fleet.jpg", "coverage-routes.jpg"]:
        placeholder = os.path.join(site_dir, "images", img_name)
        _create_placeholder_image(placeholder, scheme)

    # Zip it
    zip_name = f"{domain.replace('.', '_')}_website.zip"
    zip_path = os.path.join(tmp_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(site_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, site_dir)
                zf.write(file_path, arcname)

    return zip_path


def generate_job_description(info: dict) -> str:
    """Generate a unique Indeed job description as markdown text."""
    company = info["company_name"]
    city_state = info["city_state"]
    job_title = info["job_title"]
    pay_range = info["pay_range"]
    home_time = info.get("home_time", "Home every 2 weeks for 2 days")
    perks = info.get("perks", [])
    min_exp = info.get("min_experience", "6 months")

    # Randomize section titles to keep each description unique
    section_styles = [
        {"duties": "Day-to-Day", "reqs": "What You Bring", "pay": "Your Pay & Benefits", "schedule": "Home Time & Routes"},
        {"duties": "The Work", "reqs": "What We Need", "pay": "Compensation", "schedule": "Schedule & Routes"},
        {"duties": "Behind the Wheel", "reqs": "What We Need From You", "pay": "What You're Getting", "schedule": "The Schedule"},
        {"duties": "On the Road", "reqs": "Requirements", "pay": "Pay & Perks", "schedule": "Where You'll Run"},
        {"duties": "Your Daily Run", "reqs": "Qualifications", "pay": "What We Offer", "schedule": "Routes & Home Time"},
        {"duties": "What the Job Looks Like", "reqs": "Who We're Looking For", "pay": "The Package", "schedule": "Routing & Time Off"},
    ]

    style = random.choice(section_styles)
    perks_md = "\n".join(f"- {p}" for p in perks)

    md = f"""# {job_title} — {company}

**Location:** {city_state} (OTR — All 48 States)
**Job Type:** Full-Time
**Pay:** {pay_range} (based on experience)

---

{company} is looking for a dependable driver out of {city_state}. We run freight across all 48 states with consistent miles and a dispatch team that keeps things moving. If you want steady work, fair pay, and a carrier that respects your time — keep reading.

## {style["duties"]}

- Operate a company truck on OTR routes across the lower 48 states
- Pick up and deliver freight safely and on schedule
- Complete pre-trip and post-trip inspections per DOT regulations
- Communicate with dispatch for load assignments and route updates
- Maintain accurate logs and comply with all FMCSA/DOT requirements
- Handle all freight as no-touch

## {style["reqs"]}

- Valid Class A CDL
- Minimum {min_exp} of OTR experience
- Clean MVR — no major violations in the past 3 years
- Current DOT medical card
- Must pass drug screen and background check
- Must be at least 21 years of age
- Authorized to work in the United States

## {style["pay"]}

- **{pay_range}** based on experience
{perks_md}

## {style["schedule"]}

- **{home_time}**
- OTR routes across all 48 states
- Full-time, consistent freight year-round

---

*{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, veteran status, sexual orientation, gender identity, or any other characteristic protected by applicable federal, state, or local law.*
"""
    return md


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'R,G,B' string for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def _create_placeholder_image(path: str, scheme: dict):
    """Create a simple SVG placeholder image saved as .jpg (actually SVG content)."""
    # We'll create a minimal colored placeholder — user replaces with real photos
    primary = scheme["primary"]
    navy = scheme["navy"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
  <rect fill="{navy}" width="1200" height="800"/>
  <rect fill="{primary}" opacity="0.15" x="100" y="100" width="1000" height="600" rx="20"/>
  <text x="600" y="420" text-anchor="middle" fill="{primary}" font-family="sans-serif" font-size="32" opacity="0.4">Replace with photo</text>
</svg>'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
