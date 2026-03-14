"""
Website generator for trucking company single-page sites.
Produces index.html + images/ folder as a zip file.
Also generates an Indeed job description (markdown).
"""

import random
import os
import shutil
import zipfile
import tempfile
from pathlib import Path

# ── Stock image pools ──────────────────────────────────
_ASSETS_DIR = Path(__file__).parent.parent / "assets" / "stock_images"
_HERO_IMAGES = sorted(_ASSETS_DIR.glob("hero_*.jpg"))
_ABOUT_IMAGES = sorted(_ASSETS_DIR.glob("about_*.jpg"))
_COVERAGE_IMAGES = sorted(_ASSETS_DIR.glob("coverage_*.jpg"))

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
    ("Driven by <span class='accent'>Results</span>", "Hiring OTR Drivers"),
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
    ("<span class='accent'>Steady</span> Miles. Strong Team.", "Open OTR Positions"),
    ("Committed to the <span class='accent'>Long Haul</span>", "CDL-A Opportunities"),
    ("We Don't Just <span class='accent'>Ship.</span> We Deliver.", "Drivers Needed"),
    ("Powered by <span class='accent'>People</span> Who Care", "Join the Team"),
    ("Making Freight <span class='accent'>Simple</span>", "Apply for OTR Positions"),
    ("Coast to <span class='accent'>Coast.</span> Load to Load.", "Hiring Across 48 States"),
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
    "Headquartered in {city_state}, {company} provides reliable OTR freight service with a personal touch. We treat every load like our reputation depends on it — because it does.",
    "We're {company}, a {city_state}-based trucking operation that was started by people who actually understand the road. Our priority is simple: move freight safely and on time.",
    "{company} keeps it simple. We're a {city_state} carrier with professional drivers, well-maintained trucks, and a team that communicates. That's the whole formula.",
    "Out of {city_state}, {company} serves shippers who need a carrier they can trust without babysitting. We take the load and handle everything from there.",
    "{company} is built around reliability. We're a {city_state} operation that moves freight across 48 states — with experienced drivers and equipment you can count on.",
    "We're a small carrier out of {city_state} that operates like a big one. {company} has the capacity, the tech, and the people to get your freight where it needs to be.",
    "{company} started with one truck and a commitment to do things right. Today we run a full fleet out of {city_state} — and that commitment hasn't changed.",
    "Based in {city_state}, {company} is a carrier that values accountability. Every driver, every load, every mile — tracked, managed, and delivered with care.",
    "At {company}, we believe drivers are the backbone of this business. That's why we run well-maintained equipment out of {city_state} and treat our team right.",
    "{company} hauls dry van freight from {city_state} to everywhere the road goes. We're not flashy — just consistent, professional, and always available.",
    "We're a {city_state} trucking company that puts our money where our mouth is. {company} invests in safety, equipment, and people — and it shows in every delivery.",
    "Shipping with {company} is straightforward. Tell us what you need, we move it. No middlemen, no runaround. Just honest freight service out of {city_state}.",
    "{company} is proud to call {city_state} home. We're a carrier that understands what shippers actually need — reliability, communication, and zero excuses.",
    "From {city_state}, {company} covers the lower 48 with professional OTR service. We've built our reputation one on-time delivery at a time.",
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
    ["Newer trucks with GPS tracking", "Qualified OTR professionals", "Always-on dispatch communication", "Freight handled with care"],
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
    ["Fleet updated and GPS-tracked", "Seasoned OTR drivers", "Support team available 24/7", "No-touch policy on all freight"],
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

