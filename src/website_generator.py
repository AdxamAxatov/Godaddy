"""
Website generator for trucking company single-page sites.
Produces index.html + images/ folder as a zip file.
Also generates an Indeed job description (markdown).
"""

import json
import re
import random
import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# ── Owner-name resolution (for Indeed appeals) ─────────
_GENERIC_MAILBOXES = {
    "info", "sales", "dispatch", "hr", "jobs", "contact", "office", "careers",
    "admin", "support", "recruiting", "drive", "driving", "apply", "hiring", "team",
}
_OWNER_FIRST_NAMES = [
    "Lorna", "Marcus", "Dana", "Priya", "Hector", "Renee", "Curtis", "Yolanda",
    "Devin", "Tanya", "Roy", "Camille", "Brett", "Nadia", "Glenn", "Shauna",
    "Andre", "Marisol", "Keith", "Bianca", "Dwayne", "Allison", "Hassan", "Gloria",
]


def _resolve_owner_name(email: str, domain: str) -> str:
    """Owner first name for the appeal. A personal email local-part becomes the
    name; a generic mailbox (info@, sales@, ...) or no email falls back to a
    plausible name seeded by the domain so it's stable per company. Uses a
    private RNG — never touches the global random state."""
    local = email.split("@", 1)[0] if email and "@" in email else ""
    cleaned = re.sub(r"[^a-zA-Z]", "", local)
    if cleaned and cleaned.lower() not in _GENERIC_MAILBOXES:
        return cleaned[:1].upper() + cleaned[1:].lower()
    seed = (domain or local or "carrier").lower()
    return random.Random(seed).choice(_OWNER_FIRST_NAMES)


_COMPANY_DATA_RE = re.compile(
    r'<script[^>]*id="company-data"[^>]*>(.*?)</script>', re.DOTALL)


def _company_data_script(data: dict) -> str:
    """Embed posting data as breakout-safe JSON in a <script> tag."""
    payload = json.dumps(data).replace("<", "\\u003c")
    return f'<script type="application/json" id="company-data">{payload}</script>\n'


def extract_company_data(html: str):
    """Return the embedded company-data dict, or None if absent/unparseable."""
    m = _COMPANY_DATA_RE.search(html or "")
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except (ValueError, TypeError):
        return None


# ── Stock image pools ──────────────────────────────────
_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "stock_images"
_HERO_IMAGES = sorted(_ASSETS_DIR.glob("hero_*.jpg"))
_ABOUT_IMAGES = sorted(_ASSETS_DIR.glob("about_*.jpg"))
_COVERAGE_IMAGES = sorted(_ASSETS_DIR.glob("coverage_*.jpg"))

# ── No-repeat image state ──────────────────────────────
# Persists last-used image(s) per slot across renders so the next site
# won't reuse the exact image that the previous site used.
_IMG_STATE_FILE = Path(__file__).parent.parent / "logs" / "last_used_images.json"