COVERAGE_DESCRIPTIONS = [
    "Whether it's a cross-country haul or a regional lane, {company} has the coverage and the freight to keep your business — and our drivers — moving without gaps.",
    "From coast to coast, {company} runs consistent freight lanes across all 48 states. Wherever your freight needs to go, we've got a truck heading that direction.",
    "{company} covers the entire lower 48 with dependable OTR service. We maintain regular routes so our drivers stay productive and your freight stays on schedule.",
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
    ["Nationwide OTR coverage", "No seasonal freight gaps", "Regular route options", "Strong delivery track record"],
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
    ["U.S.-wide OTR coverage", "Loads available every week", "Routes that work for work-life balance", "On-time arrivals are our standard"],
    ["Covering the whole country", "Consistent volume, consistent routes", "Lane options for every driver", "Delivery reputation built on results"],
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
    about_checklist = random.choice(ABOUT_CHECKLISTS)
    coverage_title = random.choice(COVERAGE_TITLES)
    coverage_checklist = random.choice(COVERAGE_CHECKLISTS)

    company = info["company_name"]
    short = info.get("company_short", company.split()[0])
    domain = info["domain"]
    email = info["email"]
    address = info["address"]
    city_state = info["city_state"]
    service = info.get("service_type", "OTR Trucking — Dry Van — 48 States")
    job_title = info["job_title"]
    pay_range = info["pay_range"]

    # Pick random about/coverage descriptions and fill in company info
    about_desc = random.choice(ABOUT_DESCRIPTIONS).format(company=company, city_state=city_state)
    coverage_desc = random.choice(COVERAGE_DESCRIPTIONS).format(company=company, city_state=city_state)

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
          <p>{about_desc}</p>
          <ul class="check-list">
            <li><span class="check-dot">&#10003;</span> {about_checklist[0]}</li>
            <li><span class="check-dot">&#10003;</span> {about_checklist[1]}</li>
            <li><span class="check-dot">&#10003;</span> {about_checklist[2]}</li>
            <li><span class="check-dot">&#10003;</span> {about_checklist[3]}</li>
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
          <p>{coverage_desc}</p>
          <ul class="check-list">
            <li><span class="check-dot">&#10003;</span> {coverage_checklist[0]}</li>
            <li><span class="check-dot">&#10003;</span> {coverage_checklist[1]}</li>
            <li><span class="check-dot">&#10003;</span> {coverage_checklist[2]}</li>
            <li><span class="check-dot">&#10003;</span> {coverage_checklist[3]}</li>
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

    # Copy random stock images
    images_dir = os.path.join(site_dir, "images")
    if _HERO_IMAGES:
        shutil.copy2(str(random.choice(_HERO_IMAGES)), os.path.join(images_dir, "hero-bg.jpg"))
    if _ABOUT_IMAGES:
        shutil.copy2(str(random.choice(_ABOUT_IMAGES)), os.path.join(images_dir, "about-fleet.jpg"))
    if _COVERAGE_IMAGES:
        shutil.copy2(str(random.choice(_COVERAGE_IMAGES)), os.path.join(images_dir, "coverage-routes.jpg"))

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

    # 30 section title styles
    section_styles = [
        {"duties": "Day-to-Day", "reqs": "What You Bring", "pay": "Your Pay & Benefits", "schedule": "Home Time & Routes"},
        {"duties": "The Work", "reqs": "What We Need", "pay": "Compensation", "schedule": "Schedule & Routes"},
        {"duties": "Behind the Wheel", "reqs": "What We Need From You", "pay": "What You're Getting", "schedule": "The Schedule"},
        {"duties": "On the Road", "reqs": "Requirements", "pay": "Pay & Perks", "schedule": "Where You'll Run"},
        {"duties": "Your Daily Run", "reqs": "Qualifications", "pay": "What We Offer", "schedule": "Routes & Home Time"},
        {"duties": "What the Job Looks Like", "reqs": "Who We're Looking For", "pay": "The Package", "schedule": "Routing & Time Off"},
        {"duties": "What You'll Be Doing", "reqs": "What We Expect", "pay": "Pay & Benefits", "schedule": "Your Schedule"},
        {"duties": "Life on the Road", "reqs": "Must-Haves", "pay": "Earnings & Perks", "schedule": "Home Time"},
        {"duties": "The Gig", "reqs": "Before You Apply", "pay": "What's In It for You", "schedule": "Where You'll Be"},
        {"duties": "Your Responsibilities", "reqs": "What It Takes", "pay": "Total Compensation", "schedule": "Route Details"},
        {"duties": "Every Day Looks Like This", "reqs": "You'll Need", "pay": "Here's What You Get", "schedule": "Running & Resting"},
        {"duties": "What We'll Ask of You", "reqs": "The Non-Negotiables", "pay": "Your Earnings", "schedule": "Schedule & Home Time"},
        {"duties": "Duties", "reqs": "Driver Requirements", "pay": "Benefits Package", "schedule": "Lanes & Schedule"},
        {"duties": "The Day-to-Day Reality", "reqs": "Who Should Apply", "pay": "Compensation & Benefits", "schedule": "Route & Rest Info"},
        {"duties": "A Typical Week", "reqs": "Minimum Qualifications", "pay": "What You'll Earn", "schedule": "How the Schedule Works"},
        {"duties": "What's Expected", "reqs": "To Be Considered", "pay": "Pay Structure", "schedule": "Routing & Days Off"},
        {"duties": "In the Driver's Seat", "reqs": "Required Credentials", "pay": "Your Compensation", "schedule": "On the Road & Off"},
        {"duties": "From Pickup to Drop", "reqs": "Who Fits This Role", "pay": "The Numbers", "schedule": "Time on the Road"},
        {"duties": "How Your Day Goes", "reqs": "What We're Looking For", "pay": "Pay, Perks & More", "schedule": "How Routing Works"},
        {"duties": "Daily Operations", "reqs": "Eligibility", "pay": "What You Take Home", "schedule": "Schedule Details"},
        {"duties": "What This Job Involves", "reqs": "Hiring Criteria", "pay": "Compensation Details", "schedule": "Where and When"},
        {"duties": "Your Role", "reqs": "Candidate Profile", "pay": "Financial Package", "schedule": "Home Time & Routing"},
        {"duties": "Expectations", "reqs": "Baseline Requirements", "pay": "What We Pay", "schedule": "How It Works"},
        {"duties": "What Driving With Us Looks Like", "reqs": "The Basics We Need", "pay": "Pay & Benefits Breakdown", "schedule": "Your Time"},
        {"duties": "Here's the Job", "reqs": "Here's What We Need", "pay": "Here's What You Get", "schedule": "Here's the Schedule"},
        {"duties": "Core Duties", "reqs": "Qualifications & Requirements", "pay": "Earnings Overview", "schedule": "Routing Schedule"},
        {"duties": "What You'll Handle", "reqs": "Who Qualifies", "pay": "Money & Benefits", "schedule": "Time Breakdown"},
        {"duties": "Job Functions", "reqs": "Prerequisites", "pay": "Reward Package", "schedule": "Run & Rest Pattern"},
        {"duties": "Responsibilities on the Road", "reqs": "Driver Checklist", "pay": "What We Bring to the Table", "schedule": "How Your Time Splits"},
        {"duties": "Typical Workload", "reqs": "What You Need to Have", "pay": "Full Benefits Rundown", "schedule": "Route & Home Pattern"},
    ]

    # 30 intro paragraphs
    intros = [
        f"{company} is looking for a dependable driver out of {city_state}. We run freight across all 48 states with consistent miles and a dispatch team that keeps things moving. If you want steady work, fair pay, and a carrier that respects your time — keep reading.",
        f"We need another solid driver at {company}. Based out of {city_state}, we haul dry van freight across the lower 48 with no games and no gimmicks. Good pay, real home time, and a team that has your back.",
        f"{company} is hiring out of {city_state}. We're a straightforward carrier that moves freight, pays well, and treats drivers like adults. If that sounds like what you've been looking for, here's the details.",
        f"Looking for a driving job that doesn't come with a list of broken promises? {company} runs OTR freight from {city_state} across all 48 states. We keep it real — here's what the job looks like.",
        f"{company} needs experienced drivers. We're based in {city_state} and we run the lower 48 with consistent freight, fair pay, and a dispatch team that actually listens. Here's the rundown.",
        f"We're hiring at {company}. If you're a CDL-A driver looking for consistent miles and a carrier that doesn't waste your time, read on. We operate out of {city_state} and cover all 48 states.",
        f"Tired of carriers that overpromise and underdeliver? {company} out of {city_state} keeps it simple: good freight, honest pay, and a team that respects the people behind the wheel.",
        f"{company} is a {city_state}-based carrier looking to add experienced drivers to our fleet. We run all 48 states, pay consistently, and don't play games with home time.",
        f"Here's a driving job that won't waste your time. {company} runs OTR dry van freight out of {city_state}. Consistent miles, weekly pay, and a dispatch team that treats you like a human being.",
        f"If you know how to drive and want a company that knows how to treat drivers, {company} might be your next stop. We're hiring out of {city_state} for OTR routes across 48 states.",
        f"{company} operates from {city_state} and we're looking for drivers who want stability. We run freight coast to coast with consistent lanes and a team that communicates.",
        f"Want miles that actually pay and a company that actually cares? {company} is hiring OTR drivers out of {city_state}. No bait-and-switch — just honest work.",
        f"At {company}, drivers aren't a number. We're a growing carrier out of {city_state} looking for experienced OTR professionals who want consistent work and real support.",
        f"{company} hauls freight the right way — out of {city_state}, across all 48 states. We're hiring drivers who take the job seriously and want a carrier that does the same.",
        f"We're expanding our fleet at {company} and need reliable CDL-A drivers. Based in {city_state}, we run steady OTR routes with good pay and real home time. Here's the full picture.",
        f"{company} is a no-nonsense carrier operating out of {city_state}. We need experienced drivers who want steady miles, fair compensation, and a company that keeps its word.",
        f"Looking for your next driving gig? {company} runs OTR freight from {city_state} across the continental U.S. We've got the freight, the trucks, and the pay — we just need the driver.",
        f"At {company} in {city_state}, we believe good drivers deserve a good company. We're hiring OTR professionals for consistent routes, weekly pay, and a team that backs you up.",
        f"{company} is adding drivers to our team. We run all 48 states from our base in {city_state}. If you want consistent freight and a company that doesn't play games, this is it.",
        f"We're a {city_state} carrier that's growing the right way. {company} needs experienced drivers who want reliable work, competitive pay, and a dispatch team that respects their time.",
        f"No fluff, no empty promises. {company} is hiring CDL-A drivers out of {city_state} for OTR routes. Here's exactly what the job looks like and what you'll earn.",
        f"{company} runs clean, consistent freight out of {city_state}. We need another dependable driver who wants stable work and fair treatment. The details are below.",
        f"Drivers at {company} get treated right. We're a growing operation in {city_state} looking for experienced OTR professionals. If you want honest work with honest pay, read on.",
        f"Simple pitch: {company} needs drivers. We run OTR dry van freight out of {city_state}, pay weekly, and don't make you beg for home time. Interested? Keep reading.",
        f"{company} out of {city_state} is looking for CDL-A drivers who want to work for a carrier that values their time, their safety, and their paycheck. Here's what we're offering.",
        f"We're not the biggest carrier, but we're one of the best to work for. {company} is hiring out of {city_state} and we treat our drivers like the professionals they are.",
        f"Steady freight. Good pay. Real home time. That's {company} in three phrases. We're hiring CDL-A drivers from our {city_state} base for OTR routes across the lower 48.",
        f"If you've been through carriers that don't deliver on their promises, give {company} a shot. We operate out of {city_state} and we mean what we say — about pay, about home time, about everything.",
        f"{company} is a carrier worth driving for. Headquartered in {city_state}, we provide consistent OTR freight, competitive weekly pay, and a support team that actually supports.",
        f"CDL-A drivers wanted at {company}. We haul freight across all 48 states from {city_state} with weekly pay, real benefits, and a team that has your back every mile.",
    ]

    # 30 duties/responsibilities variations
    duties_sets = [
        ["Operate a company truck on OTR routes across the lower 48 states",
         "Pick up and deliver freight safely and on schedule",
         "Complete pre-trip and post-trip inspections per DOT regulations",
         "Communicate with dispatch for load assignments and route updates",
         "Maintain accurate logs and comply with all FMCSA/DOT requirements",
         "Handle all freight as no-touch"],
        ["Drive company equipment on over-the-road routes throughout the continental U.S.",
         "Make timely pickups and deliveries while maintaining a professional standard",
         "Perform thorough vehicle inspections before and after each trip",
         "Stay in regular contact with dispatch regarding load status and ETAs",
         "Keep electronic logs accurate and up to date per federal regulations",
         "Manage no-touch dry van freight from origin to destination"],
        ["Haul dry van freight on long-distance routes across 48 states",
         "Execute safe, on-time pickups and deliveries for every load",
         "Run full pre-trip and post-trip inspections in compliance with DOT",
         "Coordinate with dispatch on routing, load details, and schedule changes",
         "Maintain all required documentation and logs per FMCSA guidelines",
         "Ensure all cargo is handled with care — no-touch freight"],
        ["Transport goods across the country on OTR routes using company equipment",
         "Deliver freight on time while prioritizing safety at every stop",
         "Conduct daily vehicle inspections as required by DOT regulations",
         "Work closely with dispatch to stay on schedule and adjust routes as needed",
         "Keep all driving logs current and compliant with federal requirements",
         "Handle freight professionally — all loads are no-touch"],
        ["Run OTR routes covering the lower 48 states in a company truck",
         "Ensure all pickups and deliveries happen safely and on time",
         "Complete required vehicle inspections before hitting the road and after each haul",
         "Maintain open communication with dispatch for assignments and updates",
         "Stay compliant with FMCSA hours-of-service rules and log requirements",
         "Manage no-touch freight with professionalism and care"],
        ["Operate over-the-road on assigned routes across the United States",
         "Pick up loads and deliver them within the scheduled timeframe",
         "Inspect your vehicle daily per DOT pre-trip and post-trip requirements",
         "Check in with dispatch regularly for load assignments and routing changes",
         "Maintain accurate electronic logs in compliance with federal law",
         "All freight is no-touch — you drive, we handle the rest"],
        ["Drive a company-assigned truck on nationwide OTR routes",
         "Handle freight pickups and deliveries on schedule, every time",
         "Conduct thorough inspections on your vehicle before and after each trip",
         "Communicate proactively with dispatch about load progress and any issues",
         "Ensure all hours-of-service logs are accurate and compliant",
         "Freight is strictly no-touch — focus on driving safely"],
        ["Move dry van freight across all 48 states on company equipment",
         "Arrive on time for pickups and deliver on schedule without exception",
         "Run daily vehicle inspections per DOT standards",
         "Keep dispatch informed on your location, load status, and any delays",
         "Log your hours accurately using electronic logging devices",
         "Handle all loads as no-touch freight"],
        ["Take the wheel on OTR routes covering the continental U.S.",
         "Make every pickup and delivery count — safely and on time",
         "Inspect your truck thoroughly before departure and after arrival",
         "Stay connected with dispatch for real-time load management",
         "Comply with all FMCSA regulations including HOS and logging requirements",
         "No-touch freight only — your job is to drive"],
        ["Haul loads coast to coast on assigned OTR routes",
         "Deliver freight to its destination safely and within the agreed timeline",
         "Perform detailed vehicle inspections as part of your daily routine",
         "Coordinate with dispatch on scheduling, routing, and load specifics",
         "Keep electronic logs accurate and maintain full regulatory compliance",
         "Handle no-touch freight with the professionalism it deserves"],
    ]

    # 30 requirements variations
    reqs_sets = [
        [f"Valid Class A CDL", f"Minimum {min_exp} of OTR experience", "Clean MVR — no major violations in the past 3 years",
         "Current DOT medical card", "Must pass drug screen and background check", "Must be at least 21 years of age", "Authorized to work in the United States"],
        [f"Class A CDL required", f"At least {min_exp} of verifiable OTR driving experience", "No major moving violations in the last 3 years",
         "Valid DOT medical certificate", "Able to pass pre-employment drug test and background check", "21 years of age or older", "Legal authorization to work in the U.S."],
        [f"Hold a valid CDL Class A license", f"{min_exp} or more of recent OTR experience", "Clean driving record — no serious violations within 3 years",
         "DOT medical card must be current", "Willing to complete drug screening and background verification", "Minimum age: 21", "Must be authorized to work in the United States"],
        [f"Active Class A CDL", f"Minimum of {min_exp} driving OTR", "MVR must be clean — no major infractions in the past 3 years",
         "Current and valid DOT physical", "Pre-employment drug screen and background check required", "At least 21 years old", "U.S. work authorization required"],
        [f"CDL-A license in good standing", f"At least {min_exp} behind the wheel on OTR routes", "Driving record free of major violations for the past 3 years",
         "DOT medical card that's up to date", "Must clear drug test and background screening", "21+ years of age", "Legally eligible to work in the United States"],
        [f"Valid CDL Class A", f"A minimum of {min_exp} of OTR driving experience", "Clean MVR with no major violations within 36 months",
         "Current DOT medical certification", "Subject to drug screen and background check", "Must be 21 or older", "Work authorization in the U.S. is required"],
        [f"Class A Commercial Driver's License", f"OTR experience: {min_exp} minimum", "Safe driving history — no serious violations in the last 3 years",
         "Valid and current DOT medical card", "Drug test and background check are part of the hiring process", "Minimum age requirement: 21", "Must have U.S. work authorization"],
        [f"You'll need a CDL-A", f"{min_exp} of OTR experience, minimum", "A clean MVR going back 3 years — no major violations",
         "A current DOT physical on file", "Willingness to pass a drug screen and background check", "You must be at least 21", "Legal right to work in the U.S."],
        [f"CDL Class A — active and valid", f"Verifiable OTR experience of at least {min_exp}", "No major violations on your driving record in the past 3 years",
         "Current DOT medical examiner's certificate", "Pre-employment drug and background screening required", "Age 21 or above", "Authorized to work in the United States"],
        [f"A valid Class A CDL is non-negotiable", f"We need at least {min_exp} of OTR time", "Your MVR needs to be clean — no major issues in the past 3 years",
         "DOT medical card must be current", "Standard drug screen and background check apply", "21 years old minimum", "Must be eligible to work in the U.S."],
    ]

    style = random.choice(section_styles)
    intro = random.choice(intros)
    duties = random.choice(duties_sets)
    reqs = random.choice(reqs_sets)

    duties_md = "\n".join(f"- {d}" for d in duties)
    reqs_md = "\n".join(f"- {r}" for r in reqs)
    perks_md = "\n".join(f"- {p}" for p in perks)

    md = f"""# {job_title} — {company}

**Location:** {city_state} (OTR — All 48 States)
**Job Type:** Full-Time
**Pay:** {pay_range} (based on experience)

---

{intro}

## {style["duties"]}

{duties_md}

## {style["reqs"]}

{reqs_md}

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