def _load_img_state() -> dict:
    try:
        return json.loads(_IMG_STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _save_img_state(state: dict) -> None:
    try:
        _IMG_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _IMG_STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except OSError:
        pass  # best-effort; never break rendering on state-file issues


def _pick_unique(pool_paths, count: int, slot_key: str, state: dict, fallback: str) -> list:
    """Pick `count` unique image names from pool, avoiding the slot's last-used set.
    Falls back gracefully if the pool is smaller than count."""
    available = [p.name for p in pool_paths]
    if not available:
        return [fallback] * count
    last = state.get(slot_key, [])
    if isinstance(last, str):
        last = [last]
    excluded = set(last)
    candidates = [n for n in available if n not in excluded] or available[:]
    random.shuffle(candidates)
    picks = candidates[:count]
    while len(picks) < count:  # pool smaller than count — allow repeat
        picks.append(random.choice(available))
    state[slot_key] = picks if count > 1 else picks[0]
    return picks

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

# ── Hero tagline variations (30) ───────────────────────
HERO_TAGLINES = [
    ("Freight That <span class='accent'>Moves</span> When You Do", "Now Hiring CDL-A Drivers"),
    ("Your Freight. <span class='accent'>Our Priority.</span>", "Hiring Experienced Drivers"),
    ("Miles That <span class='accent'>Matter</span>", "Join Our Team Today"),
    ("Delivering <span class='accent'>Reliability</span> Coast to Coast", "CDL-A Drivers Wanted"),
    ("Built to <span class='accent'>Haul.</span> Ready to Roll.", "Now Hiring"),
    ("Keeping America <span class='accent'>Moving</span>", "Drivers Needed — Apply Now"),
    ("On Time. <span class='accent'>Every Time.</span>", "We're Hiring CDL-A Drivers"),
    ("The Road Starts <span class='accent'>Here</span>", "Join Our Growing Fleet"),
    ("Driven by <span class='accent'>Results</span>", "Hiring CDL-A Drivers"),
    ("Where <span class='accent'>Freight</span> Meets Trust", "Apply Today"),
    ("Hauling With <span class='accent'>Purpose</span>", "Now Accepting Applications"),
    ("No Shortcuts. <span class='accent'>No Excuses.</span>", "CDL-A Positions Open"),
    ("Load It. <span class='accent'>Ship It.</span> Done.", "Hiring Professional Drivers"),
    ("Real Freight. <span class='accent'>Real People.</span>", "Experienced Drivers Wanted"),
    ("Moving What <span class='accent'>Matters</span> Most", "Grow Your Career With Us"),
    ("Logistics Without <span class='accent'>Limits</span>", "Join Our Fleet"),
    ("From Dock to <span class='accent'>Destination</span>", "Open Positions Available"),
    ("The <span class='accent'>Backbone</span> of Business", "We're Looking for Drivers"),
    ("Freight Done <span class='accent'>Right</span>", "CDL-A Drivers — Apply Now"),
    ("Trusted by Shippers. <span class='accent'>Built by Drivers.</span>", "Now Hiring Nationwide"),
    ("Your Load. <span class='accent'>Our Word.</span>", "Hiring Reliable Drivers"),
    ("<span class='accent'>Steady</span> Miles. Strong Team.", "Open Driving Positions"),
    ("Committed to the <span class='accent'>Long Haul</span>", "CDL-A Opportunities"),
    ("We Don't Just <span class='accent'>Ship.</span> We Deliver.", "Drivers Needed"),
    ("Powered by <span class='accent'>People</span> Who Care", "Join the Team"),
    ("Making Freight <span class='accent'>Simple</span>", "Apply for Open Positions"),
    ("Coast to <span class='accent'>Coast.</span> Load to Load.", "Now Hiring CDL-A Drivers"),
    ("The Road Is <span class='accent'>Calling</span>", "Full-Time Positions Open"),
    ("Built for the <span class='accent'>Open Road</span>", "Experienced Drivers Welcome"),
    ("Professional Hauling. <span class='accent'>Personal Touch.</span>", "Start Driving With Us"),
]

# ── "How We Work" step variations (30 sets) ────────────
HOW_WE_WORK_SETS = [
    [("Submit Your Load", "Share your pickup, delivery, and timeline details. We'll match your freight with the right driver and route."),
     ("We Move It", "Your load is assigned, picked up on schedule, and tracked in real time. Our dispatch team stays on top of every mile."),
     ("Delivered On Time", "Safe, on-time delivery is the standard — not the exception. No surprises, just results.")],
    [("Tell Us What You Need", "Give us the details — origin, destination, timeline. We handle the rest from there."),
     ("We Handle the Logistics", "Your freight gets matched with an available driver and moved on your schedule. Real-time tracking included."),
     ("Proof of Delivery", "On-time drop-off, every time. We confirm delivery and keep you in the loop from start to finish.")],
    [("Request a Quote", "Send us your load details and we'll get back to you with a competitive rate — fast."),
     ("Scheduled & Dispatched", "Once confirmed, your freight is assigned to a professional driver and dispatched immediately."),
     ("Safe Delivery Guaranteed", "We don't cut corners. Your cargo arrives safely, on time, and in the condition it left.")],
    [("Get In Touch", "Call or email us with your freight requirements. We respond quickly and work around your schedule."),
     ("On the Road", "A qualified driver picks up your load and keeps dispatch informed every step of the way."),
     ("Mission Complete", "Delivery confirmed, paperwork handled. That's how we do business — clean and simple.")],
    [("Reach Out", "Tell us where your freight is and where it needs to go. We'll take care of the planning."),
     ("Loaded & Rolling", "A dedicated driver handles your shipment with care, keeping you updated at every checkpoint."),
     ("Signed & Sealed", "Your goods arrive intact, on schedule. BOL signed, job done.")],
    [("Share Your Shipment Details", "Provide the basics — pickup location, drop-off, weight, and timeline. We quote fast."),
     ("Freight in Motion", "Your shipment is picked up by an experienced driver and tracked mile by mile."),
     ("Delivery Confirmed", "On-time arrival with proof of delivery. That's the standard we hold ourselves to.")],
    [("Send Us Your Details", "Origin, destination, freight type — give us the info and we'll handle the logistics."),
     ("We Take It From Here", "Professional drivers, real-time updates, and a dispatch team that doesn't sleep on your load."),
     ("Job Done Right", "Consistent, damage-free delivery. Every single time.")],
    [("Start With a Call", "Reach out by phone or email. We'll scope your freight needs and build a plan."),
     ("Pickup & Transit", "Your freight is picked up on schedule and moved with precision across our network."),
     ("Delivered as Promised", "We keep our word. On-time delivery is how we earn your repeat business.")],
    [("Tell Us Your Timeline", "Whether it's tomorrow or next week, we'll find the right driver and route for your load."),
     ("In Transit", "From pickup to drop-off, your freight is tracked and managed by our dispatch team around the clock."),
     ("Successful Drop", "Load delivered, documents processed. Ready for the next one.")],
    [("Drop Us a Line", "Fill out a quick form or give us a call — we'll get you a rate within the hour."),
     ("Wheels Turning", "Your freight is assigned, loaded, and on the move. GPS tracking keeps everyone in the loop."),
     ("Another One Done", "Safe arrival, every time. That's the only way we operate.")],
    [("First Contact", "Give us the rundown — what you're shipping, when, and where. We respond same day."),
     ("Moving Your Freight", "An experienced driver takes your load and keeps dispatch updated at every stop."),
     ("Final Mile", "Delivery complete. Paperwork handled. No loose ends.")],
    [("Share the Details", "Let us know your origin, destination, and preferred dates. We'll match you with capacity."),
     ("On Schedule", "Your load hits the road on time, tracked by dispatch, and handled with care."),
     ("Promise Kept", "Delivered where you need it, when you need it. That's how we do things.")],
    [("Your Freight Starts Here", "Submit your load details and get a competitive rate — no obligations."),
     ("Assigned & Moving", "A qualified driver picks up your freight and checks in with dispatch throughout the haul."),
     ("Arrive & Confirm", "On-time delivery, every load. We don't make promises we can't keep.")],
    [("Kick Things Off", "Call, email, or submit a form. We'll have a plan ready before the day's over."),
     ("Hauling Your Load", "Experienced drivers handle your freight with the same care as their own paycheck depends on it — because it does."),
     ("Drop & Done", "Freight delivered safely. Proof sent. Onto the next one.")],
    [("Talk to Dispatch", "Reach out with your freight details — we'll match your load with a driver and confirm pickup."),
     ("Mile by Mile", "Real-time tracking, consistent communication, and a driver who knows the route."),
     ("Delivered Clean", "No damage, no delays, no excuses. That's our delivery standard.")],
    [("Place Your Order", "Tell us what needs moving. We'll line up the truck, plan the route, and confirm pickup time."),
     ("Freight On the Move", "Your shipment is in the hands of a professional, tracked and managed door to door."),
     ("Received & Signed", "On-time arrival. BOL signed. Another satisfied customer.")],
    [("One Call Does It", "Describe your freight, pick your dates, and let us handle the rest."),
     ("Picked Up & Tracked", "Your load is live on our system from the moment it leaves the dock."),
     ("Delivered Right", "Intact, on time, every time. No exceptions.")],
    [("Let's Get Started", "Send us the load info — pickup, drop, dates, weight. We quote fast and fair."),
     ("Your Load, Our Priority", "Once booked, your freight is assigned to a vetted driver and monitored through delivery."),
     ("Touchdown", "Freight at destination, paperwork complete. Simple as that.")],
    [("Book Your Load", "Get in touch with your shipment details. We'll confirm capacity and pricing within hours."),
     ("In Good Hands", "A professional driver picks up on time and keeps your freight secure across every mile."),
     ("Delivery Complete", "On schedule, on budget, no drama. The way shipping should be.")],
    [("Submit & Relax", "Give us the details and we take it from there. You focus on your business."),
     ("We've Got the Wheel", "Professional drivers, optimized routes, and dispatch that stays on it 24/7."),
     ("All Done", "Your freight arrives where it needs to be. Confirmation sent. Case closed.")],
    [("Quick Quote", "Drop us your load specs — we'll shoot back a rate and timeline same day."),
     ("Loaded Up", "Your freight hits the road with a driver who knows exactly where they're going."),
     ("At Your Door", "Delivered safe and on time. Proof of delivery in your inbox before the truck pulls away.")],
    [("Freight Inquiry", "Describe your shipping needs and we'll connect you with the right solution."),
     ("Route Locked In", "Driver assigned, pickup confirmed, and GPS tracking active throughout transit."),
     ("Final Delivery", "Load dropped, signed for, and confirmed. Ready for whatever's next.")],
    [("Make the Call", "Whether it's one load or a recurring lane, we'll build a plan that fits."),
     ("Driver Dispatched", "A reliable driver picks up your freight and moves it with zero surprises."),
     ("Proof in the Pudding", "Delivered on time. That's not a goal — it's a guarantee.")],
    [("Step One: Contact Us", "Share your freight details — we handle everything from there."),
     ("Step Two: We Ship", "Your load is picked up and tracked in real time by our dispatch team."),
     ("Step Three: Done", "On-time delivery with full documentation. No hassle.")],
    [("Describe Your Load", "Give us the pickup, delivery, and any special requirements. We plan around you."),
     ("Freight Moving", "From pickup to delivery, our team monitors your shipment every step of the way."),
     ("Successfully Delivered", "Load arrived. Customer happy. That's the only metric that matters.")],
    [("Connect With Us", "Tell us about your freight. We'll line up capacity and lock in a rate."),
     ("Shipment Underway", "Your load is picked up on schedule and tracked by our dispatch team in real time."),
     ("At the Dock", "Freight delivered, BOL signed, invoice sent. Clean and professional.")],
    [("Free Estimate", "Send us your details for a no-obligation quote. Fast turnaround guaranteed."),
     ("Truck Assigned", "A qualified driver picks up your freight and stays in contact with dispatch throughout."),
     ("Arrived Safe", "Delivery confirmed. Damage-free. On time. That's how we roll.")],
    [("Let Us Know", "Fill us in on the freight — we'll match it with a driver and get things moving."),
     ("En Route", "Your shipment is live-tracked from origin to destination with updates along the way."),
     ("Drop Complete", "Freight received by consignee. Documentation processed. Another load done right.")],
    [("What Are You Shipping?", "Tell us the what, where, and when — we take care of the how."),
     ("Out for Delivery", "Your freight is on the road, tracked in real time, and moving on schedule."),
     ("Signed, Sealed, Delivered", "On-time arrival. Clean drop. That's the whole story.")],
    [("Start Here", "Reach out with your freight needs. We'll have a truck ready faster than you'd expect."),
     ("Rolling Now", "Your load is picked up and heading to its destination with a professional behind the wheel."),
     ("Delivered & Documented", "Safe drop, on time, with proof of delivery. Just another day for us.")],
]

# ── About section variations (30) ──────────────────────
ABOUT_TITLES = [
    "Built on Consistency, Driven by People",
    "Reliable Service, Real Relationships",
    "Moving Freight the Right Way",
    "Where Hard Work Meets the Highway",
    "A Carrier You Can Count On",
    "Straightforward Trucking, No Shortcuts",
    "Family Values, Professional Results",
    "The Carrier That Shows Up",
    "Rooted in Hard Work",
    "More Than Just a Trucking Company",
    "Serious About Every Load",
    "Small Company. Big Standards.",
    "Doing Right by Every Customer",
    "Built From the Ground Up",
    "Trucking Done Honestly",
    "We Answer the Phone and Show Up",
    "Dependable by Design",
    "Run by People Who've Been Behind the Wheel",
    "Our Handshake Still Means Something",
    "Where Reliability Is the Baseline",
    "The Kind of Carrier You Keep Coming Back To",
    "No Flash. Just Freight.",
    "Keeping It Real on the Road",
    "A Team That Takes Pride in the Work",
    "We Earn Your Business Every Load",
    "Professional Hauling, Personal Accountability",
    "A Carrier Built on Trust",
    "Honest Work. Honest People.",
    "Simple Values, Solid Results",
    "Freight Is Our Business. Trust Is Our Foundation.",
]

# ── About description templates (30) — {company} and {city_state} get filled in ──
ABOUT_DESCRIPTIONS = [
    "{company} is a {city_state}-based carrier focused on dry van freight across the continental U.S. We invest in our equipment and our people — because both need to perform every day.",
    "Based out of {city_state}, {company} hauls freight the old-fashioned way — with reliable trucks, professional drivers, and a dispatch team that actually picks up the phone.",
    "{company} was built on the idea that trucking doesn't need to be complicated. Good equipment, good people, and honest communication. That's how we run things out of {city_state}.",
    "We're a {city_state} carrier that believes in doing the basics right. {company} keeps trucks rolling, drivers happy, and customers informed — no gimmicks.",
    "At {company}, we don't overpromise. We show up, load up, and deliver — every time. That's been our approach since day one out of {city_state}.",
    "{company} operates out of {city_state} with a focus on consistent, damage-free freight service. Our drivers are experienced and our dispatch team runs 24/7.",
    "Founded in {city_state}, {company} is a growing carrier that puts service quality above everything else. We keep our fleet modern and our drivers supported.",
    "{company} runs a tight operation out of {city_state}. We're not the biggest carrier — but we're one of the most dependable. Our customers stay because we deliver on our word.",
    "Headquartered in {city_state}, {company} provides reliable freight service with a personal touch. We treat every load like our reputation depends on it — because it does.",
    "We're {company}, a {city_state}-based trucking operation that was started by people who actually understand the road. Our priority is simple: move freight safely and on time.",
    "{company} keeps it simple. We're a {city_state} carrier with professional drivers, well-maintained trucks, and a team that communicates. That's the whole formula.",
    "Out of {city_state}, {company} serves shippers who need a carrier they can trust without babysitting. We take the load and handle everything from there.",
    "{company} is built around reliability. We're a {city_state} operation that moves freight across the region — with experienced drivers and equipment you can count on.",
    "We're a small carrier out of {city_state} that operates like a big one. {company} has the capacity, the tech, and the people to get your freight where it needs to be.",
    "{company} started with one truck and a commitment to do things right. Today we run a full fleet out of {city_state} — and that commitment hasn't changed.",
    "Based in {city_state}, {company} is a carrier that values accountability. Every driver, every load, every mile — tracked, managed, and delivered with care.",
    "At {company}, we believe drivers are the backbone of this business. That's why we run well-maintained equipment out of {city_state} and treat our team right.",
    "{company} hauls dry van freight from {city_state} to everywhere the road goes. We're not flashy — just consistent, professional, and always available.",
    "We're a {city_state} trucking company that puts our money where our mouth is. {company} invests in safety, equipment, and people — and it shows in every delivery.",
    "Shipping with {company} is straightforward. Tell us what you need, we move it. No middlemen, no runaround. Just honest freight service out of {city_state}.",
    "{company} is proud to call {city_state} home. We're a carrier that understands what shippers actually need — reliability, communication, and zero excuses.",
    "From {city_state}, {company} covers its lanes with professional service. We've built our reputation one on-time delivery at a time.",
    "At {company}, freight moves because our people make it happen. We're a {city_state}-based carrier with a hands-on dispatch team and drivers who take pride in the work.",
    "{company} was founded with a simple mission: be the carrier that other companies wish they'd called first. Operating from {city_state}, we serve the entire continental U.S.",
    "Our operation runs out of {city_state}, and our standards run high. {company} delivers freight safely, on time, and without drama — that's the whole pitch.",
    "{company} is the kind of {city_state} carrier that earns trust the hard way — by showing up and doing the work, load after load.",
    "We don't cut corners at {company}. From our home base in {city_state}, we move freight with professionalism and a level of care that's hard to find.",
    "Rooted in {city_state}, {company} has grown by keeping promises. Our drivers are skilled, our trucks are maintained, and our word means something.",
    "{company} runs clean, on-time freight out of {city_state}. We're a no-nonsense carrier that lets results speak louder than marketing.",
    "The team at {company} takes freight personally. We're a {city_state} carrier that treats every shipment like it's the most important one on the road.",
]

# ── About checklist variations (30) ────────────────────
ABOUT_CHECKLISTS = [
    ["Reliable, newer equipment", "Experienced, professional drivers", "24/7 dispatch and support", "No-touch dry van freight"],
    ["Late-model trucks maintained weekly", "Drivers with proven track records", "Round-the-clock dispatch availability", "No-touch freight handling"],
    ["Well-maintained modern fleet", "CDL-A drivers with clean records", "Dedicated dispatch support", "Careful, no-touch cargo handling"],
    ["Equipment you can depend on", "Professional, vetted drivers", "Dispatch available around the clock", "Safe, no-touch shipping"],
    ["Fleet maintained to the highest standard", "Experienced team behind every wheel", "Live dispatch coverage 24/7", "Damage-free freight handling"],
    ["Trucks inspected and serviced regularly", "Drivers who know the roads", "Full-time dispatch team on standby", "No-touch, no-hassle freight"],
    ["Newer trucks with GPS tracking", "Qualified driving professionals", "Always-on dispatch communication", "Freight handled with care"],
    ["Modern equipment in top condition", "Skilled drivers with years on the road", "Real-time dispatch monitoring", "Zero-touch freight policy"],
    ["Trucks built for long hauls", "Experienced, safety-focused drivers", "24/7 live dispatch support", "No-touch dry van loads"],
    ["Clean, reliable fleet", "Drivers who take pride in the work", "Dispatch that never goes dark", "Careful freight management"],
    ["Regularly serviced equipment", "Vetted, professional drivers", "Always-available dispatch", "No-touch load handling"],
    ["Dependable trucks, every haul", "Experienced team of road professionals", "Dispatch coverage that never sleeps", "Freight security guaranteed"],
    ["Up-to-date fleet with tracking", "Drivers you can trust on the road", "Round-the-clock support from dispatch", "No-touch, damage-free delivery"],
    ["Maintained fleet, zero breakdowns", "Professional drivers with clean MVRs", "24-hour dispatch availability", "Freight handled right every time"],
    ["Top-condition equipment", "CDL-A drivers who deliver consistently", "Dispatch support at all hours", "No-touch dry van service"],
    ["Fleet that's always road-ready", "Reliable drivers with experience", "Dispatch on call day and night", "Secure, no-touch cargo"],
    ["Modern trucks you can count on", "Safe, experienced driving team", "Full-coverage dispatch support", "Professional freight handling"],
    ["New equipment, maintained right", "Drivers who respect the road and the load", "Dispatch team always a call away", "No-touch handling standard"],
    ["Trucks that don't quit", "Dedicated, professional drivers", "Real dispatch — real people, real time", "Damage-free delivery guarantee"],
    ["Fleet updated and GPS-tracked", "Seasoned professional drivers", "Support team available 24/7", "No-touch policy on all freight"],
    ["Road-ready rigs, always", "Drivers with proven safety records", "Live dispatch tracking", "No-touch freight, every load"],
    ["Reliable trucks, reliable service", "Professional drivers — background checked", "Around-the-clock dispatch team", "Freight protection built in"],
    ["Equipment inspected before every haul", "CDL-A team with real experience", "24/7 dispatch and driver support", "No-touch, secure hauling"],
    ["Maintained fleet with modern safety tech", "Drivers who show up and deliver", "Dispatch monitoring every mile", "Careful, professional handling"],
    ["Trucks kept in peak condition", "Experienced, courteous drivers", "Dispatch never more than a phone call away", "No-touch dry van shipping"],
    ["GPS-equipped modern fleet", "Drivers who know what they're doing", "Full-time dispatch coverage", "Secure, no-touch freight"],
    ["Fleet you can rely on", "Team of dedicated road professionals", "Dispatch support that's always there", "Every load handled with care"],
    ["Well-maintained trucks inside and out", "Qualified drivers, no exceptions", "Real-time dispatch communication", "No-touch freight operations"],
    ["Clean fleet, zero compromises", "Professional drivers on every route", "24/7 support from experienced dispatch", "Freight handled safely, always"],
    ["Solid equipment, solid team", "Experienced drivers across all lanes", "Dispatch available whenever you need them", "No-touch, on-time delivery"],
]

# ── Coverage section variations (30) ───────────────────
COVERAGE_TITLES = [
    "All 48 States, Consistent Lanes",
    "Coast to Coast Coverage",
    "Nationwide Routes, Local Values",
    "From Point A to Anywhere",
    "Covering Every Mile That Matters",
    "Routes That Run Like Clockwork",
    "48 States. Zero Gaps.",
    "The Whole Map, Every Day",
    "Full Coverage, Full Commitment",
    "National Reach, Personal Service",
    "From Here to Everywhere",
    "No State Too Far",
    "Lanes That Keep You Moving",
    "Freight Coverage Without Borders",
    "Cross-Country, Every Day",
    "All Roads Lead to Delivery",
    "Running Routes Across America",
    "Wherever the Freight Goes, We Go",
    "Consistent Lanes, Consistent Service",
    "Coverage You Can Map Out",
    "48 States of Reliable Service",
    "End-to-End, Coast-to-Coast",
    "Routes Built for Reliability",
    "National Lanes, No Excuses",
    "From Your Dock to Any Destination",
    "Our Routes, Your Confidence",
    "The Whole Country, One Carrier",
    "Covering America, One Load at a Time",
    "Full Lower-48 Coverage",
    "Your Freight, Our Network",
]

REGIONAL_COVERAGE_TITLES = [
    "Regional Lanes, Consistent Service",
    "Close to Home, Always on Time",
    "Focused Coverage, Reliable Routes",
    "Regional Routes That Work",
    "Shorter Lanes. Bigger Results.",
    "Multi-State Coverage, Local Feel",
    "Your Region, Our Priority",
    "Dedicated Lanes, Familiar Roads",
    "Regional Reach, Personal Service",
    "Routes Built Around Home Time",
    "Tight Network, Strong Results",
    "Covering What Matters Most",
    "Lanes That Get You Home",
    "Regional Freight Done Right",
    "Focused Routes, Consistent Freight",
]

COVERAGE_DESCRIPTIONS = [
    "Whether it's a cross-country haul or a regional lane, {company} has the coverage and the freight to keep your business — and our drivers — moving without gaps.",
    "From coast to coast, {company} runs consistent freight lanes across all 48 states. Wherever your freight needs to go, we've got a truck heading that direction.",
    "{company} covers its lanes with dependable service. We maintain regular routes so our drivers stay productive and your freight stays on schedule.",
    "We don't cherry-pick lanes. {company} runs freight across the continental U.S. with consistent volume and routes that keep things moving year-round.",
    "Our network covers all 48 states with steady freight volume. {company} keeps lanes consistent so you always know what to expect — reliable pickup and delivery.",
    "{company} operates a full nationwide network. Whether it's East Coast, West Coast, or anywhere in between, your freight gets the same level of care.",
    "All 48 states. All year. {company} maintains freight lanes that provide consistent coverage and keep our fleet moving without downtime.",
    "From {city_state} to every corner of the country, {company} delivers. We run regular routes across the U.S. with the reliability shippers need.",
    "{company}'s coverage spans the entire continental U.S. We don't overextend — we keep our lanes tight and our service consistent across every state.",
    "Need freight moved anywhere in the lower 48? {company} has you covered. We maintain a network of reliable routes with year-round freight volume.",
    "Our routes run deep across the country. {company} has built a network that keeps freight flowing coast to coast without service gaps.",
    "{company} runs freight from one end of the country to the other. Our drivers know the routes, and our dispatch team keeps everything moving smoothly.",
    "With coverage across all 48 states, {company} is the kind of carrier you call when you need freight moved anywhere — and delivered on time.",
    "We've built our lane network around reliability. {company} maintains consistent routes across the U.S. so your freight always has a path.",
    "{company} keeps its coverage tight and its service tighter. All 48 states, consistent lanes, and a team that knows every route.",
    "Our routes span the entire lower 48. {company} has the capacity and the consistency to handle your freight, wherever it needs to go.",
    "Coast to coast, border to border — {company} runs the lanes that keep American business moving. Reliable, consistent, and always available.",
    "{company} doesn't just cover the map — we know it. Our drivers run regular lanes across the U.S. and our dispatch keeps it all connected.",
    "All 48 states. Year-round freight. {company} provides the kind of coverage that lets you plan ahead with confidence.",
    "Wherever the road goes in the continental U.S., {company} goes too. We maintain strong lane coverage with steady, predictable freight volume.",
    "Our coverage isn't spotty — it's solid. {company} runs consistent routes across every major lane in the lower 48.",
    "{company} has freight moving in every direction across the country. Our nationwide coverage means your load always has a truck available.",
    "We run freight in all 48 states and we do it well. {company}'s lane coverage is built on consistency and dependability.",
    "From major interstates to rural drop-offs, {company} covers it all. Our network is designed for real-world freight, not just map dots.",
    "Nationwide coverage with local attention to detail. {company} runs the lower 48 with routes that make sense and service that delivers.",
    "{company}'s coverage area is simple: all of it. We run freight across the continental U.S. with routes that our drivers know inside and out.",
    "Our network keeps growing, but our standards stay the same. {company} covers all 48 states with the reliability you'd expect from a top carrier.",
    "Need it shipped across the state or across the country? {company} handles both with the same level of professionalism and care.",
    "{company} provides full lower-48 freight coverage with consistent lanes and year-round volume. No seasonal slowdowns, no coverage gaps.",
    "From dock to dock, coast to coast — {company} has the routes, the trucks, and the team to move your freight wherever it needs to go.",
]

COVERAGE_CHECKLISTS = [
    ["Full lower-48 coverage", "Steady, year-round freight volume", "Dedicated lane options available", "On-time delivery track record"],
    ["All 48 states covered", "Consistent freight year-round", "Preferred lane assignments", "Proven on-time performance"],
    ["Nationwide coverage", "No seasonal freight gaps", "Regular route options", "Strong delivery track record"],
    ["Coast-to-coast service", "Year-round freight availability", "Dedicated and spot lanes", "Reliable delivery history"],
    ["Lower-48 full coverage", "Freight that doesn't stop", "Lane consistency for drivers", "On-time rates above industry average"],
    ["Complete national coverage", "Steady volume, no dead miles", "Route familiarity for drivers", "Delivery commitments we keep"],
    ["48-state reach", "Consistent, predictable freight", "Dedicated lane opportunities", "Track record of on-time delivery"],
    ["Covering every major lane", "Non-stop freight flow", "Routes drivers can count on", "Dependable delivery every time"],
    ["All lower-48 lanes active", "Year-round shipping demand", "Preferred route matching", "On-time performance guaranteed"],
    ["Full U.S. coverage", "Freight keeps rolling, all seasons", "Lane options that fit your life", "Delivery reliability that's proven"],
    ["National route network", "Consistent freight volume", "Driver-friendly lane assignments", "Strong on-time history"],
    ["48 states, every day", "No off-season freight drops", "Regular lane commitments", "Reliable, on-time arrivals"],
    ["Cross-country capabilities", "Year-round loads available", "Familiar routes for our team", "On-time delivery is standard"],
    ["Coast-to-coast lanes", "Steady volume keeps trucks moving", "Route options that make sense", "On-time, every time"],
    ["Full national coverage", "Freight that flows all year", "Dedicated lane programs", "Proven delivery record"],
    ["48-state service area", "Consistent loads, consistent pay", "Routes planned with drivers in mind", "On-time rate that speaks for itself"],
    ["Nationwide freight lanes", "Zero seasonal slowdowns", "Lane preferences honored", "Track record you can verify"],
    ["Complete lower-48 network", "Year-round freight commitments", "Route familiarity built over time", "On-time performance is non-negotiable"],
    ["All 48 states in our network", "Steady freight, no downtime", "Lanes that work for everyone", "Delivery track record we're proud of"],
    ["National reach, every lane", "Freight available 365 days", "Dedicated and flexible routing", "Consistent on-time arrivals"],
    ["Full coverage across the U.S.", "Volume that keeps drivers earning", "Lane options for all preferences", "Delivery you can count on"],
    ["48-state freight network", "Reliable year-round volume", "Familiar lanes for our drivers", "On-time delivery, no exceptions"],
    ["Lower-48 coverage without gaps", "Steady freight flow", "Route assignments that make sense", "Proven punctuality"],
    ["From any origin to any destination", "Consistent shipping demand", "Driver-preferred lane matching", "On-time track record that sticks"],
    ["All lanes, all states", "Freight volume that doesn't quit", "Routes built around reliability", "On-time delivery as a rule"],
    ["National freight coverage", "Year-round load availability", "Consistent, familiar lanes", "Delivery commitments honored"],
    ["48 states served daily", "No freight shortages", "Route stability for our team", "Punctual delivery history"],
    ["Full continental coverage", "Steady demand across all seasons", "Lane assignments drivers prefer", "Delivery standards above the norm"],
    ["U.S.-wide coverage", "Loads available every week", "Routes that work for work-life balance", "On-time arrivals are our standard"],
    ["Covering the whole country", "Consistent volume, consistent routes", "Lane options for every driver", "Delivery reputation built on results"],
]

REGIONAL_COVERAGE_DESCRIPTIONS = [
    "Based in {city_state}, {company} provides reliable regional freight service across a focused multi-state area. Consistent lanes, dependable schedules, and freight that keeps moving.",
    "{company} runs regional lanes out of {city_state} with the kind of consistency drivers and shippers both appreciate. We keep our routes tight and our service solid.",
    "Regional freight done right. {company} operates dedicated lanes from {city_state}, keeping drivers close to home and freight on schedule.",
    "From {city_state}, {company} covers a focused service area with dependable regional freight. We maintain regular routes so drivers stay productive and shippers stay happy.",
    "{company} specializes in regional dry van freight from {city_state}. Shorter lanes, more home time, and the same professional service as any nationwide carrier.",
    "We keep things close to home at {company}. Our regional lanes out of {city_state} give drivers consistent miles without the long stretches away from family.",
    "{company} runs a tight regional network from {city_state}. Familiar routes, steady freight, and a schedule that lets you get home regularly.",
    "Regional lanes with real consistency — that's what {company} offers out of {city_state}. We've built our service area around reliability and driver satisfaction.",
    "{company} out of {city_state} keeps freight moving across our regional service area. Dedicated lanes, familiar routes, and a team that knows the territory.",
    "Focused coverage, consistent freight. {company} runs regional lanes from {city_state} with the reliability that shippers depend on and drivers appreciate.",
]

REGIONAL_COVERAGE_CHECKLISTS = [
    ["Focused regional coverage", "Steady, year-round freight volume", "Dedicated lane options available", "On-time delivery track record"],
    ["Multi-state service area", "Consistent freight year-round", "Familiar route assignments", "Proven on-time performance"],
    ["Regional lanes covered", "No seasonal freight gaps", "Regular route options", "Strong delivery track record"],
    ["Tight regional network", "Year-round freight availability", "Dedicated lanes for drivers", "Reliable delivery history"],
    ["Multi-state coverage", "Freight that doesn't stop", "Lane consistency for drivers", "On-time rates above industry average"],
    ["Focused service area", "Steady volume, minimal deadhead", "Route familiarity for drivers", "Delivery commitments we keep"],
    ["Regional reach", "Consistent, predictable freight", "Dedicated lane opportunities", "Track record of on-time delivery"],
    ["Covering key regional lanes", "Non-stop freight flow", "Routes drivers can count on", "Dependable delivery every time"],
    ["Strong regional presence", "Year-round shipping demand", "Preferred route matching", "On-time performance guaranteed"],
    ["Full regional coverage", "Freight keeps rolling, all seasons", "Lane options that get you home", "Delivery reliability that's proven"],
]




def generate_job_description(info: dict) -> str:
    """Generate an Indeed-compliant CDL-A job description as HTML fragments."""
    company = info["company_name"]
    city_state = info["city_state"]
    pay_range = info["pay_range"]
    home_time = info.get("home_time", "Home every 2 weeks for 3 days")
    perks = info.get("perks", [])
    min_exp = info.get("min_experience", "6 months")
    routes_type = info.get("routes_type", "OTR Routes")
    is_regional = "regional" in routes_type.lower()
    route_label = "Regional" if is_regional else "OTR"
    coverage_noun = "a multi-state regional area" if is_regional else "the lower 48"
    coverage_adj = "multi-state regional" if is_regional else "48-state"

    # ── Tone selection (voice variation across postings) ──
    tone = random.choice(["direct", "professional", "conversational"])

    # ── Tone-locked section titles ──
    titles = {
        "direct": {
            "pay": "Pay",
            "route": "Route & Schedule",
            "benefits": "Benefits",
            "duties": "Responsibilities",
            "reqs": "Requirements",
            "culture": "Why Drivers Stay",
            "apply": "Apply",
        },
        "professional": {
            "pay": "Compensation",
            "route": "Routes & Home Time",
            "benefits": "Benefits & Perks",
            "duties": "Job Responsibilities",
            "reqs": "Qualifications",
            "culture": "What Drivers Value",
            "apply": "How to Apply",
        },
        "conversational": {
            "pay": "The Pay",
            "route": "Your Routes & Home Time",
            "benefits": "What You Get",
            "duties": "What You'll Do",
            "reqs": "What You Need",
            "culture": "Why Drivers Choose Us",
            "apply": "Ready to Roll?",
        },
    }[tone]

    # ── Helpers ──
    def _ul(items):
        return "<ul>\n" + "".join(f"<li>{i}</li>\n" for i in items) + "</ul>"

    def _section(title, content_html):
        return f"<p><b>{title}</b></p>\n{content_html}"

    # ── 1. Pay & Compensation ──
    # Indeed rule: one defined range with a unit/period. Never "up to", stacked
    # ranges, or exaggerated/"guaranteed" earnings — those get flagged. A bonus
    # alongside the range is allowed (Indeed's own examples show "plus bonus").
    pay_bullets = [f"{pay_range} (weekly gross)", "Paid weekly via direct deposit"]
    if info.get("orientation_pay"):
        pay_bullets.append(f"{info['orientation_pay']} paid orientation")
    if info.get("sign_on_bonus"):
        pay_bullets.append(f"{info['sign_on_bonus']} sign-on bonus")
    pay_html = _section(titles["pay"], _ul(pay_bullets))

    # ── 2. Route & Schedule ──
    route_bullets = [
        f"{coverage_adj.capitalize()} {route_label} coverage out of {city_state}",
        home_time,
        "No-touch dry van freight",
        "Modern, well-maintained equipment on every run",
    ]
    route_html = _section(titles["route"], _ul(route_bullets))

    # ── 3. Intro (opens the posting: who we are + what we do + hook) ──
    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    coverage_phrase = "a focused multi-state region" if is_regional else "all 48 states"
    intros = [
        f"{company} is a {city_only}-based dry van carrier running {route_label} freight across {coverage_phrase}. We invest in our equipment, we invest in our people, and we don't cut corners on either. If you've been driving long enough to know what a well-run operation feels like, you'll recognize it here.",
        f"Based out of {city_only}, {company} hauls {route_label} dry van freight across {coverage_phrase}. Clean trucks, experienced drivers, and a dispatch team that actually picks up the phone — that's the whole formula.",
        f"{company} runs {route_label} dry van freight out of {city_only} across {coverage_phrase}. We're not the biggest carrier on the road — we're one of the most dependable. And we're adding experienced CDL-A drivers to the fleet.",
        f"Out of {city_only}, {company} operates a professional dry van fleet covering {coverage_phrase}. We're hiring CDL-A drivers who want consistent miles, honest pay, and a carrier that delivers on what it promises.",
        f"{company} is a straightforward {route_label} carrier based in {city_only} — clean trucks, steady freight, and a dispatch team that backs you up. If you've been through carriers that overpromise and underdeliver, this is what different looks like.",
        f"Headquartered in {city_only}, {company} runs {route_label} dry van freight across {coverage_phrase}. We run a tight operation, we pay consistently, and we don't waste anyone's time with games around home time or settlements.",
        f"{company} is a {city_only} trucking operation hauling dry van freight across {coverage_phrase}. We hire drivers who take the work seriously. In return, we provide the tools, the freight, and the support to make it worth their while.",
        f"At {company}, we run {route_label} dry van freight from {city_only} across {coverage_phrase}. Modern equipment, steady freight, and a team that treats drivers like the professionals they are — that's what we offer.",
        f"{company} hauls {route_label} dry van freight out of {city_only} across {coverage_phrase}. We built this company on consistency — for our customers and for our drivers. You get steady freight, straight pay, and a dispatch team that actually helps.",
        f"From {city_only}, {company} covers {coverage_phrase} with {route_label} dry van freight. We're hiring drivers who want to work for a carrier that acts like it values them. Honest pay, real home time, well-maintained equipment — that's the pitch.",
        f"{company} is a {city_only}-based carrier running dry van freight across {coverage_phrase}. Our drivers stay because the work is consistent, the pay is fair, and dispatch doesn't disappear when something goes sideways.",
        f"Out of {city_only}, {company} runs {route_label} dry van freight across {coverage_phrase}. We believe good drivers deserve a good company — clean equipment, reliable freight, no BS. If that matches what you're looking for, keep reading.",
        f"{company} operates {route_label} dry van freight from {city_only} across {coverage_phrase}. We're adding experienced CDL-A drivers to the team. If you take pride in the work, you'll fit here.",
        f"{company} is a {city_only} dry van carrier serving {coverage_phrase}. We run a professional operation — and we expect the same from the people behind the wheel. The basics done right, every week.",
        f"Based in {city_only}, {company} runs {route_label} dry van freight across {coverage_phrase}. We're a carrier worth driving for. Consistent miles, fair pay, and a team that doesn't disappear when you need them.",
    ]
    intro_html = f"<p>{random.choice(intros)}</p>"

    # ── 4. Benefits ──
    benefits_html = _section(titles["benefits"], _ul(perks)) if perks else ""

    # ── 5. Responsibilities (tone-locked) ──
    duties_by_tone = {
        "direct": [
            f"Safely operate a Class A commercial vehicle on assigned {route_label} lanes across {coverage_noun}",
            "Complete thorough pre-trip and post-trip inspections per DOT requirements",
            "Pick up and deliver freight on time per dispatch schedule",
            "Maintain accurate ELD logs, bills of lading, and delivery documentation",
            "Keep dispatch informed on load status, ETAs, and any road conditions",
            "Follow all federal, state, and company safety regulations without exception",
        ],
        "professional": [
            f"Operate a company-assigned Class A vehicle on {route_label.lower()} routes throughout {coverage_noun}",
            "Execute safe, timely freight pickups and deliveries in accordance with customer and company standards",
            "Conduct thorough pre-trip and post-trip vehicle inspections in compliance with DOT regulations",
            "Maintain regular communication with the dispatch team regarding load status, ETAs, and route adjustments",
            "Ensure full compliance with FMCSA Hours of Service regulations and maintain accurate electronic logs",
            "Document and report equipment defects, incidents, or service delays in a timely and accurate manner",
        ],
        "conversational": [
            f"Run {route_label} freight across {coverage_noun} out of {city_state}",
            "Do your pre-trip and post-trip every day — it protects you and the equipment",
            "Pick up and deliver on time, handle the customer's dock like it's your own",
            "Keep your ELD logs accurate — we run a clean operation and expect the same from our drivers",
            "Stay in touch with dispatch — communication keeps everyone moving",
            "All no-touch dry van — your job is driving, not loading",
        ],
    }
    duties_html = _section(titles["duties"], _ul(duties_by_tone[tone]))

    # ── 6. Requirements (modern, compliant phrasing) ──
    reqs = [
        "Valid Class A Commercial Driver's License (CDL-A)",
        f"Minimum {min_exp} verifiable {route_label} CDL-A driving experience within the past 3 years",
        "No DUI, reckless driving, or at-fault accidents in the past 36 months",
        "Current DOT medical examiner's certificate",
        "Must pass DOT pre-employment drug screening per 49 CFR Part 382",
        "Must be 21 years of age or older (federal interstate commerce requirement)",
        "Must not be currently enrolled in a DOT Substance Abuse Professional (SAP) return-to-duty program",
        "Legally authorized to work in the United States",
    ]
    reqs_html = _section(titles["reqs"], _ul(reqs))

    # ── 7. Optional: Why Drivers Stay OR Apply CTA (one of them, coin-flip) ──
    if random.random() < 0.5:
        culture_pool = [
            "Dispatch team that picks up the phone and actually helps",
            "Freight that keeps moving — no sitting at the yard waiting for loads",
            "Equipment that's maintained — we don't ask you to drive junk",
            "A team that treats drivers like the professionals they are",
            "Consistent lanes so you know what to expect week to week",
            "A safety culture that's real, not just a poster on the wall",
            "Direct deposit every week without fail",
            "No micromanaging — do your job, get your miles, get home",
            "Straight answers from recruiting — no bait-and-switch",
            "Drivers who've stayed with us for years, not months",
        ]
        bullets = random.sample(culture_pool, k=random.randint(3, 4))
        extra_html = _section(titles["culture"], _ul(bullets))
    else:
        # Keep CTAs on-platform (Indeed Apply button) and free of off-platform
        # routing ("call/text/email us") or misleading time guarantees — both
        # can get a posting flagged or removed.
        apply_lines = [
            f"Ready to make a move? Hit Apply and submit your application through Indeed — qualified drivers hear back quickly.",
            f"If {company} sounds like the right fit, apply through Indeed and our team will review your application.",
            f"Applying takes two minutes. Use the Apply button and we'll follow up on next steps.",
            f"Take the next step and apply on Indeed. We review applications daily for qualified drivers.",
            f"Qualified and interested? Apply now through Indeed to get the process started.",
        ]
        extra_html = f"<p><b>{titles['apply']}</b></p>\n<p>{random.choice(apply_lines)}</p>"

    # ── 8. EEO (modern, full coverage — PWFA + GINA + Bostock) ──
    eeo_variants = [
        f"{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex (including pregnancy, childbirth, and related medical conditions), national origin, age, disability, genetic information, veteran status, sexual orientation, gender identity, or any other characteristic protected by applicable federal, state, or local law.",
        f"{company} provides equal employment opportunities to all applicants and employees without regard to race, color, religion, sex (including pregnancy, childbirth, and related medical conditions), national origin, age, disability, genetic information, veteran status, sexual orientation, gender identity, or any other legally protected status.",
        f"Employment decisions at {company} are made without regard to race, color, religion, sex (including pregnancy, childbirth, and related medical conditions), national origin, age, disability, genetic information, veteran status, sexual orientation, gender identity, or any other characteristic protected by federal, state, or local law. {company} is an Equal Opportunity Employer.",
    ]
    eeo_html = f"<p><i>{random.choice(eeo_variants)}</i></p>"

    # ── Assemble (fixed order) ──
    parts = [
        intro_html,
        pay_html,
        route_html,
    ]
    if benefits_html:
        parts.append(benefits_html)
    parts.extend([duties_html, reqs_html, extra_html, eeo_html])

    return "\n\n".join(parts)


def _natural_list(items) -> str:
    items = [str(i) for i in items if str(i).strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def generate_appeal(info: dict) -> str:
    """Plain-text Indeed reinstatement appeal. Human-like and unique each run,
    built from the site's embedded company-data. Omits missing posting facts."""
    company = info.get("company_name", "our company")
    domain = info.get("domain", "")
    city_state = info.get("city_state", "")
    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    owner = info.get("owner_name") or _resolve_owner_name(info.get("email", ""), domain)
    job_title = info.get("job_title", "CDL-A Truck Driver")
    pay_range = info.get("pay_range", "")
    home_time = info.get("home_time", "")
    min_exp = info.get("min_experience", "")
    routes_type = info.get("routes_type", "OTR Routes")
    is_regional = "regional" in routes_type.lower()
    route_label = "Regional" if is_regional else "OTR"
    territory = "a focused multi-state region" if is_regional else "the lower 48"
    perks = info.get("perks", [])

    openings = [
        f"My name is {owner} and I run {company} out of {city_only}.",
        f"I'm {owner}, the owner of {company} here in {city_only}.",
        f"This is {owner} from {company} — we're a carrier based in {city_only}.",
        f"My name's {owner} and I own and operate {company} in {city_only}.",
        f"I'm {owner}, and I handle the day-to-day at {company} out of {city_only}.",
    ]
    nature = [
        f"We're a small {route_label.lower()} dry van carrier covering {territory}.",
        f"We run {route_label} dry van freight across {territory} — nothing fancy, just steady work.",
        f"We're a {route_label.lower()} carrier hauling dry van across {territory} with our own trucks.",
        f"We do {route_label} dry van runs across {territory}.",
    ]
    intros = [
        "I'm writing to appeal a flagged posting on our account.",
        "I'm reaching out to appeal a posting that got paused on our account.",
        "I wanted to follow up on a posting of ours that was flagged.",
    ]

    job_bits = []
    if pay_range:
        job_bits.append(f"The job we listed is a {job_title} paying {pay_range}.")
    else:
        job_bits.append(f"The job we listed is a {job_title}.")
    if home_time:
        job_bits.append(f"Home time is {home_time}.")
    if min_exp:
        job_bits.append(f"We ask for {min_exp} of CDL-A experience.")
    if perks:
        job_bits.append("We offer " + _natural_list(perks[:6]) + ".")
    job_block = " ".join(job_bits)

    legitimacy = [
        "I handle the hiring myself, so every application comes straight to me.",
        "There's no agency or third party involved — it's just us looking for a driver.",
        "We posted because we genuinely need a driver, plain and simple.",
        "Nothing about the posting is misleading; it's a real job at a real company.",
        "We're a small operation, and every hire matters to us.",
        "I'm the one reviewing applications and making the calls.",
    ]
    beats = " ".join(random.sample(legitimacy, k=random.randint(2, 3)))

    asks = [
        "I'd really appreciate it if you could take another look and reinstate the posting.",
        "I'd be grateful if this could be reviewed and put back up.",
        "Please take another look — I'd love to get this posting back online.",
        "I'm hoping you can review this and reinstate our access.",
    ]
    if domain:
        closes = [
            f"You can verify everything about us at {domain}, and I'm happy to send over any documents you need.",
            f"Everything checks out on our site at {domain}, and I can provide whatever paperwork helps.",
            f"Our site {domain} has all our company details, and I'll gladly share documents to confirm we're legitimate.",
        ]
    else:
        closes = [
            "I'm happy to send over any documents you need to verify us.",
            "I can provide whatever paperwork helps verify us.",
        ]

    p1 = " ".join([random.choice(openings), random.choice(nature), random.choice(intros)])
    p3 = " ".join([random.choice(asks), random.choice(closes)])
    paragraphs = [p1, job_block, beats, p3] if job_block else [p1, beats, p3]
    return "\n\n".join(p for p in paragraphs if p)


def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'R,G,B' string for use in rgba()."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


# ── Block-based website generation ────────────────────────────────────────────

def _build_ctx(info: dict, color: dict, font: tuple) -> dict:
    """Build a context dict with all variables needed by section blocks."""
    heading_font, body_font, font_url = font
    tagline, sub_tagline = random.choice(HERO_TAGLINES)
    steps = random.choice(HOW_WE_WORK_SETS)

    img_state = _load_img_state()
    hero_img = _pick_unique(_HERO_IMAGES, 1, "hero", img_state, "hero_1.jpg")[0]
    about_picks = _pick_unique(_ABOUT_IMAGES, 2, "about", img_state, "about_11.jpg")
    about_img, about_img2 = about_picks[0], about_picks[1]
    coverage_img = _pick_unique(_COVERAGE_IMAGES, 1, "coverage", img_state, "coverage_21.jpg")[0]
    _save_img_state(img_state)

    company = info["company_name"]
    short = info.get("company_short", company.split()[0])
    city_state = info.get("city_state", "")

    perks_html = "\n".join(
        f'<div class="perk">{p}</div>' for p in info.get("perks", [])
    )

    _is_regional = "regional" in info.get("routes_type", "OTR Routes").lower()
    about_desc = random.choice(ABOUT_DESCRIPTIONS).format(company=company, city_state=city_state)
    coverage_desc = random.choice(REGIONAL_COVERAGE_DESCRIPTIONS if _is_regional else COVERAGE_DESCRIPTIONS).format(company=company, city_state=city_state)
    about_title = random.choice(ABOUT_TITLES)
    about_checklist = random.choice(ABOUT_CHECKLISTS)
    coverage_title = random.choice(REGIONAL_COVERAGE_TITLES if _is_regional else COVERAGE_TITLES)
    coverage_checklist = random.choice(REGIONAL_COVERAGE_CHECKLISTS if _is_regional else COVERAGE_CHECKLISTS)

    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    state_only = city_state.split(",")[1].strip().split()[0] if "," in city_state else ""
    _hero_area = "a focused multi-state region" if _is_regional else "all 48 states"
    hero_desc = info.get(
        "hero_desc",
        f"{company} keeps goods moving across {_hero_area} with reliable service — out of {city_only}, {state_only}."
    )

    logo_parts = short.split(None, 1)
    if len(logo_parts) == 2:
        logo_html = f'{logo_parts[0]}<span> {logo_parts[1].upper()}</span>'
    else:
        logo_html = f'{short}<span> {info.get("domain", "").split(".")[0].upper()}</span>'

    return {
        "company_name": company,
        "company_short": short,
        "domain": info.get("domain", ""),
        "email": info.get("email", ""),
        "address": info.get("address", ""),
        "city_state": city_state,
        "job_title": info.get("job_title", "CDL-A Driver"),
        "pay_range": info.get("pay_range", "$1,400 – $1,700 / week"),
        "home_time": info.get("home_time", "Home every 2 weeks"),
        "home_time_short": info.get("home_time_short", "2 Weeks Out"),
        "home_time_detail": info.get("home_time_detail", "Home 2 Days"),
        "min_experience": info.get("min_experience", "6 Mo. Exp"),
        "fourth_card_value": info.get("fourth_card_value", "6 Mo. Exp"),
        "fourth_card_label": info.get("fourth_card_label", "Min. Required"),
        "routes": info.get("routes", "48 States"),
        "routes_type": info.get("routes_type", "OTR Routes"),
        "perks": info.get("perks", []),
        "primary": color["primary"],
        "primary_light": color["primary_light"],
        "primary_hover": color["primary_hover"],
        "navy": color["navy"],
        "dark_slate": color["dark_slate"],
        "accent_bg": color["accent_bg"],
        "accent_bg_light": color["accent_bg_light"],
        "gray_50": color["gray_50"],
        "body_bg": color["body_bg"],
        "font_heading": heading_font,
        "font_body": body_font,
        "font_url": font_url,
        "hero_img": hero_img,
        "about_img": about_img,
        "about_img2": about_img2,
        "coverage_img": coverage_img,
        "tagline": tagline,
        "sub_tagline": sub_tagline,
        "steps": steps,
        "perks_html": perks_html,
        "hero_desc": hero_desc,
        "logo_html": logo_html,
        "about_desc": about_desc,
        "coverage_desc": coverage_desc,
        "about_title": about_title,
        "about_checklist": about_checklist,
        "coverage_title": coverage_title,
        "coverage_checklist": coverage_checklist,
        "year": 2026,
    }


def _page_shell(ctx: dict, body_html: str, extra_css: str = "") -> str:
    """Return a complete HTML page wrapping body_html with base CSS and JS."""
    p  = ctx["primary"];  pl = ctx["primary_light"]; ph = ctx["primary_hover"]
    navy = ctx["navy"];   ds = ctx["dark_slate"]
    ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    g50 = ctx["gray_50"]; bg = ctx["body_bg"]
    fh = ctx["font_heading"]; fb = ctx["font_body"]; fu = ctx["font_url"]
    company = ctx["company_name"]; city_state = ctx["city_state"]
    pr = _hex_to_rgb(p); nr = _hex_to_rgb(navy)

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        f"  <title>{company} \u2014 CDL-A Drivers | {city_state}</title>\n"
        f"  <meta name=\"description\" content=\"{company} is hiring CDL-A drivers in {city_state}. {ctx['routes_type']} — dry van freight.\">\n"
        "  <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
        "  <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
        f"  <link href=\"{fu}\" rel=\"stylesheet\">\n"
        "  <style>\n"
        "    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }\n"
        "    html { scroll-behavior: smooth; }\n"
        f"    :root {{\n"
        f"      --primary: {p}; --primary-light: {pl}; --primary-hover: {ph};\n"
        f"      --navy: {navy}; --dark-slate: {ds};\n"
        f"      --accent-bg: {ab}; --accent-bg-light: {abl};\n"
        f"      --gray-50: {g50}; --gray-100: #F1F5F9; --gray-200: #E2E8F0;\n"
        "      --gray-400: #94A3B8; --gray-500: #64748B; --gray-700: #334155;\n"
        "      --gray-900: #0F172A; --white: #FFFFFF;\n"
        f"      --body-bg: {bg};\n"
        "    }\n"
        f"    body {{ font-family: '{fb}', sans-serif; color: #334155; background: var(--body-bg); overflow-x: hidden; line-height: 1.65; }}\n"
        f"    h1, h2, h3, h4, h5 {{ font-family: '{fh}', sans-serif; line-height: 1.15; }}\n"
        "    a { text-decoration: none; color: inherit; }\n"
        "    img { max-width: 100%; display: block; object-fit: cover; }\n"
        "    ul { list-style: none; }\n"
        "    .reveal { opacity: 0; transform: translateY(32px); transition: opacity 0.65s ease-out, transform 0.65s ease-out; }\n"
        "    .reveal.show { opacity: 1; transform: translateY(0); }\n"
        "    .reveal-left { opacity: 0; transform: translateX(-32px); transition: opacity 0.65s ease-out, transform 0.65s ease-out; }\n"
        "    .reveal-left.show { opacity: 1; transform: translateX(0); }\n"
        "    .reveal-right { opacity: 0; transform: translateX(32px); transition: opacity 0.65s ease-out, transform 0.65s ease-out; }\n"
        "    .reveal-right.show { opacity: 1; transform: translateX(0); }\n"
        "    .delay-1 { transition-delay: 0.1s; } .delay-2 { transition-delay: 0.2s; }\n"
        "    .delay-3 { transition-delay: 0.3s; } .delay-4 { transition-delay: 0.4s; }\n"
        f"    .btn {{ display: inline-block; padding: 14px 34px; border-radius: 6px; font-family: '{fh}', sans-serif; font-weight: 700; font-size: 0.95rem; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; text-align: center; }}\n"
        f"    .btn-primary {{ background: var(--primary); color: #fff; border-color: var(--primary); }}\n"
        f"    .btn-primary:hover {{ background: var(--primary-hover); border-color: var(--primary-hover); transform: translateY(-2px); box-shadow: 0 8px 24px rgba({pr},0.35); }}\n"
        "    .btn-outline-light { background: transparent; color: #fff; border-color: rgba(255,255,255,0.35); }\n"
        "    .btn-outline-light:hover { border-color: var(--primary-light); color: var(--primary-light); }\n"
        "    .btn-outline-dark { background: transparent; color: var(--primary); border-color: var(--primary); }\n"
        "    .btn-outline-dark:hover { background: var(--primary); color: #fff; }\n"
        "    .section { padding: 96px 24px; }\n"
        "    .container { max-width: 1200px; margin: 0 auto; width: 100%; }\n"
        f"    .section-label {{ font-family: '{fh}', sans-serif; font-size: 0.73rem; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; color: var(--primary); margin-bottom: 10px; display: block; }}\n"
        "    .section-heading { font-size: clamp(1.8rem, 3.8vw, 2.6rem); font-weight: 900; color: var(--gray-900); margin-bottom: 14px; letter-spacing: -0.5px; }\n"
        "    .section-heading-light { color: #fff; }\n"
        "    .section-desc { font-size: 1.05rem; color: var(--gray-500); line-height: 1.72; max-width: 600px; }\n"
        "    .section-header-center { text-align: center; margin: 0 auto 60px; max-width: 640px; }\n"
        "    .accent { color: var(--primary-light); }\n"
        f"    #site-header {{ position: fixed; top: 0; width: 100%; z-index: 1000; background: rgba(255,255,255,0.96); backdrop-filter: blur(14px); border-bottom: 1px solid transparent; transition: border-color 0.3s, box-shadow 0.3s; height: 70px; }}\n"
        "    #site-header.scrolled { border-bottom-color: var(--gray-200); box-shadow: 0 2px 16px rgba(0,0,0,0.07); }\n"
        "    .nav-inner { max-width: 1200px; margin: 0 auto; padding: 0 28px; height: 100%; display: flex; align-items: center; justify-content: space-between; }\n"
        f"    .nav-logo {{ font-family: '{fh}', sans-serif; font-weight: 900; font-size: 1.45rem; color: var(--navy); letter-spacing: -0.5px; }}\n"
        "    .nav-logo span { color: var(--primary); }\n"
        "    .nav-links { display: flex; gap: 30px; align-items: center; }\n"
        "    .nav-links a { font-size: 0.875rem; font-weight: 600; color: var(--gray-500); transition: color 0.25s; }\n"
        "    .nav-links a:hover { color: var(--primary); }\n"
        "    .nav-apply { background: var(--primary) !important; color: #fff !important; padding: 9px 22px; border-radius: 6px; font-weight: 700 !important; }\n"
        "    .nav-apply:hover { background: var(--primary-hover) !important; }\n"
        "    .burger { display: none; cursor: pointer; flex-direction: column; gap: 5px; background: none; border: none; z-index: 1100; }\n"
        "    .burger span { display: block; width: 24px; height: 2px; background: var(--navy); border-radius: 2px; transition: all 0.3s; }\n"
        "    .burger.open span:nth-child(1) { transform: rotate(45deg) translate(5px,5px); }\n"
        "    .burger.open span:nth-child(2) { opacity: 0; }\n"
        "    .burger.open span:nth-child(3) { transform: rotate(-45deg) translate(5px,-5px); }\n"
        "    .mobile-menu { display: none; position: fixed; inset: 0; background: #fff; z-index: 999; flex-direction: column; align-items: center; justify-content: center; gap: 36px; }\n"
        "    .mobile-menu.open { display: flex; }\n"
        f"    .mobile-menu a {{ font-family: '{fh}', sans-serif; font-size: 1.5rem; font-weight: 800; color: var(--navy); transition: color 0.25s; }}\n"
        "    .mobile-menu a:hover { color: var(--primary); }\n"
        "    .perk { display: flex; align-items: center; gap: 10px; font-size: 0.93rem; line-height: 1.45; }\n"
        "    .perk::before { content: ''; width: 7px; height: 7px; border-radius: 50%; background: var(--primary-light); flex-shrink: 0; }\n"
        "    .stat-card { border-radius: 10px; padding: 24px 18px; text-align: center; transition: transform 0.3s; }\n"
        "    .stat-card:hover { transform: translateY(-4px); }\n"
        f"    .stat-card-val {{ font-family: '{fh}', sans-serif; font-size: 1.3rem; font-weight: 900; margin-bottom: 4px; }}\n"
        "    .stat-card-lbl { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }\n"
        "    .check-list { display: flex; flex-direction: column; gap: 13px; }\n"
        "    .check-item { display: flex; align-items: flex-start; gap: 12px; font-size: 0.95rem; color: var(--gray-700); font-weight: 500; }\n"
        "    .check-dot { width: 22px; height: 22px; border-radius: 6px; background: var(--accent-bg); color: var(--primary); display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 900; flex-shrink: 0; margin-top: 1px; }\n"
        "    .field { margin-bottom: 14px; }\n"
        "    .field label { display: block; font-size: 0.8rem; font-weight: 700; color: var(--gray-700); margin-bottom: 5px; }\n"
        f"    .field input, .field textarea, .field select {{ width: 100%; padding: 11px 14px; border: 1px solid var(--gray-200); border-radius: 6px; font-family: '{fb}', sans-serif; font-size: 0.93rem; color: var(--gray-700); background: var(--gray-50); outline: none; transition: border-color 0.25s; }}\n"
        "    .field input:focus, .field textarea:focus, .field select:focus { border-color: var(--primary); }\n"
        "    .field textarea { resize: vertical; min-height: 88px; }\n"
        "    .field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }\n"
        "    .eeo-text { font-size: 0.77rem; color: rgba(255,255,255,0.25); line-height: 1.65; text-align: center; max-width: 700px; margin: 28px auto 0; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.07); }\n"
        "    .eeo-text-dark { font-size: 0.77rem; color: var(--gray-400); line-height: 1.65; text-align: center; max-width: 700px; margin: 28px auto 0; padding-top: 24px; border-top: 1px solid var(--gray-200); }\n"
        "    @keyframes pulse-dot { 0%,100%{ opacity:1; } 50%{ opacity:0.35; } }\n"
        "    @media (max-width: 900px) { .nav-links { display: none; } .burger { display: flex; } .section { padding: 72px 20px; } .field-row { grid-template-columns: 1fr; } }\n"
        "    @media (max-width: 600px) { .section { padding: 60px 16px; } }\n"
        + (f"    {extra_css}\n" if extra_css else "")
        + "  </style>\n"
        "</head>\n"
        "<body>\n"
        + body_html
        + "  <script>\n"
        "    const hdr = document.getElementById('site-header');\n"
        "    if (hdr) window.addEventListener('scroll', () => hdr.classList.toggle('scrolled', window.scrollY > 40));\n"
        "    const burger = document.getElementById('blk-burger');\n"
        "    const mob = document.getElementById('blk-mob-menu');\n"
        "    function blkToggle() {\n"
        "      if (!burger || !mob) return;\n"
        "      burger.classList.toggle('open'); mob.classList.toggle('open');\n"
        "      document.body.style.overflow = mob.classList.contains('open') ? 'hidden' : '';\n"
        "    }\n"
        "    if (burger) burger.addEventListener('click', blkToggle);\n"
        "    document.querySelectorAll('.blk-mob-link').forEach(a => a.addEventListener('click', blkToggle));\n"
        "    const revObs = new IntersectionObserver(entries => {\n"
        "      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('show'); });\n"
        "    }, { threshold: 0.1 });\n"
        "    document.querySelectorAll('.reveal, .reveal-left, .reveal-right').forEach(el => revObs.observe(el));\n"
        "    document.querySelectorAll('form[data-blk-form]').forEach(f => {\n"
        "      f.addEventListener('submit', e => { e.preventDefault(); alert(\"Thanks! We'll be in touch soon.\"); e.target.reset(); });\n"
        "    });\n"
        "  </script>\n"
        "</body>\n"
        "</html>"
    )


# ── NAV & FOOTER ──────────────────────────────────────────────────────────────

def _nav(ctx: dict) -> str:
    return (
        "  <header id=\"site-header\">\n"
        "    <div class=\"nav-inner\">\n"
        f"      <a href=\"#\" class=\"nav-logo\">{ctx['logo_html']}</a>\n"
        "      <nav class=\"nav-links\">\n"
        "        <a href=\"#about\">About</a>\n"
        "        <a href=\"#careers\">Careers</a>\n"
        "        <a href=\"#contact\">Contact</a>\n"
        "        <a href=\"#careers\" class=\"nav-apply\">Apply Now</a>\n"
        "      </nav>\n"
        "      <button class=\"burger\" id=\"blk-burger\" aria-label=\"Toggle menu\">\n"
        "        <span></span><span></span><span></span>\n"
        "      </button>\n"
        "    </div>\n"
        "  </header>\n"
        "  <div class=\"mobile-menu\" id=\"blk-mob-menu\">\n"
        "    <a href=\"#\" class=\"blk-mob-link\">Home</a>\n"
        "    <a href=\"#about\" class=\"blk-mob-link\">About</a>\n"
        "    <a href=\"#careers\" class=\"blk-mob-link\">Careers</a>\n"
        "    <a href=\"#contact\" class=\"blk-mob-link\">Contact</a>\n"
        "  </div>\n"
    )


def _footer(ctx: dict) -> str:
    fh = ctx["font_heading"]
    p  = ctx["primary"]
    navy = ctx["navy"]
    company = ctx["company_name"]
    email = ctx["email"]
    address = ctx["address"]
    city_state = ctx["city_state"]
    _addr = f"{address}<br>{city_state}" if address else city_state
    year = ctx["year"]
    logo = ctx["logo_html"]
    return (
        f"  <footer style=\"background:{navy}; padding:52px 24px 28px; color:#94A3B8;\">\n"
        "    <div style=\"max-width:1200px; margin:0 auto;\">\n"
        "      <div style=\"display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:32px; margin-bottom:40px;\">\n"
        "        <div>\n"
        f"          <div style=\"font-family:'{fh}',sans-serif; font-weight:900; font-size:1.5rem; color:#fff; margin-bottom:10px;\">{logo}</div>\n"
        f"          <p style=\"font-size:0.88rem; max-width:280px; line-height:1.6; color:#94A3B8;\">Professional CDL-A carrier serving {ctx['routes'].lower()} from {city_state}.</p>\n"
        "        </div>\n"
        "        <div style=\"display:flex; gap:48px; flex-wrap:wrap;\">\n"
        "          <div>\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{p}; margin-bottom:14px;\">Company</div>\n"
        "            <div style=\"display:flex; flex-direction:column; gap:10px;\">\n"
        f"              <a href=\"#about\" style=\"font-size:0.88rem; color:#94A3B8;\" onmouseover=\"this.style.color='{p}'\" onmouseout=\"this.style.color='#94A3B8'\">About Us</a>\n"
        f"              <a href=\"#careers\" style=\"font-size:0.88rem; color:#94A3B8;\" onmouseover=\"this.style.color='{p}'\" onmouseout=\"this.style.color='#94A3B8'\">Careers</a>\n"
        f"              <a href=\"#contact\" style=\"font-size:0.88rem; color:#94A3B8;\" onmouseover=\"this.style.color='{p}'\" onmouseout=\"this.style.color='#94A3B8'\">Contact</a>\n"
        "            </div>\n"
        "          </div>\n"
        "          <div>\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{p}; margin-bottom:14px;\">Contact</div>\n"
        "            <div style=\"display:flex; flex-direction:column; gap:10px;\">\n"
        f"              <span style=\"font-size:0.88rem; color:#94A3B8;\">{email}</span>\n"
        f"              <span style=\"font-size:0.88rem; color:#94A3B8;\">{_addr}</span>\n"
        "              <span style=\"font-size:0.88rem; color:#94A3B8;\">Dispatch: 24/7</span>\n"
        "            </div>\n"
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        "      <div style=\"border-top:1px solid rgba(255,255,255,0.07); padding-top:22px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;\">\n"
        f"        <span style=\"font-size:0.78rem; color:rgba(255,255,255,0.22);\">&copy; {year} {company}. All rights reserved.</span>\n"
        "        <span style=\"font-size:0.78rem; color:rgba(255,255,255,0.22);\">Equal Opportunity Employer</span>\n"
        "      </div>\n"
        "    </div>\n"
        "  </footer>\n"
    )


def _checklist_html(items):
    return "".join(
        f"<li class=\"check-item\"><span class=\"check-dot\">&#10003;</span> {item}</li>"
        for item in items
    )


def _stat_cards_dark(ctx: dict) -> str:
    """4 stat cards styled for dark background."""
    p = ctx["primary"]; pl = ctx["primary_light"]; fh = ctx["font_heading"]
    items = [
        (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
        (ctx["home_time_short"], ctx["home_time_detail"]),
        (ctx["routes"], ctx["routes_type"]),
        (ctx["fourth_card_value"], ctx["fourth_card_label"]),
    ]
    return "".join(
        f"<div class=\"stat-card\" style=\"background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);\">"
        f"<div class=\"stat-card-val\" style=\"color:{pl};\">{val}</div>"
        f"<div class=\"stat-card-lbl\" style=\"color:rgba(255,255,255,0.4);\">{lbl}</div></div>"
        for val, lbl in items
    )


def _stat_cards_light(ctx: dict) -> str:
    """4 stat cards styled for light background."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]; fh = ctx["font_heading"]
    items = [
        (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
        (ctx["home_time_short"], ctx["home_time_detail"]),
        (ctx["routes"], ctx["routes_type"]),
        (ctx["fourth_card_value"], ctx["fourth_card_label"]),
    ]
    return "".join(
        f"<div class=\"stat-card\" style=\"background:{abl}; border:1px solid {ab}; border-top:3px solid {p};\">"
        f"<div class=\"stat-card-val\" style=\"color:{p};\">{val}</div>"
        f"<div class=\"stat-card-lbl\" style=\"color:#64748B;\">{lbl}</div></div>"
        for val, lbl in items
    )


# ── HERO VARIANTS ─────────────────────────────────────────────────────

def _hero_v1(ctx: dict) -> str:
    """Route-ticker hero: dark bg, headline, horizontal ticker strip of fake lane pairs."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; ds = ctx["dark_slate"]
    fh = ctx["font_heading"]; fb = ctx["font_body"]
    nr = _hex_to_rgb(navy); pr = _hex_to_rgb(p)
    company = ctx["company_name"]
    lanes = "CHI \u2192 DAL\u2002\u00b7\u2002ATL \u2192 LAX\u2002\u00b7\u2002MIA \u2192 NYC\u2002\u00b7\u2002DEN \u2192 SEA\u2002\u00b7\u2002HOU \u2192 PHX\u2002\u00b7\u2002DTW \u2192 STL\u2002\u00b7\u2002CLT \u2192 BOS\u2002\u00b7\u2002PHL \u2192 MEM"
    return (
        f"  <section style=\"position:relative; min-height:100vh; display:flex; flex-direction:column;"
        f" align-items:center; justify-content:center; padding:140px 24px 60px; text-align:center;"
        f" background:url('images/{ctx['hero_img']}') center/cover no-repeat;\">\n"
        f"    <div style=\"position:absolute; inset:0; background:linear-gradient(180deg,rgba({nr},0.93) 0%,rgba({nr},0.80) 100%);\"></div>\n"
        "    <div style=\"position:relative; z-index:1; max-width:860px; width:100%; flex:1; display:flex; flex-direction:column; justify-content:center;\">\n"
        f"      <div class=\"reveal\" style=\"display:inline-flex; gap:8px; align-items:center; justify-content:center;"
        f" background:rgba({pr},0.18); border:1px solid rgba({pr},0.4); color:{pl};"
        " font-size:0.72rem; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:6px 20px; border-radius:50px; margin-bottom:28px;\">"
        "\U0001f4f5\u2002DISPATCH LIVE\n"
        "      </div>\n"
        f"      <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.6rem,5.5vw,4.6rem);"
        " font-weight:900; color:#fff; line-height:1.06; margin-bottom:20px; letter-spacing:-1.5px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"      <p class=\"reveal delay-1\" style=\"font-size:1.1rem; color:rgba(255,255,255,0.6); max-width:540px;"
        f" margin:0 auto 36px; line-height:1.72;\">{ctx['hero_desc']}</p>\n"
        "      <div class=\"reveal delay-2\" style=\"display:flex; gap:14px; justify-content:center; flex-wrap:wrap;\">\n"
        "        <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        "        <a href=\"#contact\" class=\"btn btn-outline-light\">Get a Quote</a>\n"
        "      </div>\n"
        "    </div>\n"
        "    <div style=\"position:relative; z-index:1; width:100%; overflow:hidden;"
        f" border-top:1px solid rgba({pr},0.25); padding:16px 0; background:rgba(0,0,0,0.35);\">\n"
        f"      <p style=\"font-family:'Courier New',monospace; font-size:0.78rem; font-weight:700; color:{pl};"
        " letter-spacing:1px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; text-align:center; margin:0;\">"
        f"\U0001f6e3\ufe0f\u2002ACTIVE LANES:\u2002{lanes}</p>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v2(ctx: dict) -> str:
    """Diagonal clip-path split: dark-left copy panel + right truck image."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    nr = _hex_to_rgb(navy); pr = _hex_to_rgb(p)
    pay_val = ctx["pay_range"].split("/")[0].strip()
    return (
        "  <section style=\"position:relative; min-height:100vh; display:flex; padding-top:70px; overflow:hidden;\">\n"
        f"    <div style=\"position:relative; z-index:2; width:55%; background:{navy};"
        " clip-path:polygon(0 0,100% 0,88% 100%,0 100%); padding:100px 80px 80px 48px;"
        " display:flex; align-items:center;\">\n"
        "      <div style=\"max-width:480px;\">\n"
        f"        <div class=\"reveal\" style=\"font-size:0.72rem; font-weight:700; letter-spacing:3px;"
        f" text-transform:uppercase; color:{pl}; margin-bottom:16px;\">\U0001f69a CDL-A · Now Hiring</div>\n"
        f"        <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.4rem,4vw,3.8rem);"
        " font-weight:900; color:#fff; line-height:1.07; margin-bottom:20px; letter-spacing:-1px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"        <p class=\"reveal delay-1\" style=\"font-size:1.02rem; color:rgba(255,255,255,0.58);"
        f" margin-bottom:32px; line-height:1.72; max-width:420px;\">{ctx['hero_desc']}</p>\n"
        "        <div class=\"reveal delay-2\" style=\"display:flex; gap:14px; flex-wrap:wrap;\">\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        "          <a href=\"#about\" class=\"btn btn-outline-light\">About Us</a>\n"
        "        </div>\n"
        f"        <div class=\"reveal delay-3\" style=\"margin-top:44px; display:flex; gap:32px; flex-wrap:wrap;\">\n"
        f"          <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.7rem; font-weight:900; color:{pl};\">{pay_val}</div>"
        "<div style=\"font-size:0.75rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-top:3px;\">Weekly Pay</div></div>\n"
        f"          <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.7rem; font-weight:900; color:{pl};\">{ctx['home_time_short']}</div>"
        "<div style=\"font-size:0.75rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-top:3px;\">Home Time</div></div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        f"    <div style=\"position:absolute; right:0; top:0; bottom:0; width:55%;"
        f" background:url('images/{ctx['hero_img']}') center/cover no-repeat;\"></div>\n"
        "  </section>\n"
    )


def _hero_v3(ctx: dict) -> str:
    """Pay-centered hero: huge pay number as visual anchor, truck image right, minimal copy."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    nr = _hex_to_rgb(navy)
    pay_val = ctx["pay_range"].split("/")[0].strip()
    return (
        f"  <section style=\"background:{navy}; min-height:100vh; display:flex; align-items:center;"
        " padding:120px 24px 80px; overflow:hidden;\">\n"
        "    <div style=\"max-width:1200px; margin:0 auto; width:100%; display:grid;"
        " grid-template-columns:1fr 1fr; gap:48px; align-items:center;\">\n"
        "      <div class=\"reveal-left\">\n"
        f"        <div style=\"font-size:0.72rem; font-weight:700; letter-spacing:3px;"
        f" text-transform:uppercase; color:{pl}; margin-bottom:14px;\">CDL-A &middot; {ctx['routes_type']}</div>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:clamp(4rem,9vw,8rem);"
        f" font-weight:900; color:{pl}; line-height:0.9; letter-spacing:-4px; margin-bottom:6px;\">{pay_val}</div>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.05rem; font-weight:700;"
        f" color:rgba(255,255,255,0.5); margin-bottom:28px;\">Per Week &middot; {ctx['routes']}</div>\n"
        f"        <h2 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.4rem,2.5vw,2rem);"
        f" font-weight:800; color:#fff; line-height:1.2; margin-bottom:18px;\">{ctx['tagline']}</h2>\n"
        f"        <p class=\"reveal delay-1\" style=\"font-size:0.98rem; color:rgba(255,255,255,0.52);"
        f" margin-bottom:32px; line-height:1.72; max-width:440px;\">{ctx['hero_desc']}</p>\n"
        "        <div class=\"reveal delay-2\" style=\"display:flex; gap:14px; flex-wrap:wrap;\">\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\" style=\"padding:14px 36px;\">Apply Today</a>\n"
        "        </div>\n"
        "      </div>\n"
        "      <div class=\"reveal-right\" style=\"border-radius:16px; overflow:hidden; box-shadow:0 32px 80px rgba(0,0,0,0.5);\">\n"
        f"        <img src=\"images/{ctx['hero_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:520px; object-fit:cover; display:block;\">\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v4(ctx: dict) -> str:
    """Blueprint/specs style: grid-paper SVG bg, stenciled headline, spec readout."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    pr = _hex_to_rgb(p)
    pay_val = ctx["pay_range"].split("/")[0].strip()
    specs = [
        ("FLEET TYPE", ctx["routes_type"]),
        ("LANES", ctx["routes"]),
        ("HOME TIME", ctx["home_time_short"]),
        ("MIN EXP", ctx["min_experience"]),
        ("PAY RATE", pay_val + "/WK"),
        ("DISPATCH", "24 / 7"),
    ]
    spec_html = "".join(
        f"<div style=\"border:1px solid rgba({pr},0.35); border-radius:4px; padding:12px 16px;\">"
        f"<div style=\"font-size:0.62rem; letter-spacing:2px; color:rgba(255,255,255,0.38); margin-bottom:4px;\">{k}</div>"
        f"<div style=\"font-family:'Courier New',monospace; font-size:0.92rem; font-weight:700; color:{pl};\">{v}</div>"
        "</div>"
        for k, v in specs
    )
    return (
        f"  <section style=\"position:relative; min-height:100vh; display:flex; align-items:center;"
        f" padding:140px 24px 80px; background:{navy}; overflow:hidden;\">\n"
        "    <!-- Blueprint grid SVG -->\n"
        f"    <svg style=\"position:absolute; inset:0; width:100%; height:100%; opacity:0.07;\" xmlns=\"http://www.w3.org/2000/svg\">"
        "<defs><pattern id=\"bgrid\" width=\"40\" height=\"40\" patternUnits=\"userSpaceOnUse\">"
        f"<path d=\"M 40 0 L 0 0 0 40\" fill=\"none\" stroke=\"{pl}\" stroke-width=\"0.5\"/></pattern></defs>"
        "<rect width=\"100%\" height=\"100%\" fill=\"url(#bgrid)\"/></svg>\n"
        "    <div style=\"position:relative; z-index:1; max-width:1000px; margin:0 auto; width:100%;\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:64px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        f"          <div style=\"font-family:'Courier New',monospace; font-size:0.68rem; font-weight:700;"
        f" letter-spacing:3px; color:{pl}; margin-bottom:20px;\">// SPEC SHEET &middot; {ctx['company_short']}</div>\n"
        f"          <h1 style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.6rem,5vw,4.2rem);"
        " font-weight:900; color:#fff; line-height:1.07; letter-spacing:-1px; margin-bottom:20px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"          <p style=\"font-size:1rem; color:rgba(255,255,255,0.55); margin-bottom:32px; line-height:1.72;\">{ctx['hero_desc']}</p>\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">View Open Positions</a>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\">\n"
        f"          <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:12px;\">{spec_html}</div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v5(ctx: dict) -> str:
    """Magazine-cover style: oversized number, bold headline, corner stamps, truck image strip."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    pr = _hex_to_rgb(p); nr = _hex_to_rgb(navy)
    company = ctx["company_name"]
    year = ctx["year"]
    return (
        f"  <section style=\"background:{navy}; min-height:100vh; padding:120px 24px 0; overflow:hidden;\">\n"
        "    <div style=\"max-width:1200px; margin:0 auto;\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:32px; align-items:flex-end;\">\n"
        "        <div>\n"
        f"          <div class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(7rem,15vw,13rem);"
        " font-weight:900; line-height:0.85; color:transparent; -webkit-text-stroke:2px rgba(255,255,255,0.08);"
        f" margin-bottom:-16px; letter-spacing:-6px; user-select:none;\">{year}</div>\n"
        f"          <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.4rem,4.5vw,3.6rem);"
        " font-weight:900; color:#fff; line-height:1.06; margin-bottom:18px; letter-spacing:-1px;"
        f" position:relative; z-index:1;\">{ctx['tagline']}</h1>\n"
        f"          <p class=\"reveal delay-1\" style=\"font-size:1rem; color:rgba(255,255,255,0.55);"
        f" margin-bottom:28px; line-height:1.72; max-width:480px;\">{ctx['hero_desc']}</p>\n"
        "          <div class=\"reveal delay-2\" style=\"display:flex; gap:12px; flex-wrap:wrap; align-items:center;\">\n"
        "            <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        f"            <span style=\"background:{p}; color:#fff; font-family:'{fh}',sans-serif; font-size:0.68rem;"
        " font-weight:800; letter-spacing:2px; text-transform:uppercase; padding:6px 14px; border-radius:4px;\">\U00002605 CDL-A</span>\n"
        f"            <span style=\"border:2px solid rgba(255,255,255,0.2); color:rgba(255,255,255,0.6); font-family:'{fh}',sans-serif; font-size:0.68rem;"
        f" font-weight:800; letter-spacing:2px; text-transform:uppercase; padding:5px 14px; border-radius:4px;\">{ctx['routes']}</span>\n"
        "          </div>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\" style=\"border-radius:16px 16px 0 0; overflow:hidden; margin-top:32px;\">\n"
        f"          <img src=\"images/{ctx['hero_img']}\" alt=\"{company}\" style=\"width:100%; height:480px; object-fit:cover; display:block;\">\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── PROCESS VARIANTS ──────────────────────────────────────────────────

def _process_v1(ctx: dict) -> str:
    """Before/After comparison table: without-us (X) vs. with-us (check) columns."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    rows = [
        ("Real-time load tracking", False, True),
        ("24/7 dispatch coverage", False, True),
        ("On-time delivery — every load", False, True),
        ("No-touch dry van freight", False, True),
        ("Transparent communication", False, True),
        ("Professional, vetted drivers", False, True),
    ]
    row_html = "".join(
        f"<tr style=\"border-bottom:1px solid #E2E8F0;\">"
        f"<td style=\"padding:14px 20px; font-size:0.92rem; color:#334155;\">{label}</td>"
        f"<td style=\"padding:14px 20px; text-align:center; font-size:1.1rem;\">"
        f"{'<span style=\"color:#EF4444;\">&#10007;</span>' if not without else '<span style=\"color:#22C55E;\">&#10003;</span>'}"
        f"</td>"
        f"<td style=\"padding:14px 20px; text-align:center; font-size:1.1rem;\">"
        f"{'<span style=\"color:#22C55E;\">&#10003;</span>' if with_us else '<span style=\"color:#EF4444;\">&#10007;</span>'}"
        f"</td>"
        "</tr>"
        for label, without, with_us in rows
    )
    return (
        f"  <section class=\"section\" style=\"background:{abl};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        "          <span class=\"section-label\">Why Us</span>\n"
        f"          <h2 class=\"section-heading\">The Difference Is Real</h2>\n"
        "          <p class=\"section-desc\" style=\"margin-top:12px;\">Not all carriers are built the same. See what sets us apart from the typical freight operation.</p>\n"
        "          <a href=\"#contact\" class=\"btn btn-primary\" style=\"margin-top:28px; display:inline-block;\">Get a Quote</a>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\" style=\"overflow:hidden; border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,0.08);\">\n"
        "          <table style=\"width:100%; border-collapse:collapse; background:#fff;\">\n"
        "            <thead>\n"
        f"              <tr style=\"background:{navy};\">\n"
        f"                <th style=\"padding:16px 20px; text-align:left; font-family:'{fh}',sans-serif; font-size:0.8rem; font-weight:700; color:rgba(255,255,255,0.6); letter-spacing:1px; text-transform:uppercase;\">Feature</th>\n"
        f"                <th style=\"padding:16px 20px; text-align:center; font-family:'{fh}',sans-serif; font-size:0.8rem; font-weight:700; color:rgba(255,255,255,0.4); letter-spacing:1px; text-transform:uppercase;\">Others</th>\n"
        f"                <th style=\"padding:16px 20px; text-align:center; font-family:'{fh}',sans-serif; font-size:0.8rem; font-weight:700; color:{ctx['primary_light']}; letter-spacing:1px; text-transform:uppercase;\">Us</th>\n"
        "              </tr>\n"
        "            </thead>\n"
        f"            <tbody>{row_html}</tbody>\n"
        "          </table>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v2(ctx: dict) -> str:
    """Stacked numbered rows with a key-metric on the right per step."""
    p = ctx["primary"]; abl = ctx["accent_bg_light"]; ab = ctx["accent_bg"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    metrics = ["&lt; 24h", "&lt; 1h", "100%"]
    metric_labels = ["Response Time", "Dispatch", "On-Time Rate"]
    rows = ""
    for i, (title, desc) in enumerate(steps, 1):
        metric = metrics[(i - 1) % len(metrics)]
        mlabel = metric_labels[(i - 1) % len(metric_labels)]
        rows += (
            f"        <div class=\"reveal\" style=\"display:flex; align-items:center; gap:0;"
            " background:#fff; border:1px solid #E2E8F0; border-radius:12px; overflow:hidden;"
            " transition:box-shadow 0.3s;\""
            " onmouseover=\"this.style.boxShadow='0 8px 28px rgba(0,0,0,0.07)'\""
            " onmouseout=\"this.style.boxShadow=''\">\n"
            f"          <div style=\"background:{abl}; padding:36px 28px; min-width:72px; text-align:center; flex-shrink:0; align-self:stretch; display:flex; align-items:center; justify-content:center;\">\n"
            f"            <span style=\"font-family:'{fh}',sans-serif; font-size:2.8rem; font-weight:900; color:{p}; line-height:1;\">0{i}</span>\n"
            "          </div>\n"
            "          <div style=\"flex:1; padding:28px 32px;\">\n"
            f"            <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.15rem; font-weight:800; color:{navy}; margin-bottom:8px;\">{title}</h3>\n"
            f"            <p style=\"font-size:0.92rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "          </div>\n"
            f"          <div style=\"background:{ab}; padding:28px 32px; text-align:center; flex-shrink:0; min-width:110px; align-self:stretch; display:flex; flex-direction:column; align-items:center; justify-content:center;\">\n"
            f"            <div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:{p}; margin-bottom:4px;\">{metric}</div>\n"
            f"            <div style=\"font-size:0.7rem; color:#64748B; text-transform:uppercase; letter-spacing:1px;\">{mlabel}</div>\n"
            "          </div>\n"
            "        </div>\n"
        )
    return (
        "  <section class=\"section\" style=\"background:#fff;\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">Our Process</span>\n"
        "        <h2 class=\"section-heading\">How We Deliver Every Time</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">Simple, accountable, measurable. Three steps we execute without fail.</p>\n"
        "      </div>\n"
        "      <div style=\"display:flex; flex-direction:column; gap:16px; max-width:960px; margin:0 auto;\">\n"
        + rows
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v3(ctx: dict) -> str:
    """Photo-accent cards: each step card has a thin truck-image strip across the top."""
    p = ctx["primary"]; ab = ctx["accent_bg"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    images = [ctx["hero_img"], ctx["about_img"], ctx["coverage_img"]]
    icons = ["\U0001f4cb", "\U0001f69a", "\u2705"]
    cards = ""
    for i, (title, desc) in enumerate(steps, 1):
        img = images[(i - 1) % len(images)]
        icon = icons[(i - 1) % len(icons)]
        cards += (
            f"        <div class=\"reveal delay-{i}\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px;"
            " overflow:hidden; transition:transform 0.3s,box-shadow 0.3s;\""
            " onmouseover=\"this.style.transform='translateY(-5px)';this.style.boxShadow='0 12px 36px rgba(0,0,0,0.1)'\""
            " onmouseout=\"this.style.transform='';this.style.boxShadow=''\">\n"
            f"          <div style=\"height:100px; background:url('images/{img}') center/cover no-repeat; position:relative;\">\n"
            f"            <div style=\"position:absolute; inset:0; background:rgba(0,0,0,0.45);\"></div>\n"
            f"            <div style=\"position:absolute; bottom:12px; left:16px; font-size:1.6rem;\">{icon}</div>\n"
            f"            <div style=\"position:absolute; bottom:12px; right:16px; font-family:'{fh}',sans-serif;"
            f" font-size:1.5rem; font-weight:900; color:rgba(255,255,255,0.15); line-height:1;\">0{i}</div>\n"
            "          </div>\n"
            "          <div style=\"padding:28px 28px;\">\n"
            f"            <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.15rem; font-weight:800; color:{navy}; margin-bottom:10px;\">{title}</h3>\n"
            f"            <p style=\"font-size:0.92rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "          </div>\n"
            "        </div>\n"
        )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">How We Work</span>\n"
        "        <h2 class=\"section-heading\">From Booking to Delivery</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">Three steps, zero confusion. Here's exactly what to expect when you haul with us.</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:24px;\">\n"
        + cards
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v4(ctx: dict) -> str:
    """Highway road SVG with 3 pin-style milestones along a curved line."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    pr = _hex_to_rgb(p)
    step_items = ""
    pct = [20, 50, 80]
    for i, (title, desc) in enumerate(steps, 1):
        left = pct[(i - 1) % len(pct)]
        step_items += (
            f"      <div class=\"reveal\" style=\"position:absolute; left:{left}%; top:50%; transform:translate(-50%,-50%); text-align:center; width:200px;\">\n"
            f"        <div style=\"width:48px; height:48px; border-radius:50%; background:{p}; color:#fff;"
            f" display:flex; align-items:center; justify-content:center; font-family:'{fh}',sans-serif;"
            " font-size:1.1rem; font-weight:900; margin:0 auto 12px; box-shadow:0 4px 16px rgba(0,0,0,0.25);\">0{i}</div>\n"
            f"        <div style=\"font-family:'{fh}',sans-serif; font-size:0.92rem; font-weight:800; color:{navy}; margin-bottom:4px;\">{title}</div>\n"
            f"        <div style=\"font-size:0.8rem; color:#64748B; line-height:1.55;\">{desc[:60]}...</div>\n"
            "      </div>\n"
        )
    return (
        "  <section class=\"section\" style=\"background:#fff;\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:48px;\">\n"
        "        <span class=\"section-label\">The Journey</span>\n"
        "        <h2 class=\"section-heading\">Your Load's Path to Delivery</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">Every shipment follows the same proven route from first call to final drop.</p>\n"
        "      </div>\n"
        "      <!-- Road diagram -->\n"
        "      <div style=\"position:relative; height:260px; margin:0 auto; max-width:960px;\">\n"
        "        <svg style=\"position:absolute; inset:0; width:100%; height:100%;\" viewBox=\"0 0 960 260\" preserveAspectRatio=\"none\" xmlns=\"http://www.w3.org/2000/svg\">\n"
        "          <path d=\"M 0 180 Q 240 60 480 130 Q 720 200 960 80\" fill=\"none\" stroke=\"#E2E8F0\" stroke-width=\"12\" stroke-linecap=\"round\"/>\n"
        f"          <path d=\"M 0 180 Q 240 60 480 130 Q 720 200 960 80\" fill=\"none\" stroke=\"{p}\" stroke-width=\"4\" stroke-linecap=\"round\" stroke-dasharray=\"12 8\"/>\n"
        "        </svg>\n"
        + step_items
        + "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:24px; max-width:960px; margin:24px auto 0;\">\n"
        + "".join(
            f"        <div class=\"reveal delay-{i}\" style=\"padding:28px; border-left:3px solid {p}; background:{ctx['accent_bg_light']};\">\n"
            f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1rem; font-weight:800; color:{navy}; margin-bottom:8px;\">{title}</h3>\n"
            f"          <p style=\"font-size:0.9rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "        </div>\n"
            for i, (title, desc) in enumerate(steps, 1)
        )
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v5(ctx: dict) -> str:
    """Quote/testimonial per step: each step framed as a driver quote in a speech bubble."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    pr = _hex_to_rgb(p)
    driver_names = ["Mike R., Driver", "Carlos T., Driver", "James W., Driver"]
    cards = ""
    for i, (title, desc) in enumerate(steps, 1):
        name = driver_names[(i - 1) % len(driver_names)]
        cards += (
            f"        <div class=\"reveal delay-{i}\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:16px;"
            " padding:36px 32px; position:relative; transition:box-shadow 0.3s;\""
            f" onmouseover=\"this.style.boxShadow='0 10px 32px rgba({pr},0.1)'\""
            " onmouseout=\"this.style.boxShadow=''\">\n"
            f"          <div style=\"font-size:3rem; color:{p}; line-height:1; margin-bottom:12px; font-family:Georgia,serif;\">&ldquo;</div>\n"
            f"          <p style=\"font-size:0.96rem; color:#334155; line-height:1.72; margin-bottom:20px; font-style:italic;\">{desc}</p>\n"
            f"          <div style=\"border-top:1px solid #E2E8F0; padding-top:16px; display:flex; align-items:center; justify-content:space-between;\">\n"
            f"            <div style=\"font-family:'{fh}',sans-serif; font-size:0.88rem; font-weight:700; color:{navy};\">{title}</div>\n"
            f"            <div style=\"font-size:0.78rem; color:#94A3B8;\">{name}</div>\n"
            "          </div>\n"
            "        </div>\n"
        )
    return (
        f"  <section class=\"section\" style=\"background:{ctx['gray_50']};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">The Process</span>\n"
        "        <h2 class=\"section-heading\">Drivers Know. Here's the Story.</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">From first call to final delivery, our process speaks for itself.</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:24px;\">\n"
        + cards
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── ABOUT VARIANTS ────────────────────────────────────────────────────

def _about_v1(ctx: dict) -> str:
    """Stats overlay on full-width truck image: semi-transparent panels over the photo."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    nr = _hex_to_rgb(navy)
    _is_regional = "regional" in ctx.get("routes_type", "OTR Routes").lower()
    coverage_val = "Multi-State" if _is_regional else "48 States"
    stats = [
        (coverage_val, "Coverage"),
        ("24/7", "Dispatch"),
        ("CDL-A", "Drivers"),
        ("100%", "No-Touch"),
    ]
    stat_panels = "".join(
        f"<div style=\"background:rgba({nr},0.82); border:1px solid rgba(255,255,255,0.1);"
        " border-radius:10px; padding:20px 24px; text-align:center;\">"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.6rem; font-weight:900; color:{pl}; margin-bottom:4px;\">{val}</div>"
        f"<div style=\"font-size:0.72rem; color:rgba(255,255,255,0.5); text-transform:uppercase; letter-spacing:1px;\">{lbl}</div>"
        "</div>"
        for val, lbl in stats
    )
    return (
        "  <section style=\"position:relative; overflow:hidden;\" id=\"about\">\n"
        f"    <img src=\"images/{ctx['about_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:560px; object-fit:cover; display:block;\">\n"
        f"    <div style=\"position:absolute; inset:0; background:linear-gradient(90deg,rgba({nr},0.75) 0%,rgba({nr},0.25) 60%,transparent 100%);\"></div>\n"
        "    <div style=\"position:absolute; inset:0; display:flex; align-items:center; padding:0 48px;\">\n"
        "      <div class=\"reveal-left\" style=\"max-width:480px;\">\n"
        "        <span class=\"section-label\">About Us</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.8rem,3.5vw,2.8rem);"
        " font-weight:900; color:#fff; line-height:1.1; margin-bottom:16px;\">"
        f"{ctx['about_title']}</h2>\n"
        f"        <p style=\"font-size:0.97rem; color:rgba(255,255,255,0.65); line-height:1.72; margin-bottom:28px;\">{ctx['about_desc']}</p>\n"
        "        <a href=\"#careers\" class=\"btn btn-primary\">Join Our Team</a>\n"
        "      </div>\n"
        "    </div>\n"
        f"    <div class=\"reveal\" style=\"position:absolute; bottom:24px; right:32px;"
        f" display:grid; grid-template-columns:repeat(4,1fr); gap:12px; max-width:560px;\">{stat_panels}</div>\n"
        "  </section>\n"
    )


def _about_v2(ctx: dict) -> str:
    """Centered pull-quote layout: about_title as blockquote, about_img as full background."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    nr = _hex_to_rgb(navy)
    return (
        f"  <section style=\"position:relative; padding:120px 24px;\" id=\"about\">\n"
        f"    <div style=\"position:absolute; inset:0; background:url('images/{ctx['about_img']}') center/cover no-repeat;\"></div>\n"
        f"    <div style=\"position:absolute; inset:0; background:rgba({nr},0.88);\"></div>\n"
        "    <div style=\"position:relative; z-index:1; max-width:820px; margin:0 auto; text-align:center;\">\n"
        "      <div class=\"reveal\">\n"
        "        <span class=\"section-label\">About Us</span>\n"
        f"        <blockquote style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.5rem,3vw,2.4rem);"
        " font-weight:800; color:#fff; line-height:1.3; font-style:italic; margin:24px 0;"
        f" border-left:none; padding:0;\">&ldquo;{ctx['about_title']}&rdquo;</blockquote>\n"
        f"        <p style=\"font-size:1rem; color:rgba(255,255,255,0.58); line-height:1.75; margin-bottom:36px;\">{ctx['about_desc']}</p>\n"
        f"        <ul class=\"check-list\" style=\"display:inline-flex; flex-direction:column; text-align:left; margin:0 auto 36px; color:rgba(255,255,255,0.8);\">{_checklist_html(ctx['about_checklist'][:3])}</ul>\n"
        "        <div>\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">View Open Positions</a>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v3(ctx: dict) -> str:
    """Feature-stat grid + image row: stat numbers with about_img on right."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    pr = _hex_to_rgb(p)
    _is_regional = "regional" in ctx.get("routes_type", "OTR Routes").lower()
    states_val = "Multi-State" if _is_regional else "48 States"
    feat_stats = [
        (states_val, "Coverage", "\U0001f5fa\ufe0f"),
        ("24/7", "Dispatch", "\U0001f550"),
        ("CDL-A", "All Drivers", "\U0001f9d1\u200d\u2708\ufe0f"),
        ("No-Touch", "Dry Van", "\U0001f4e6"),
    ]
    grid_html = "".join(
        f"<div class=\"reveal delay-{i}\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px;"
        f" padding:28px 24px; text-align:center; transition:box-shadow 0.3s,transform 0.3s;\""
        f" onmouseover=\"this.style.boxShadow='0 8px 24px rgba({pr},0.1)';this.style.transform='translateY(-4px)'\""
        " onmouseout=\"this.style.boxShadow='';this.style.transform=''\">"
        f"<div style=\"font-size:2rem; margin-bottom:10px;\">{icon}</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.4rem; font-weight:900; color:{p}; margin-bottom:4px;\">{val}</div>"
        f"<div style=\"font-size:0.78rem; color:#64748B; text-transform:uppercase; letter-spacing:1px;\">{lbl}</div>"
        "</div>"
        for i, (val, lbl, icon) in enumerate(feat_stats, 1)
    )
    return (
        f"  <section class=\"section\" style=\"background:{abl};\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        f"        <span class=\"section-label\">About {ctx['company_name']}</span>\n"
        f"        <h2 class=\"section-heading\">{ctx['about_title']}</h2>\n"
        f"        <p class=\"section-desc\" style=\"margin:0 auto;\">{ctx['about_desc']}</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:52px;\">\n"
        + grid_html
        + "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:56px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        "          <span class=\"section-label\">What We Haul</span>\n"
        f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.6rem; font-weight:800; color:{navy}; margin-bottom:14px;\">{ctx['coverage_title']}</h3>\n"
        f"          <p style=\"font-size:0.97rem; color:#64748B; line-height:1.72; margin-bottom:24px;\">{ctx['coverage_desc']}</p>\n"
        f"          <ul class=\"check-list\">{_checklist_html(ctx['coverage_checklist'][:3])}</ul>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\" style=\"border-radius:12px; overflow:hidden; box-shadow:0 8px 32px rgba(0,0,0,0.1);\">\n"
        f"          <img src=\"images/{ctx['coverage_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:360px; object-fit:cover; display:block;\">\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v4(ctx: dict) -> str:
    """Vertical image strip: about_img stacked above coverage_img on one side, story on other."""
    p = ctx["primary"]; navy = ctx["navy"]; fh = ctx["font_heading"]
    return (
        "  <section class=\"section\" style=\"background:#fff;\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1.2fr; gap:56px; align-items:stretch;\">\n"
        "        <div class=\"reveal-left\" style=\"display:flex; flex-direction:column; gap:16px;\">\n"
        f"          <div style=\"flex:1; border-radius:12px; overflow:hidden; min-height:220px;\">\n"
        f"            <img src=\"images/{ctx['about_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:100%; object-fit:cover; display:block; min-height:220px;\">\n"
        "          </div>\n"
        f"          <div style=\"flex:1; border-radius:12px; overflow:hidden; min-height:220px;\">\n"
        f"            <img src=\"images/{ctx['coverage_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:100%; object-fit:cover; display:block; min-height:220px;\">\n"
        "          </div>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\" style=\"display:flex; flex-direction:column; justify-content:center;\">\n"
        "          <span class=\"section-label\">About Us</span>\n"
        f"          <h2 class=\"section-heading\" style=\"margin-bottom:16px;\">{ctx['about_title']}</h2>\n"
        f"          <p style=\"font-size:1rem; color:#64748B; line-height:1.72; margin-bottom:28px;\">{ctx['about_desc']}</p>\n"
        f"          <ul class=\"check-list\" style=\"margin-bottom:32px;\">{_checklist_html(ctx['about_checklist'])}</ul>\n"
        "          <a href=\"#careers\" class=\"btn btn-outline-dark\">Join Our Team</a>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v5(ctx: dict) -> str:
    """Terminal/CLI-styled about block: monospace green-on-dark text simulation."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]; short = ctx["company_short"]
    _is_regional = "regional" in ctx.get("routes_type", "OTR Routes").lower()
    coverage_line = "regional" if _is_regional else "nationwide (48 states)"
    lines = [
        (f"$ carrier --query {short.lower().replace(' ','_')}", "rgba(255,255,255,0.35)"),
        ("", ""),
        (f"  name         : {company}", "#A3E635"),
        (f"  base         : {ctx['city_state']}", "#A3E635"),
        (f"  coverage     : {coverage_line}", "#A3E635"),
        (f"  freight_type : {ctx['routes_type']}", "#A3E635"),
        (f"  home_time    : {ctx['home_time']}", "#A3E635"),
        ("  dispatch     : 24/7 available", "#A3E635"),
        ("  drivers      : CDL-A, vetted &amp; professional", "#A3E635"),
        ("  no_touch     : true", "#A3E635"),
        ("", ""),
        ("$ status", "rgba(255,255,255,0.35)"),
        ("  \u25cf ACCEPTING APPLICATIONS", "#22C55E"),
    ]
    term_html = "".join(
        f"<div style=\"line-height:1.8; font-family:'Courier New',monospace; font-size:0.88rem; color:{color};\">{text}</div>\n"
        for text, color in lines
    )
    return (
        "  <section class=\"section\" id=\"about\" style=\"background:#0D1117;\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        f"          <div style=\"border-radius:12px; overflow:hidden; background:#161B22; border:1px solid rgba(255,255,255,0.07); padding:28px 32px; font-family:'Courier New',monospace;\">\n"
        "            <div style=\"display:flex; gap:8px; margin-bottom:20px;\">\n"
        "              <span style=\"width:12px; height:12px; border-radius:50%; background:#FF5F56; display:inline-block;\"></span>\n"
        "              <span style=\"width:12px; height:12px; border-radius:50%; background:#FFBD2E; display:inline-block;\"></span>\n"
        "              <span style=\"width:12px; height:12px; border-radius:50%; background:#27C93F; display:inline-block;\"></span>\n"
        "            </div>\n"
        + term_html
        + "          </div>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\">\n"
        "          <span class=\"section-label\" style=\"color:#A3E635;\">About Us</span>\n"
        f"          <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.8rem,3vw,2.6rem);"
        " font-weight:900; color:#fff; line-height:1.1; margin-bottom:16px;\">"
        f"{ctx['about_title']}</h2>\n"
        f"          <p style=\"font-size:0.97rem; color:rgba(255,255,255,0.55); line-height:1.75; margin-bottom:28px;\">{ctx['about_desc']}</p>\n"
        f"          <ul class=\"check-list\" style=\"color:rgba(255,255,255,0.8); margin-bottom:32px;\">{_checklist_html(ctx['about_checklist'][:3])}</ul>\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">Join Our Team</a>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── CAREERS VARIANTS ──────────────────────────────────────────────────

def _careers_v1(ctx: dict) -> str:
    """Oversized pay banner + icon-grid perks: big pay strip then emoji-icon perk cards."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]
    pay_val = ctx["pay_range"].split("/")[0].strip()
    perk_icons = ["\U0001f4b5", "\U0001f3e0", "\U0001f6e3\ufe0f", "\u2705", "\U0001f4c5", "\U0001f3e5"]
    perk_list = ctx["perks"]
    perk_cards = "".join(
        f"<div class=\"reveal delay-{i}\" style=\"background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);"
        " border-radius:10px; padding:22px 18px; text-align:center;\">"
        f"<div style=\"font-size:1.8rem; margin-bottom:10px;\">{perk_icons[i % len(perk_icons)]}</div>"
        f"<div style=\"font-size:0.88rem; color:rgba(255,255,255,0.72); line-height:1.45; font-weight:500;\">{perk}</div>"
        "</div>"
        for i, perk in enumerate(perk_list[:6])
    )
    return (
        f"  <section id=\"careers\" style=\"background:{navy};\">\n"
        "    <!-- Oversized pay banner -->\n"
        f"    <div style=\"background:{p}; padding:48px 24px; text-align:center; border-bottom:4px solid rgba(255,255,255,0.1);\">\n"
        "      <div class=\"reveal\">\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px;"
        " text-transform:uppercase; color:rgba(255,255,255,0.65); margin-bottom:8px;\">CDL-A &middot; Now Hiring</div>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:clamp(3rem,7vw,6rem);"
        f" font-weight:900; color:#fff; line-height:0.95; letter-spacing:-3px; margin-bottom:6px;\">{pay_val}</div>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.1rem; font-weight:600; color:rgba(255,255,255,0.7);\">{ctx['job_title']} &middot; {ctx['routes_type']}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <!-- Stats row -->\n"
        f"    <div style=\"background:{navy}; padding:32px 24px; border-bottom:1px solid rgba(255,255,255,0.06);\">\n"
        "      <div style=\"max-width:960px; margin:0 auto; display:grid; grid-template-columns:repeat(4,1fr); gap:16px;\">\n"
        + _stat_cards_dark(ctx)
        + "\n      </div>\n"
        "    </div>\n"
        "    <!-- Perk icon grid -->\n"
        "    <div style=\"padding:64px 24px;\">\n"
        "      <div style=\"max-width:1000px; margin:0 auto;\">\n"
        f"        <h3 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:1.1rem; font-weight:800; color:#fff; text-align:center; margin-bottom:32px; text-transform:uppercase; letter-spacing:1.5px;\">What You Get</h3>\n"
        "        <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:40px;\">\n"
        + perk_cards
        + "        </div>\n"
        "        <div style=\"text-align:center;\">\n"
        f"          <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:15px 44px; font-size:1rem;\">Apply Now &mdash; {ctx['job_title']}</a>\n"
        "        </div>\n"
        f"        <p class=\"eeo-text\">{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, or veteran status.</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v2(ctx: dict) -> str:
    """Alternating color rows: job title / requirements / benefits / apply — each a distinct bg."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    company = ctx["company_name"]
    return (
        "  <section id=\"careers\">\n"
        "    <!-- Row 1: Job title -->\n"
        f"    <div style=\"background:{navy}; padding:64px 24px; text-align:center;\">\n"
        "      <div class=\"reveal\">\n"
        f"        <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{pl}; display:block; margin-bottom:10px;\">Now Hiring</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(2rem,4vw,3rem); font-weight:900; color:#fff; letter-spacing:-0.5px; margin-bottom:8px;\">{ctx['job_title']}</h2>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:{pl};\">{ctx['pay_range']}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <!-- Row 2: Quick stats -->\n"
        f"    <div style=\"background:{p}; padding:36px 24px;\">\n"
        "      <div style=\"max-width:900px; margin:0 auto; display:grid; grid-template-columns:repeat(4,1fr); gap:20px; text-align:center;\">\n"
        + "".join(
            f"<div><div style=\"font-family:'{fh}',sans-serif; font-size:1.3rem; font-weight:900; color:#fff;\">{val}</div>"
            f"<div style=\"font-size:0.72rem; color:rgba(255,255,255,0.6); text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">{lbl}</div></div>"
            for val, lbl in [
                (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
                (ctx["home_time_short"], ctx["home_time_detail"]),
                (ctx["routes"], ctx["routes_type"]),
                (ctx["fourth_card_value"], ctx["fourth_card_label"]),
            ]
        )
        + "\n      </div>\n"
        "    </div>\n"
        "    <!-- Row 3: Benefits -->\n"
        f"    <div style=\"background:{abl}; padding:64px 24px;\">\n"
        "      <div style=\"max-width:860px; margin:0 auto;\">\n"
        "        <div class=\"reveal\" style=\"text-align:center; margin-bottom:32px;\">\n"
        f"          <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{p};\">Benefits &amp; Perks</span>\n"
        "        </div>\n"
        "        <div class=\"reveal\" style=\"display:grid; grid-template-columns:1fr 1fr; gap:12px 48px; color:#334155;\">\n"
        f"          {ctx['perks_html']}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <!-- Row 4: Apply -->\n"
        "    <div style=\"background:#fff; padding:56px 24px; text-align:center;\">\n"
        "      <div class=\"reveal\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.4rem; font-weight:800; color:{navy}; margin-bottom:16px;\">Ready to Get Behind the Wheel?</h3>\n"
        f"        <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:15px 44px; font-size:1rem;\">Apply Today</a>\n"
        f"        <p class=\"eeo-text-dark\">{company} is an Equal Opportunity Employer.</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v3(ctx: dict) -> str:
    """Question-style applicant checklist: 'Do you have CDL-A? ✓' + Apply CTA."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    company = ctx["company_name"]
    questions = [
        ("Do you hold a valid CDL-A license?", True),
        (f"Do you have {ctx['min_experience']} of verifiable experience?", True),
        ("Do you want consistent, no-touch dry van freight?", True),
        (f"Are you looking for {ctx['home_time']}?", True),
        (f"Do you want {ctx['pay_range']} weekly?", True),
        ("Are you ready to work with a carrier that actually communicates?", True),
    ]
    q_html = "".join(
        f"<div class=\"reveal delay-{i}\" style=\"display:flex; align-items:center; gap:16px; padding:18px 24px;"
        " background:#fff; border:1px solid #E2E8F0; border-radius:10px;\">"
        f"<span style=\"width:28px; height:28px; border-radius:50%; background:{'#DCFCE7' if chk else '#FEE2E2'};"
        f" color:{'#16A34A' if chk else '#DC2626'}; display:flex; align-items:center; justify-content:center;"
        f" font-size:0.9rem; font-weight:900; flex-shrink:0;\">{'&#10003;' if chk else '&#10007;'}</span>"
        f"<span style=\"font-size:0.94rem; color:#334155; font-weight:500;\">{q}</span>"
        "</div>"
        for i, (q, chk) in enumerate(questions, 1)
    )
    return (
        f"  <section class=\"section\" style=\"background:{abl};\" id=\"careers\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        "          <span class=\"section-label\">Is This You?</span>\n"
        f"          <h2 class=\"section-heading\" style=\"margin-bottom:16px;\">{ctx['job_title']}</h2>\n"
        f"          <div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:{p}; margin-bottom:20px;\">{ctx['pay_range']}</div>\n"
        f"          <p style=\"font-size:0.97rem; color:#64748B; line-height:1.72; margin-bottom:28px;\">If you answered yes to all of the below, we want to hear from you today. No gimmicks &mdash; just real freight and fair pay.</p>\n"
        f"          <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\">Apply Now</a>\n"
        f"          <p class=\"eeo-text-dark\" style=\"max-width:400px;\">{company} is an Equal Opportunity Employer.</p>\n"
        "        </div>\n"
        "        <div style=\"display:flex; flex-direction:column; gap:12px;\">\n"
        + q_html
        + "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v4(ctx: dict) -> str:
    """Split with quick-apply form: left job details, right 3-field inline apply form."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]
    stat_items = [
        (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
        (ctx["home_time_short"], ctx["home_time_detail"]),
        (ctx["routes"], ctx["routes_type"]),
        (ctx["fourth_card_value"], ctx["fourth_card_label"]),
    ]
    stat_html = "".join(
        f"<div style=\"text-align:center; padding:16px; background:rgba(255,255,255,0.06);"
        " border:1px solid rgba(255,255,255,0.08); border-radius:8px;\">"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:900; color:{pl}; margin-bottom:4px;\">{val}</div>"
        f"<div style=\"font-size:0.72rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px;\">{lbl}</div>"
        "</div>"
        for val, lbl in stat_items
    )
    return (
        f"  <section id=\"careers\" style=\"display:grid; grid-template-columns:1fr 1fr; min-height:640px;\">\n"
        f"    <div style=\"background:{navy}; padding:80px 56px; display:flex; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-left\">\n"
        f"        <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{pl}; display:block; margin-bottom:10px;\">Now Hiring</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.8rem,3vw,2.6rem); font-weight:900; color:#fff; letter-spacing:-0.5px; margin-bottom:8px;\">{ctx['job_title']}</h2>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.4rem; font-weight:900; color:{pl}; margin-bottom:28px;\">{ctx['pay_range']}</div>\n"
        f"        <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:28px;\">{stat_html}</div>\n"
        "        <div style=\"color:rgba(255,255,255,0.65); font-size:0.9rem; line-height:1.7;\">\n"
        f"          {ctx['perks_html']}\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <div style=\"background:#F8FAFC; padding:80px 56px; display:flex; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-right\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.4rem; font-weight:800; color:{navy}; margin-bottom:8px;\">Quick Apply</h3>\n"
        "        <p style=\"font-size:0.92rem; color:#64748B; margin-bottom:24px;\">Takes less than 2 minutes. We'll reach out within 24 hours.</p>\n"
        "        <form data-blk-form=\"1\">\n"
        "          <div class=\"field\"><label>Full Name</label><input type=\"text\" placeholder=\"Your full name\" required></div>\n"
        "          <div class=\"field\"><label>Phone Number</label><input type=\"tel\" placeholder=\"(555) 000-0000\" required></div>\n"
        "          <div class=\"field\"><label>Email Address</label><input type=\"email\" placeholder=\"you@email.com\" required></div>\n"
        "          <div class=\"field\"><label>Years of CDL-A Experience</label><select><option value=\"\">Select...</option><option>1 year</option><option>2 years</option><option>3-5 years</option><option>5+ years</option></select></div>\n"
        f"          <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:14px; font-size:1rem;\">Submit Application</button>\n"
        "        </form>\n"
        f"        <p style=\"font-size:0.77rem; color:#94A3B8; margin-top:16px;\">{company} is an Equal Opportunity Employer.</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v5(ctx: dict) -> str:
    """9-cell job details grid: pay, home time, routes, exp, freight, equipment, bonus, orientation, benefits."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    company = ctx["company_name"]
    pr = _hex_to_rgb(p)
    cells = [
        ("\U0001f4b5", "Weekly Pay", ctx["pay_range"]),
        ("\U0001f3e0", "Home Time", ctx["home_time"]),
        ("\U0001f6e3\ufe0f", "Routes", ctx["routes"]),
        ("\U0001f4cb", "Min. Experience", ctx["min_experience"]),
        ("\U0001f4e6", "Freight Type", "No-Touch Dry Van"),
        ("\U0001f69a", "Equipment", "Late-Model Trucks"),
        (ctx["fourth_card_value"], ctx["fourth_card_label"], "Driver Bonus"),
        ("\U0001f4c5", "Orientation", "Paid Orientation"),
        ("\U0001f3e5", "Benefits", "Health &amp; Dental"),
    ]
    cell_html = "".join(
        f"<div class=\"reveal\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:10px;"
        f" padding:24px 20px; text-align:center; transition:border-color 0.3s,transform 0.3s;\""
        f" onmouseover=\"this.style.borderColor='{p}';this.style.transform='translateY(-3px)'\""
        " onmouseout=\"this.style.borderColor='#E2E8F0';this.style.transform=''\">"
        f"<div style=\"font-size:1.6rem; margin-bottom:8px;\">{icon}</div>"
        f"<div style=\"font-size:0.7rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;\">{label}</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:0.95rem; font-weight:800; color:{navy};\">{value}</div>"
        "</div>"
        for icon, label, value in cells
    )
    return (
        f"  <section class=\"section\" style=\"background:{abl};\" id=\"careers\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:48px;\">\n"
        "        <span class=\"section-label\">Now Hiring</span>\n"
        f"        <h2 class=\"section-heading\">{ctx['job_title']}</h2>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.6rem; font-weight:900; color:{p}; margin-top:8px;\">{ctx['pay_range']}</div>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:16px; max-width:860px; margin:0 auto 40px;\">\n"
        + cell_html
        + "      </div>\n"
        "      <div class=\"reveal\" style=\"text-align:center;\">\n"
        f"        <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:15px 44px; font-size:1rem;\">Apply for This Position</a>\n"
        "      </div>\n"
        f"      <p class=\"eeo-text-dark\">{company} is an Equal Opportunity Employer.</p>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── CONTACT VARIANTS ──────────────────────────────────────────────────

def _contact_v1(ctx: dict) -> str:
    """Minimalist single CTA: 'Ready to move?' + giant button + tiny contact info below."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    _addr = f"{ctx['address']}, {ctx['city_state']}" if ctx["address"] else ctx["city_state"]
    return (
        f"  <section class=\"section\" style=\"background:{navy}; text-align:center;\" id=\"contact\">\n"
        "    <div class=\"container\" style=\"max-width:720px;\">\n"
        "      <div class=\"reveal\">\n"
        "        <span class=\"section-label\">Contact</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.2rem,5vw,4rem); font-weight:900;"
        " color:#fff; line-height:1.07; margin-bottom:16px;\">Ready to Move?</h2>\n"
        "        <p style=\"font-size:1.05rem; color:rgba(255,255,255,0.5); margin-bottom:36px; line-height:1.72;\">"
        "Whether you have freight to ship or you're ready to drive, we make it easy to get started.</p>\n"
        "        <div style=\"display:flex; gap:14px; justify-content:center; flex-wrap:wrap; margin-bottom:48px;\">\n"
        f"          <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:18px 52px; font-size:1.1rem;\">Get In Touch</a>\n"
        "          <a href=\"#careers\" class=\"btn btn-outline-light\" style=\"padding:18px 40px; font-size:1.1rem;\">Apply Now</a>\n"
        "        </div>\n"
        "        <div style=\"display:flex; justify-content:center; gap:40px; flex-wrap:wrap;"
        " padding-top:32px; border-top:1px solid rgba(255,255,255,0.08);\">\n"
        f"          <div style=\"text-align:center;\"><div style=\"font-size:1.2rem; margin-bottom:4px;\">\u2709\ufe0f</div>"
        f"<div style=\"font-size:0.82rem; color:rgba(255,255,255,0.4);\">{ctx['email']}</div></div>\n"
        f"          <div style=\"text-align:center;\"><div style=\"font-size:1.2rem; margin-bottom:4px;\">\U0001f4cd</div>"
        f"<div style=\"font-size:0.82rem; color:rgba(255,255,255,0.4);\">{_addr}</div></div>\n"
        f"          <div style=\"text-align:center;\"><div style=\"font-size:1.2rem; margin-bottom:4px;\">\U0001f550</div>"
        "<div style=\"font-size:0.82rem; color:rgba(255,255,255,0.4);\">Dispatch 24/7</div></div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _contact_v2(ctx: dict) -> str:
    """Full-bleed bg image with centered glass-morphism form panel."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    nr = _hex_to_rgb(navy)
    _addr = f"{ctx['address']}<br>{ctx['city_state']}" if ctx["address"] else ctx["city_state"]
    return (
        f"  <section id=\"contact\" style=\"position:relative; padding:100px 24px;"
        f" background:url('images/{ctx['coverage_img']}') center/cover no-repeat;\">\n"
        f"    <div style=\"position:absolute; inset:0; background:rgba({nr},0.75);\"></div>\n"
        "    <div style=\"position:relative; z-index:1; max-width:660px; margin:0 auto;\">\n"
        "      <div class=\"reveal\" style=\"background:rgba(255,255,255,0.08); backdrop-filter:blur(12px);"
        " -webkit-backdrop-filter:blur(12px); border:1px solid rgba(255,255,255,0.15);"
        " border-radius:20px; padding:48px;\">\n"
        "        <div style=\"text-align:center; margin-bottom:32px;\">\n"
        "          <span class=\"section-label\">Contact Us</span>\n"
        f"          <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.6rem,3vw,2.4rem);"
        " font-weight:900; color:#fff; margin-bottom:8px;\">Let's Talk Freight</h2>\n"
        "          <p style=\"font-size:0.9rem; color:rgba(255,255,255,0.55);\">Get a quote or send your driver application &mdash; we respond the same day.</p>\n"
        "        </div>\n"
        "        <form data-blk-form=\"1\">\n"
        "          <div class=\"field-row\">"
        "<div class=\"field\"><label style=\"color:rgba(255,255,255,0.7);\">Name</label>"
        "<input type=\"text\" placeholder=\"Your name\" style=\"background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.18); color:#fff;\" required></div>"
        "<div class=\"field\"><label style=\"color:rgba(255,255,255,0.7);\">Email</label>"
        "<input type=\"email\" placeholder=\"you@email.com\" style=\"background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.18); color:#fff;\" required></div>"
        "          </div>\n"
        "          <div class=\"field\"><label style=\"color:rgba(255,255,255,0.7);\">Inquiry Type</label>"
        "<select style=\"background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.18); color:#fff;\">"
        "<option value=\"\">Select...</option><option>Freight Quote</option><option>Driver Application</option><option>General</option>"
        "</select></div>\n"
        "          <div class=\"field\"><label style=\"color:rgba(255,255,255,0.7);\">Message</label>"
        "<textarea placeholder=\"Tell us what you need...\" style=\"background:rgba(255,255,255,0.08); border-color:rgba(255,255,255,0.18); color:#fff;\"></textarea></div>\n"
        f"          <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:14px; font-size:1rem;\">Send Message</button>\n"
        "        </form>\n"
        "        <div style=\"display:flex; justify-content:center; gap:28px; margin-top:28px; flex-wrap:wrap;\">\n"
        f"          <div style=\"font-size:0.8rem; color:rgba(255,255,255,0.45);\">\u2709\ufe0f {ctx['email']}</div>\n"
        f"          <div style=\"font-size:0.8rem; color:rgba(255,255,255,0.45);\">\U0001f4cd {ctx['city_state']}</div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _contact_v3(ctx: dict) -> str:
    """Phone-first layout: big call-to-dispatch primary CTA, form as secondary action."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    _addr = f"{ctx['address']}, {ctx['city_state']}" if ctx["address"] else ctx["city_state"]
    return (
        f"  <section id=\"contact\" style=\"background:{g50};\">\n"
        "    <!-- Phone-first top banner -->\n"
        f"    <div style=\"background:{navy}; padding:64px 24px; text-align:center;\">\n"
        "      <div class=\"reveal\">\n"
        "        <span class=\"section-label\">Get In Touch</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(2rem,4vw,3rem); font-weight:900;"
        " color:#fff; margin-bottom:12px; letter-spacing:-0.5px;\">\U0001f4de Call Dispatch</h2>\n"
        f"        <p style=\"font-size:1rem; color:rgba(255,255,255,0.5); max-width:480px; margin:0 auto 28px; line-height:1.7;\">"
        "Our dispatch team is available around the clock. Real people, real answers &mdash; no phone trees.</p>\n"
        "        <div style=\"display:flex; justify-content:center; gap:20px; flex-wrap:wrap;\">\n"
        f"          <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        f" border-radius:10px; padding:16px 28px; text-align:center;\">"
        f"<div style=\"font-size:0.7rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;\">Email</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:0.97rem; font-weight:700; color:{pl};\">{ctx['email']}</div></div>\n"
        f"          <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        " border-radius:10px; padding:16px 28px; text-align:center;\">"
        "<div style=\"font-size:0.7rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;\">Location</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:0.97rem; font-weight:700; color:#fff;\">{_addr}</div></div>\n"
        f"          <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        " border-radius:10px; padding:16px 28px; text-align:center;\">"
        "<div style=\"font-size:0.7rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;\">Hours</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:0.97rem; font-weight:700; color:#fff;\">24/7 Dispatch</div></div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <!-- Secondary form -->\n"
        "    <div style=\"padding:72px 24px;\">\n"
        "      <div style=\"max-width:680px; margin:0 auto;\">\n"
        "        <div class=\"reveal\" style=\"text-align:center; margin-bottom:32px;\">\n"
        f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.3rem; font-weight:800; color:{navy}; margin-bottom:8px;\">Or Send a Message</h3>\n"
        "          <p style=\"font-size:0.92rem; color:#64748B;\">Prefer email? Use the form below and we'll get back to you the same day.</p>\n"
        "        </div>\n"
        "        <div class=\"reveal\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:40px;\">\n"
        "          <form data-blk-form=\"1\">\n"
        "            <div class=\"field-row\"><div class=\"field\"><label>Name</label><input type=\"text\" placeholder=\"Your full name\" required></div><div class=\"field\"><label>Email</label><input type=\"email\" placeholder=\"you@email.com\" required></div></div>\n"
        "            <div class=\"field\"><label>Subject</label><select><option value=\"\">Select one...</option><option>Freight Quote</option><option>Driver Application</option><option>General Question</option></select></div>\n"
        "            <div class=\"field\"><label>Message</label><textarea placeholder=\"How can we help?\"></textarea></div>\n"
        f"            <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:14px;\">Send Message</button>\n"
        "          </form>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

def generate_website_from_blocks(info: dict) -> str:
    """
    Generate a premium, never-repeating trucking company website.

    Delegates page rendering to the studio engine, which picks one of several
    fully self-contained "design studios" (each its own CSS, layout, type scale
    and motion) plus a procedurally generated colour palette — so two
    generations rarely look alike. Returns the path to a zip containing
    index.html + images/.

    The embedded breakout-safe company-data <script> is preserved by the studio
    engine, so /appeal and the CSV-autofill flow keep working. The legacy
    block-based renderer (`_legacy_generate_from_blocks`) is kept below as a
    fallback in case the studio engine is unavailable.
    """
    try:
        from react_engine import render_site
        html, ctx = render_site(info)
    except Exception as exc:  # pragma: no cover - defensive fallback
        log = __import__("logging").getLogger("automation")
        log.warning("Studio engine failed (%s); falling back to legacy generator", exc)
        return _legacy_generate_from_blocks(info)

    domain = info.get("domain", "site")
    tmp_dir  = tempfile.mkdtemp()
    site_dir = os.path.join(tmp_dir, domain.replace(".", "_"))
    images_dir = os.path.join(site_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    for img_name in {ctx["hero_img"], ctx["about_img"], ctx["about_img2"], ctx["coverage_img"]}:
        src = _ASSETS_DIR / img_name
        if src.exists():
            shutil.copy2(str(src), os.path.join(images_dir, img_name))

    zip_name = f"{domain.replace('.', '_')}_website.zip"
    zip_path = os.path.join(tmp_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(site_dir):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, site_dir))

    return zip_path


def _legacy_generate_from_blocks(info: dict) -> str:
    """
    Legacy block-based generator (original `generate_website_from_blocks`).
    Kept as a fallback; produces index.html + images/ as a zip.
    """
    color = random.choice(COLOR_SCHEMES)
    font  = random.choice(FONT_PAIRS)
    ctx   = _build_ctx(info, color, font)

    hero    = random.choice([_hero_v1, _hero_v2, _hero_v3, _hero_v4, _hero_v5])(ctx)
    process = random.choice([_process_v1, _process_v2, _process_v3, _process_v4, _process_v5])(ctx)
    about   = random.choice([_about_v1, _about_v2, _about_v3, _about_v4, _about_v5])(ctx)
    careers = random.choice([_careers_v1, _careers_v2, _careers_v3, _careers_v4, _careers_v5])(ctx)
    contact = random.choice([_contact_v1, _contact_v2, _contact_v3])(ctx)

    owner_name = _resolve_owner_name(info.get("email", ""), ctx["domain"])
    company_data = {
        "company_name": ctx["company_name"], "domain": ctx["domain"],
        "email": ctx["email"], "address": ctx["address"],
        "city_state": ctx["city_state"], "owner_name": owner_name,
        "job_title": ctx["job_title"], "pay_range": ctx["pay_range"],
        "home_time": ctx["home_time"], "min_experience": ctx["min_experience"],
        "routes_type": ctx["routes_type"], "perks": ctx["perks"],
    }
    body = (_company_data_script(company_data)
            + _nav(ctx) + hero + process + about + careers + contact + _footer(ctx))
    html = _page_shell(ctx, body)

    domain = info.get("domain", "site")
    tmp_dir  = tempfile.mkdtemp()
    site_dir = os.path.join(tmp_dir, domain.replace(".", "_"))
    images_dir = os.path.join(site_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    for img_name in {ctx["hero_img"], ctx["about_img"], ctx["about_img2"], ctx["coverage_img"]}:
        src = _ASSETS_DIR / img_name
        if src.exists():
            shutil.copy2(str(src), os.path.join(images_dir, img_name))

    zip_name = f"{domain.replace('.', '_')}_website.zip"
    zip_path = os.path.join(tmp_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(site_dir):
            for file in files:
                fp = os.path.join(root, file)
                zf.write(fp, os.path.relpath(fp, site_dir))

    return zip_path
