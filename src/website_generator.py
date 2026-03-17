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


# ── Template-based website generation ─────────────────
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# Original company info baked into each template — used for find-and-replace
_TEMPLATE_ORIGINALS = {
    "collaborationlogisticsllc": {
        "company": "Collaboration Logistics LLC",
        "company_upper": "COLLABORATION LOGISTICS LLC",
        "company_short": "Collaboration Logistics",
        "domain": "collaborationlogisticsllc.com",
        "email": "antwann@collaborationlogisticsllc.com",
        "email_prefix": "antwann",
        "address": "3450 Forrest Park Rd SE Apt 2202",
        "city": "Atlanta, GA",
    },
    "g17corp": {
        "company": "G17 Corp",
        "company_upper": "G17 CORP",
        "company_short": "G17 Corp",
        "domain": "g17corp.com",
        "email": "russell@g17corp.com",
        "email_prefix": "russell",
        "address": "3052 Sagebrook Dr",
        "city": "Miamisburg, OH",
    },
    "matthewlogisticsllc": {
        "company": "Matthew Logistics LLC",
        "company_upper": "MATTHEW LOGISTICS LLC",
        "company_short": "Matthew Logistics",
        "domain": "matthewlogisticsllc.com",
        "email": "yuliet@matthewlogisticsllc.com",
        "email_prefix": "yuliet",
        "address": "14214 Duncannon Dr",
        "city": "Houston, TX",
    },
    "woodennickelfreightlogisticsllc": {
        "company": "Wooden Nickel Freight & Logistics LLC",
        "company_upper": "WOODEN NICKEL FREIGHT & LOGISTICS LLC",
        "company_short": "Wooden Nickel Freight",
        "domain": "woodennickelfreightlogisticsllc.com",
        "email": "jordan@woodennickelfreightlogisticsllc.com",
        "email_prefix": "jordan",
        "address": "918 Akers Ridge Dr SE Ste 112",
        "city": "Atlanta, GA",
    },
    "1guy1girl1truckllc": {
        "company": "1 Guy 1 Girl 1 Truck LLC",
        "company_upper": "1 GUY 1 GIRL 1 TRUCK LLC",
        "company_short": "1 Guy 1 Girl 1 Truck",
        "domain": "1guy1girl1truckllc.com",
        "email": "precious@1guy1girl1truckllc.com",
        "email_prefix": "precious",
        "address": "1234 N Kenilworth Ave",
        "city": "Oak Park, IL",
    },
    "oevtransportationllc": {
        "company": "OEV Transportation LLC",
        "company_upper": "OEV TRANSPORTATION LLC",
        "company_short": "OEV Transportation",
        "domain": "oevtransportationllc.com",
        "email": "beard@oevtransportationllc.com",
        "email_prefix": "beard",
        "address": "13 Forest Wood Ln",
        "city": "Park Forest, IL",
    },
    "paramountinvestments1llc": {
        "company": "Paramount Investments 1 LLC",
        "company_upper": "PARAMOUNT INVESTMENTS 1 LLC",
        "company_short": "Paramount Investments 1",
        "domain": "paramountinvestments1llc.com",
        "email": "liam@paramountinvestments1llc.com",
        "email_prefix": "liam",
        "address": "",
        "city": "Houston, TX",
    },
    "phenomenalstarlogisticsllc": {
        "company": "Phenomenal Star Logistics LLC",
        "company_upper": "PHENOMENAL STAR LOGISTICS LLC",
        "company_short": "Phenomenal Star Logistics",
        "domain": "phenomenalstarlogisticsllc.com",
        "email": "james@phenomenalstarlogisticsllc.com",
        "email_prefix": "james",
        "address": "",
        "city": "Atlanta, GA",
    },
    "squarebidnessllc": {
        "company": "Square Bid-ness LLC",
        "company_upper": "SQUARE BID-NESS LLC",
        "company_short": "SQUARE BID-NESS",
        "domain": "squarebid-nessllc.com",
        "email": "austin@squarebid-nessllc.com",
        "email_prefix": "austin",
        "address": "7137 Rittenhouse Village Ct",
        "city": "Houston, TX",
    },
}


def generate_website_from_template(info: dict) -> str:
    """
    Pick a random template, replace company info, and return path to new zip.
    Uses the same info dict as generate_website().
    """
    # Get available templates
    available = [d for d in _TEMPLATE_ORIGINALS if (_TEMPLATES_DIR / d / "index.html").exists()]
    if not available:
        # Fallback to the original generator if no templates found
        return generate_website(info)

    template_name = random.choice(available)
    original = _TEMPLATE_ORIGINALS[template_name]
    template_dir = _TEMPLATES_DIR / template_name

    # Read the template HTML
    with open(template_dir / "index.html", "r", encoding="utf-8") as f:
        html = f.read()

    # New company info from user input
    new_company = info["company_name"]
    new_domain = info["domain"]
    new_email = info["email"]
    new_email_prefix = new_email.split("@")[0] if "@" in new_email else new_email
    new_address = info.get("address", "")
    new_city = info.get("city_state", "")
    new_short = info.get("company_short", new_company)

    # ── Replace company-specific strings (order matters — longest first) ──

    # Email (full email first, then prefix alone in email contexts)
    if original["email"]:
        html = html.replace(original["email"], new_email)
    # Domain references
    if original["domain"]:
        html = html.replace(original["domain"], new_domain)

    # Company name — replace all case variants (longest first to avoid partial matches)
    if original["company_upper"]:
        html = html.replace(original["company_upper"], new_company.upper())
        html = html.replace(original["company_upper"].replace("&", "&amp;"), new_company.upper().replace("&", "&amp;"))
    if original["company"]:
        html = html.replace(original["company"], new_company)
        html = html.replace(original["company"].title(), new_company)
        html = html.replace(original["company"].replace("&", "&amp;"), new_company.replace("&", "&amp;"))
    # Short/logo name (e.g. "Collaboration Logistics" without "LLC")
    orig_short = original.get("company_short", "")
    if orig_short and orig_short != original["company"]:
        html = html.replace(orig_short, new_short)
    # Also replace the shortest recognizable company name fragment
    # e.g. "Wooden Nickel" from "Wooden Nickel Freight"
    orig_words = original["company"].replace("&", "").split()
    # Try progressively shorter prefixes (min 2 words) to catch alt text etc.
    for length in range(len(orig_words) - 1, 1, -1):
        fragment = " ".join(orig_words[:length]).strip()
        if len(fragment) >= 6 and fragment in html:
            html = html.replace(fragment, new_short)
            break

    # Address
    if original["address"] and new_address:
        html = html.replace(original["address"], new_address)

    # City
    if original["city"] and new_city:
        html = html.replace(original["city"], new_city)

    # Copyright year
    html = html.replace("&copy; 2025", "&copy; 2026")
    html = html.replace("© 2025", "© 2026")

    # ── Replace template image references with stock image names ──
    # Templates use: truck1.jpg, truck2.jpg, pic1.png, pic2.png, Truck4.jpg, truck3.jpg
    # Stock images: hero_*.jpg, about_*.jpg, coverage_*.jpg
    hero_img = random.choice(_HERO_IMAGES).name if _HERO_IMAGES else "hero_1.jpg"
    about_img = random.choice(_ABOUT_IMAGES).name if _ABOUT_IMAGES else "about_11.jpg"
    coverage_img = random.choice(_COVERAGE_IMAGES).name if _COVERAGE_IMAGES else "coverage_21.jpg"
    # Pick a second unique about and coverage image
    about_img2 = random.choice([i.name for i in _ABOUT_IMAGES if i.name != about_img]) if len(_ABOUT_IMAGES) > 1 else about_img
    hero_img2 = random.choice([i.name for i in _HERO_IMAGES if i.name != hero_img]) if len(_HERO_IMAGES) > 1 else hero_img

    # Map template image names to stock images
    html = html.replace("images/truck1.jpg", f"images/{hero_img}")
    html = html.replace("images/truck2.jpg", f"images/{about_img}")
    html = html.replace("images/truck3.jpg", f"images/{coverage_img}")
    html = html.replace("images/Truck4.jpg", f"images/{about_img2}")
    html = html.replace("images/pic1.png", f"images/{hero_img2}")
    html = html.replace("images/pic2.png", f"images/{coverage_img}")

    # ── Package into zip ──
    tmp_dir = tempfile.mkdtemp()

    # Write modified HTML
    with open(os.path.join(tmp_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

    # Copy stock images (not template images)
    dest_images = os.path.join(tmp_dir, "images")
    os.makedirs(dest_images, exist_ok=True)
    used_images = {hero_img, about_img, coverage_img, about_img2, hero_img2}
    for img_name in used_images:
        src = _ASSETS_DIR / img_name
        if src.exists():
            shutil.copy2(str(src), os.path.join(dest_images, img_name))

    # Create zip
    zip_name = f"{new_domain.replace('.', '_')}_website.zip"
    zip_path = os.path.join(tempfile.mkdtemp(), zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(tmp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, tmp_dir)
                zf.write(file_path, arcname)

    # Cleanup temp dir
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return zip_path


def generate_job_description(info: dict) -> str:
    """Generate a unique Indeed job description as HTML fragments for rich-text pasting."""
    company = info["company_name"]
    city_state = info["city_state"]
    job_title = info["job_title"]
    pay_range = info["pay_range"]
    home_time = info.get("home_time", "Home every 2 weeks for 2 days")
    perks = info.get("perks", [])
    min_exp = info.get("min_experience", "6 months")

    # ── Tone ─────────────────────────────────────────────────────────────────
    tone = random.choice(["direct", "professional", "conversational"])

    # ── 30 section title styles ───────────────────────────────────────────────
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

    # ── 30 intro paragraphs ───────────────────────────────────────────────────
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

    # ── Duties pools (one per tone, 6 items each — drop 1-2 randomly) ─────────
    duties_pool = {
        "direct": [
            "Drive OTR. Cover all 48 states. Stay on schedule.",
            "Pick up loads and deliver them — safely, on time, every run.",
            "Pre-trip and post-trip inspections. Every single day. No exceptions.",
            "Check in with dispatch. Keep them posted. Don't go dark.",
            "Keep your ELD logs clean and current. Federal law, not optional.",
            "No-touch freight. Your only job is getting it there in one piece.",
            "Report any equipment issues immediately — don't nurse a sick truck down the road.",
            "Follow load instructions to the letter. Pickups, deliveries, paperwork.",
        ],
        "professional": [
            f"Operate a company-assigned Class A vehicle on over-the-road routes throughout the continental United States",
            "Execute safe, timely freight pickups and deliveries in accordance with customer requirements and company standards",
            "Conduct thorough pre-trip and post-trip vehicle inspections as mandated by DOT regulations",
            "Maintain consistent communication with the dispatch team regarding load status, ETAs, and any route adjustments",
            "Ensure full compliance with FMCSA Hours of Service rules and maintain accurate electronic logs at all times",
            "Handle no-touch dry van freight with care and professionalism from origin to final destination",
            "Document and report all equipment defects, incidents, or service delays in a timely and accurate manner",
            "Adhere to all federal, state, and local transportation regulations throughout each assignment",
        ],
        "conversational": [
            "You'll be running OTR across the lower 48 — we've got freight everywhere so the miles stay consistent",
            "Pick up your loads, deliver them on time, treat the customer's dock like your own — that's the standard",
            "Do your pre-trip and post-trip every day — it protects you and the equipment, no shortcuts",
            "Stay in touch with your dispatcher — they're in your corner and communication keeps everyone moving",
            "Keep your ELD logs accurate — we run a clean operation and expect the same from our drivers",
            "It's all no-touch freight — back in, drop and hook or live unload depending on the customer, you stay in the cab",
            "If something's wrong with your truck, speak up — we'd rather fix it in a shop than on the side of I-80",
            "Follow load-specific instructions when they come up — sometimes there's a window, a contact name, or a special procedure",
        ],
    }

    # ── Requirements pools (one per tone) ────────────────────────────────────
    # Optional items (age, work auth) sometimes included
    reqs_pool = {
        "direct": {
            "core": [
                f"CDL-A. Valid. No exceptions.",
                f"{min_exp} OTR experience, minimum.",
                "Clean MVR — no majors in the last 3 years.",
                "Current DOT medical card.",
                "Pass the drug screen and background check.",
            ],
            "optional": [
                "21 or older.",
                "Must be authorized to work in the U.S.",
                "No SAP drivers. Must be fully cleared.",
            ],
        },
        "professional": {
            "core": [
                f"Valid Class A Commercial Driver's License (CDL-A)",
                f"Minimum of {min_exp} verifiable over-the-road driving experience",
                "Clean driving record — no major violations within the past 36 months",
                "Current DOT medical examiner's certificate",
                "Ability to successfully complete pre-employment drug screening and background verification",
            ],
            "optional": [
                "Must be 21 years of age or older",
                "Must be legally authorized to work in the United States",
                "No active SAP program participation — must be fully return-to-duty cleared",
            ],
        },
        "conversational": {
            "core": [
                f"You'll need a valid CDL-A — active and in good standing",
                f"At least {min_exp} of OTR experience under your belt",
                "A clean MVR — no DUIs, reckless driving, or major violations in the past 3 years",
                "Current DOT physical on file",
                "You'll need to pass a drug screen and background check before you start",
            ],
            "optional": [
                "Must be 21+ — that's federal, not our rule",
                "You need to be legally allowed to work in the U.S.",
                "If you've been through SAP, you'll need to be fully cleared before applying",
            ],
        },
    }

    # ── "Why Drivers Stay" culture bullets ───────────────────────────────────
    culture_bullets = [
        f"Dispatch team that picks up the phone and actually helps",
        f"Freight that keeps moving — no sitting at the yard waiting for loads",
        f"Equipment that's maintained — we don't ask you to drive junk",
        f"A team that treats drivers like the professionals they are",
        f"Consistent lanes so you know what to expect week to week",
        f"A safety culture that's real, not just a poster on the wall",
        f"Direct deposit every Friday without fail",
        f"No micromanaging — do your job, get your miles, go home",
        f"Recruiters who are straight with you from day one",
        f"A company that's been around long enough to know what drivers need",
    ]

    # ── "About {company}" blurbs ──────────────────────────────────────────────
    about_blurbs = [
        f"{company} is a privately held trucking company based in {city_state}. We specialize in dry van OTR freight and have built our reputation on consistent loads, reliable pay, and treating drivers with respect. We're not a mega-carrier — and that's by design.",
        f"Founded and operated out of {city_state}, {company} has been moving freight across the country for years. We run a tight fleet, keep our equipment well-maintained, and invest in the drivers who keep our operation moving. Small enough to care, large enough to keep you rolling.",
        f"{company} started in {city_state} with a simple idea: run freight the right way. That means good equipment, honest pay, and a dispatch team that has your back. We've grown steadily by doing exactly that — and we're not stopping now.",
        f"We're a {city_state}-based carrier that believes in doing things the right way — fair pay, honest communication, and freight that actually moves. {company} isn't trying to be the biggest name in trucking. We just want to be the best one to work for.",
        f"{company} operates out of {city_state} and runs dry van freight coast to coast. We're a close-knit operation where every driver matters and every mile gets paid. If you've been burned by big carriers before, you'll notice the difference here.",
    ]

    # ── "Apply Today" CTAs ────────────────────────────────────────────────────
    apply_ctas = [
        f"Ready to make a move? Apply today and a member of our recruiting team will reach out within 24 hours. We make the process straightforward — no runaround, no bait-and-switch.",
        f"If {company} sounds like the right fit, don't wait. Apply now and let's talk. We respect your time and we'll give you a straight answer on whether this works for both of us.",
        f"Applying takes two minutes. If you meet the qualifications and want consistent work with a carrier that delivers on its promises, hit apply and we'll be in touch.",
        f"Take the next step. Apply today and connect with our team in {city_state}. We're hiring now and we move fast for qualified drivers.",
        f"Don't let this one sit in your browser. Apply today — our team reviews applications daily and we'll get back to you fast.",
    ]

    # ── EEO statements (5 variations) ────────────────────────────────────────
    eeo_statements = [
        f"{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, veteran status, sexual orientation, gender identity, or any other characteristic protected by applicable federal, state, or local law.",
        f"{company} provides equal employment opportunities to all applicants and employees without regard to race, color, religion, gender, national origin, age, disability, sexual orientation, gender identity, veteran status, or any other legally protected status.",
        f"We are an equal opportunity employer. Employment decisions at {company} are made without regard to race, color, religion, sex, national origin, age, disability, genetic information, veteran status, sexual orientation, or gender identity.",
        f"{company} is committed to a diverse and inclusive workplace. We do not discriminate on the basis of race, color, religion, sex, national origin, age, disability, veteran status, or any other characteristic protected by law. All qualified candidates are encouraged to apply.",
        f"Equal Opportunity Employer — {company} does not discriminate on the basis of race, sex, color, religion, age, national origin, marital status, disability, veteran status, genetic information, sexual orientation, gender identity, or any other reason prohibited by law in the provision of employment opportunities and benefits.",
    ]

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _ul(items):
        return "<ul>\n" + "".join(f"<li>{i}</li>\n" for i in items) + "</ul>"

    def _section(title, content_html):
        return f"<p><b>{title}</b></p>\n{content_html}"

    # ── Build intro (vary length: 1 sentence vs full paragraph) ──────────────
    raw_intro = random.choice(intros)
    sentences = [s.strip() for s in raw_intro.replace("—", " — ").split(". ") if s.strip()]
    if len(sentences) >= 3 and random.random() < 0.3:
        intro_text = sentences[0] + "."
    else:
        intro_text = raw_intro
    intro_html = f"<p>{intro_text}</p>"

    # ── Build duties section ──────────────────────────────────────────────────
    style = random.choice(section_styles)
    all_duties = duties_pool[tone][:]
    random.shuffle(all_duties)
    drop = random.randint(1, 2)
    duties = all_duties[: max(4, len(all_duties) - drop)]

    # ── Build requirements section ────────────────────────────────────────────
    pool = reqs_pool[tone]
    core_reqs = pool["core"][:]
    optional_reqs = pool["optional"][:]
    random.shuffle(optional_reqs)
    num_optional = random.randint(0, len(optional_reqs))
    reqs = core_reqs + optional_reqs[:num_optional]

    # ── Build pay section (3 presentation styles) ────────────────────────────
    pay_style = random.randint(0, 2)
    if pay_style == 0:
        # pay range as first bullet
        pay_bullets = [f"{pay_range} weekly"] + perks
        pay_title = style["pay"]
        pay_html = _section(pay_title, _ul(pay_bullets))
    elif pay_style == 1:
        # intro sentence before bullet list
        pay_title = style["pay"]
        pay_intro = f"<p>Competitive weekly pay: <b>{pay_range}</b></p>"
        pay_html = f"<p><b>{pay_title}</b></p>\n{pay_intro}\n{_ul(perks) if perks else ''}"
    else:
        # pay embedded in section heading
        pay_title = f"{style['pay']} ({pay_range}/wk)"
        pay_html = _section(pay_title, _ul(perks) if perks else "<p>Competitive pay discussed during hiring process.</p>")

    # ── Build schedule section (3 presentation styles) ────────────────────────
    sched_style = random.randint(0, 2)
    if sched_style == 0:
        sched_html = _section(style["schedule"], _ul([
            home_time,
            "OTR routes across all 48 states",
            "Full-time, consistent freight year-round",
        ]))
    elif sched_style == 1:
        sched_paragraph = (
            f"Drivers at {company} run OTR across all 48 states. "
            f"{home_time}. "
            f"This is a full-time position with consistent freight year-round — no seasonal slowdowns."
        )
        sched_html = f"<p><b>{style['schedule']}</b></p>\n<p>{sched_paragraph}</p>"
    else:
        sched_paragraph = f"We run OTR across the continental U.S. out of {city_state}. Freight is consistent and full-time."
        sched_html = (
            f"<p><b>{style['schedule']}</b></p>\n"
            f"<p>{sched_paragraph}</p>\n"
            + _ul([home_time, "All 48 states"])
        )

    # ── Optional extra sections (0-2 of 3 possible) ──────────────────────────
    extras_available = []

    # "Why Drivers Stay"
    stay_bullets = random.sample(culture_bullets, k=random.randint(3, 4))
    stay_html = _section("Why Drivers Stay", _ul(stay_bullets))
    extras_available.append(stay_html)

    # "About {company}"
    about_html = f"<p><b>About {company}</b></p>\n<p>{random.choice(about_blurbs)}</p>"
    extras_available.append(about_html)

    # "Apply Today"
    apply_html = f"<p><b>Apply Today</b></p>\n<p>{random.choice(apply_ctas)}</p>"
    extras_available.append(apply_html)

    random.shuffle(extras_available)
    num_extras = random.randint(0, 2)
    chosen_extras = extras_available[:num_extras]

    # ── EEO ──────────────────────────────────────────────────────────────────
    eeo_html = f"<p><i>{random.choice(eeo_statements)}</i></p>"

    # ── Section order (intro always first, EEO always last) ──────────────────
    core_sections = [
        ("duties",   _section(style["duties"], _ul(duties))),
        ("reqs",     _section(style["reqs"],   _ul(reqs))),
        ("pay",      pay_html),
        ("schedule", sched_html),
    ]
    orders = [
        ["duties", "reqs",     "pay",      "schedule"],
        ["pay",    "duties",   "reqs",     "schedule"],
        ["schedule","duties",  "pay",      "reqs"],
        ["reqs",   "duties",   "pay",      "schedule"],
    ]
    chosen_order = random.choice(orders)
    section_map = {k: v for k, v in core_sections}
    ordered_sections = [section_map[k] for k in chosen_order]

    # Inject extras before EEO (spread them around the ordered sections)
    all_parts = [intro_html] + ordered_sections + chosen_extras + [eeo_html]

    return "\n\n".join(all_parts)


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

    hero_img = random.choice(_HERO_IMAGES).name if _HERO_IMAGES else "hero_1.jpg"
    about_names = [i.name for i in _ABOUT_IMAGES]
    about_img = random.choice(about_names) if about_names else "about_1.jpg"
    about_img2 = random.choice([n for n in about_names if n != about_img]) if len(about_names) > 1 else about_img
    coverage_img = random.choice(_COVERAGE_IMAGES).name if _COVERAGE_IMAGES else "coverage_1.jpg"

    company = info["company_name"]
    short = info.get("company_short", company.split()[0])
    city_state = info.get("city_state", "")

    perks_html = "\n".join(
        f'<div class="perk">{p}</div>' for p in info.get("perks", [])
    )

    about_desc = random.choice(ABOUT_DESCRIPTIONS).format(company=company, city_state=city_state)
    coverage_desc = random.choice(COVERAGE_DESCRIPTIONS).format(company=company, city_state=city_state)
    about_title = random.choice(ABOUT_TITLES)
    about_checklist = random.choice(ABOUT_CHECKLISTS)
    coverage_title = random.choice(COVERAGE_TITLES)
    coverage_checklist = random.choice(COVERAGE_CHECKLISTS)

    city_only = city_state.split(",")[0].strip() if "," in city_state else city_state
    state_only = city_state.split(",")[1].strip().split()[0] if "," in city_state else ""
    hero_desc = info.get(
        "hero_desc",
        f"{company} keeps goods moving across all 48 states with reliable service — out of {city_only}, {state_only}."
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
        f"  <meta name=\"description\" content=\"{company} is hiring CDL-A drivers in {city_state}. OTR dry van freight across 48 states.\">\n"
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
    city_state = ctx["city_state"]
    year = ctx["year"]
    logo = ctx["logo_html"]
    return (
        f"  <footer style=\"background:{navy}; padding:52px 24px 28px; color:#94A3B8;\">\n"
        "    <div style=\"max-width:1200px; margin:0 auto;\">\n"
        "      <div style=\"display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:32px; margin-bottom:40px;\">\n"
        "        <div>\n"
        f"          <div style=\"font-family:'{fh}',sans-serif; font-weight:900; font-size:1.5rem; color:#fff; margin-bottom:10px;\">{logo}</div>\n"
        f"          <p style=\"font-size:0.88rem; max-width:280px; line-height:1.6; color:#94A3B8;\">Professional CDL-A carrier serving all 48 states from {city_state}.</p>\n"
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
        f"              <span style=\"font-size:0.88rem; color:#94A3B8;\">{city_state}</span>\n"
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


# ── HERO VARIANTS ─────────────────────────────────────────────────────────────

def _hero_v1(ctx: dict) -> str:
    """Full-screen truck image, dark overlay, centered text, 3 stat pills at bottom."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; ds = ctx["dark_slate"]
    fh = ctx["font_heading"]; fb = ctx["font_body"]
    nr = _hex_to_rgb(navy); dsr = _hex_to_rgb(ds); pr = _hex_to_rgb(p)
    company = ctx["company_name"]
    return (
        "  <section style=\"position:relative; min-height:100vh; display:flex; align-items:center;"
        " justify-content:center; padding:140px 24px 80px; text-align:center;"
        f" background:url('images/{ctx['hero_img']}') center/cover no-repeat;\">\n"
        f"    <div style=\"position:absolute; inset:0; background:linear-gradient(160deg,rgba({nr},0.9) 0%,rgba({dsr},0.78) 100%);\"></div>\n"
        "    <div style=\"position:relative; z-index:1; max-width:820px; width:100%;\">\n"
        f"      <div class=\"reveal\" style=\"display:inline-flex; align-items:center; gap:8px; background:rgba({pr},0.15);"
        f" border:1px solid rgba({pr},0.35); color:{pl}; font-size:0.75rem; font-weight:700;"
        " padding:6px 18px; border-radius:50px; margin-bottom:28px; letter-spacing:1.5px; text-transform:uppercase;\">\n"
        "        <span style=\"width:8px; height:8px; border-radius:50%; background:#22C55E; display:inline-block; animation:pulse-dot 2s infinite;\"></span>\n"
        "        Now Hiring CDL-A Drivers\n"
        "      </div>\n"
        f"      <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.8rem,6vw,4.8rem);"
        " font-weight:900; color:#fff; line-height:1.06; margin-bottom:22px; letter-spacing:-1.5px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"      <p class=\"reveal\" style=\"font-size:1.15rem; color:rgba(255,255,255,0.65); max-width:560px;"
        f" margin:0 auto 38px; line-height:1.7;\">{ctx['hero_desc']}</p>\n"
        "      <div class=\"reveal\" style=\"display:flex; gap:14px; justify-content:center; flex-wrap:wrap;\">\n"
        "        <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        "        <a href=\"#about\" class=\"btn btn-outline-light\">Learn More</a>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"display:flex; justify-content:center; gap:16px; margin-top:60px; flex-wrap:wrap;\">\n"
        "        <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        " border-radius:50px; padding:10px 24px; color:#fff; font-size:0.88rem; font-weight:600;\">\U0001f5fa\ufe0f 48 States</div>\n"
        "        <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        " border-radius:50px; padding:10px 24px; color:#fff; font-size:0.88rem; font-weight:600;\">\U0001f69a OTR Routes</div>\n"
        "        <div style=\"background:rgba(255,255,255,0.07); border:1px solid rgba(255,255,255,0.12);"
        " border-radius:50px; padding:10px 24px; color:#fff; font-size:0.88rem; font-weight:600;\">\U0001faaa CDL-A Required</div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v2(ctx: dict) -> str:
    """Split 50/50: dark left panel with logo+stats, right truck image."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]; fb = ctx["font_body"]
    pay_val = ctx["pay_range"].split("/")[0].strip()
    return (
        "  <section style=\"min-height:100vh; display:grid; grid-template-columns:1fr 1fr; padding-top:70px;\">\n"
        f"    <div style=\"background:{navy}; display:flex; align-items:center; padding:80px 56px;\">\n"
        "      <div style=\"max-width:480px;\">\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-weight:900; font-size:1.6rem; color:#fff; margin-bottom:48px;\">{ctx['logo_html']}</div>\n"
        f"        <h1 class=\"reveal-left\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.4rem,4vw,3.8rem);"
        " font-weight:900; color:#fff; line-height:1.08; margin-bottom:22px; letter-spacing:-1px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"        <p class=\"reveal-left delay-1\" style=\"font-size:1.05rem; color:rgba(255,255,255,0.6); margin-bottom:36px; line-height:1.7;\">{ctx['hero_desc']}</p>\n"
        "        <div class=\"reveal-left delay-2\">\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        "        </div>\n"
        "        <div class=\"reveal-left delay-3\" style=\"display:flex; flex-direction:column; gap:20px;"
        " margin-top:52px; padding-top:36px; border-top:1px solid rgba(255,255,255,0.08);\">\n"
        f"          <div style=\"display:flex; align-items:center; gap:16px;\">\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:2.2rem; font-weight:900; color:{pl}; min-width:80px;\">{pay_val}</div>\n"
        "            <div style=\"font-size:0.82rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1px;\">Weekly Pay</div>\n"
        "          </div>\n"
        f"          <div style=\"display:flex; align-items:center; gap:16px;\">\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:2.2rem; font-weight:900; color:{pl}; min-width:80px;\">48</div>\n"
        "            <div style=\"font-size:0.82rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1px;\">States Covered</div>\n"
        "          </div>\n"
        f"          <div style=\"display:flex; align-items:center; gap:16px;\">\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:2.2rem; font-weight:900; color:{pl}; min-width:80px;\">24/7</div>\n"
        "            <div style=\"font-size:0.82rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1px;\">Dispatch Support</div>\n"
        "          </div>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        f"    <div style=\"background:url('images/{ctx['hero_img']}') center/cover no-repeat; min-height:500px;\"></div>\n"
        "  </section>\n"
    )


def _hero_v3(ctx: dict) -> str:
    """Shorter hero left-aligned on dark bg, right image, full-width stats bar below."""
    p = ctx["primary"]; navy = ctx["navy"]
    fh = ctx["font_heading"]; fb = ctx["font_body"]
    pay_val = ctx["pay_range"].split("/")[0].strip()
    return (
        f"  <section style=\"background:{navy}; padding:140px 24px 0;\">\n"
        "    <div style=\"max-width:1200px; margin:0 auto; display:grid; grid-template-columns:1fr 1fr;"
        " gap:64px; align-items:center; padding-bottom:72px;\">\n"
        "      <div>\n"
        f"        <span class=\"section-label reveal\">{ctx['sub_tagline']}</span>\n"
        f"        <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.4rem,4.5vw,3.8rem);"
        " font-weight:900; color:#fff; line-height:1.08; margin-bottom:22px; letter-spacing:-1px;\">"
        f"{ctx['tagline']}</h1>\n"
        f"        <p class=\"reveal delay-1\" style=\"font-size:1.05rem; color:rgba(255,255,255,0.6);"
        f" margin-bottom:36px; line-height:1.7; max-width:460px;\">{ctx['hero_desc']}</p>\n"
        "        <div class=\"reveal delay-2\" style=\"display:flex; gap:14px; flex-wrap:wrap;\">\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">Apply Now</a>\n"
        "          <a href=\"#about\" class=\"btn btn-outline-light\">About Us</a>\n"
        "        </div>\n"
        "      </div>\n"
        "      <div class=\"reveal-right\" style=\"border-radius:12px; overflow:hidden; box-shadow:0 24px 64px rgba(0,0,0,0.4);\">\n"
        f"        <img src=\"images/{ctx['hero_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:420px; object-fit:cover;\">\n"
        "      </div>\n"
        "    </div>\n"
        f"    <div style=\"background:{p}; padding:28px 24px;\">\n"
        "      <div style=\"max-width:1100px; margin:0 auto; display:grid; grid-template-columns:repeat(4,1fr); gap:20px; text-align:center;\">\n"
        f"        <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:#fff;\">{pay_val}</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.7); text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">Weekly Pay</div></div>\n"
        f"        <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:#fff;\">{ctx['home_time_short']}</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.7); text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">Home Time</div></div>\n"
        f"        <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:#fff;\">{ctx['min_experience']}</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.7); text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">Min. Experience</div></div>\n"
        f"        <div><div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:900; color:#fff;\">{ctx['routes']}</div>"
        f"<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.7); text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">{ctx['routes_type']}</div></div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v4(ctx: dict) -> str:
    """Announcement bar, full-screen hero, centered with 'Now Hiring' badge and large stats."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; ds = ctx["dark_slate"]
    fh = ctx["font_heading"]; fb = ctx["font_body"]
    nr = _hex_to_rgb(navy); dsr = _hex_to_rgb(ds)
    city_state = ctx["city_state"]
    pay_val = ctx["pay_range"].split("/")[0].strip()
    return (
        f"  <div style=\"background:{p}; padding:10px 24px; text-align:center; position:fixed; top:70px; width:100%; z-index:900;\">\n"
        f"    <span style=\"font-family:'{fh}',sans-serif; font-size:0.82rem; font-weight:700; color:#fff; letter-spacing:0.5px;\">\n"
        f"      \U0001f69b Now Hiring CDL-A Drivers &mdash; {city_state} &mdash;"
        " <a href=\"#careers\" style=\"color:#fff; text-decoration:underline;\">Apply Today</a>\n"
        "    </span>\n"
        "  </div>\n"
        "  <section style=\"position:relative; min-height:100vh; display:flex; align-items:center;"
        " justify-content:center; padding:170px 24px 80px; text-align:center;"
        f" background:url('images/{ctx['hero_img']}') center/cover no-repeat;\">\n"
        f"    <div style=\"position:absolute; inset:0; background:linear-gradient(180deg,rgba({nr},0.85) 0%,rgba({dsr},0.92) 100%);\"></div>\n"
        "    <div style=\"position:relative; z-index:1; max-width:760px; width:100%;\">\n"
        f"      <div class=\"reveal\" style=\"display:inline-block; background:{p}; color:#fff;"
        f" font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:800;"
        " padding:7px 22px; border-radius:50px; margin-bottom:28px; letter-spacing:2px; text-transform:uppercase;\">\u2736 Now Hiring \u2736</div>\n"
        f"      <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.8rem,6vw,5rem);"
        f" font-weight:900; color:#fff; line-height:1.05; margin-bottom:22px; letter-spacing:-1.5px;\">{ctx['tagline']}</h1>\n"
        f"      <p class=\"reveal delay-1\" style=\"font-size:1.12rem; color:rgba(255,255,255,0.62);"
        f" margin:0 auto 40px; max-width:540px; line-height:1.7;\">{ctx['hero_desc']}</p>\n"
        "      <div class=\"reveal delay-2\" style=\"display:flex; gap:14px; justify-content:center; flex-wrap:wrap;\">\n"
        "        <a href=\"#careers\" class=\"btn btn-primary\" style=\"font-size:1rem; padding:16px 40px;\">Apply Now &mdash; CDL-A</a>\n"
        "      </div>\n"
        "      <div class=\"reveal delay-3\" style=\"display:flex; justify-content:center; gap:40px; margin-top:56px; flex-wrap:wrap;\">\n"
        f"        <div style=\"text-align:center;\"><div style=\"font-family:'{fh}',sans-serif; font-size:2.4rem; font-weight:900; color:{pl};\">{pay_val}</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1.5px; margin-top:6px;\">Per Week</div></div>\n"
        "        <div style=\"width:1px; background:rgba(255,255,255,0.1);\"></div>\n"
        f"        <div style=\"text-align:center;\"><div style=\"font-family:'{fh}',sans-serif; font-size:2.4rem; font-weight:900; color:{pl};\">48</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1.5px; margin-top:6px;\">States</div></div>\n"
        "        <div style=\"width:1px; background:rgba(255,255,255,0.1);\"></div>\n"
        f"        <div style=\"text-align:center;\"><div style=\"font-family:'{fh}',sans-serif; font-size:2.4rem; font-weight:900; color:{pl};\">{ctx['home_time_short']}</div>"
        "<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.45); text-transform:uppercase; letter-spacing:1.5px; margin-top:6px;\">Home Time</div></div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _hero_v5(ctx: dict) -> str:
    """Minimal clean: light bg, large company name, accent tagline, truck card below."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]; fb = ctx["font_body"]
    company = ctx["company_name"]
    return (
        f"  <section style=\"background:{abl}; padding:140px 24px 0; overflow:hidden;\">\n"
        "    <div style=\"max-width:1100px; margin:0 auto;\">\n"
        "      <div style=\"text-align:center; margin-bottom:56px;\">\n"
        f"        <div class=\"reveal\" style=\"display:inline-block; background:{ab}; color:{p};"
        f" font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:800;"
        " padding:7px 20px; border-radius:50px; margin-bottom:24px; letter-spacing:2px; text-transform:uppercase;\">CDL-A Positions Open</div>\n"
        f"        <h1 class=\"reveal\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(2.2rem,5vw,4rem);"
        f" font-weight:900; color:{navy}; line-height:1.08; margin-bottom:4px; letter-spacing:-1px;\">{company}</h1>\n"
        f"        <div class=\"reveal delay-1\" style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.3rem,3vw,2.2rem);"
        f" font-weight:700; color:{p}; margin-bottom:24px;\">{ctx['tagline']}</div>\n"
        f"        <p class=\"reveal delay-2\" style=\"font-size:1.05rem; color:#64748B; max-width:520px;"
        f" margin:0 auto 36px; line-height:1.72;\">{ctx['hero_desc']}</p>\n"
        "        <div class=\"reveal delay-3\">\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\" style=\"font-size:1rem; padding:15px 40px;\">View Open Positions</a>\n"
        "        </div>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"border-radius:16px 16px 0 0; overflow:hidden; box-shadow:0 -8px 48px rgba(0,0,0,0.1);\">\n"
        f"        <img src=\"images/{ctx['hero_img']}\" alt=\"{company}\" style=\"width:100%; height:400px; object-fit:cover; display:block;\">\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── PROCESS VARIANTS ──────────────────────────────────────────────────────────

def _process_v1(ctx: dict) -> str:
    """3 horizontal numbered cards on light bg, number in accent circle."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; g50 = ctx["gray_50"]
    navy = ctx["navy"]; fh = ctx["font_heading"]; pr = _hex_to_rgb(p)
    steps = ctx["steps"]
    cards = ""
    for i, (title, desc) in enumerate(steps, 1):
        cards += (
            f"        <div class=\"reveal delay-{i}\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px;"
            f" padding:40px 32px; transition:border-color 0.3s,box-shadow 0.3s,transform 0.3s;\""
            f" onmouseover=\"this.style.borderColor='{p}';this.style.transform='translateY(-5px)';this.style.boxShadow='0 12px 36px rgba({pr},0.1)'\""
            f" onmouseout=\"this.style.borderColor='#E2E8F0';this.style.transform='';this.style.boxShadow=''\">\n"
            f"          <div style=\"width:52px; height:52px; border-radius:50%; background:{ab}; color:{p};"
            f" display:flex; align-items:center; justify-content:center;"
            f" font-family:'{fh}',sans-serif; font-size:1.25rem; font-weight:900; margin-bottom:22px;\">0{i}</div>\n"
            f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:{navy}; margin-bottom:10px;\">{title}</h3>\n"
            f"          <p style=\"font-size:0.94rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "        </div>\n"
        )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:56px;\">\n"
        "        <span class=\"section-label\">How We Work</span>\n"
        "        <h2 class=\"section-heading\">Simple Process. Consistent Results.</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">From first contact to final delivery, we keep it professional every step of the way.</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:24px;\">\n"
        + cards
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v2(ctx: dict) -> str:
    """Dark section, large outlined numbers, arrows between steps."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    items = ""
    for i, (title, desc) in enumerate(steps, 1):
        items += (
            f"        <div class=\"reveal delay-{i}\" style=\"flex:1; text-align:center; padding:40px 24px;\">\n"
            f"          <div style=\"font-family:'{fh}',sans-serif; font-size:5rem; font-weight:900; line-height:1;"
            " color:transparent; -webkit-text-stroke:2px rgba(255,255,255,0.15); margin-bottom:20px;\">"
            f"0{i}</div>\n"
            f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:#fff; margin-bottom:12px;\">{title}</h3>\n"
            f"          <p style=\"font-size:0.92rem; color:rgba(255,255,255,0.55); line-height:1.65;\">{desc}</p>\n"
            "        </div>\n"
        )
        if i < len(steps):
            items += "        <div style=\"color:rgba(255,255,255,0.15); font-size:2rem; align-self:center; margin-top:-32px;\">&rsaquo;</div>\n"
    return (
        f"  <section class=\"section\" style=\"background:{navy};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:60px;\">\n"
        "        <span class=\"section-label\">Our Process</span>\n"
        "        <h2 class=\"section-heading section-heading-light\">How It Works</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto; color:rgba(255,255,255,0.5);\">Three steps. Zero complications.</p>\n"
        "      </div>\n"
        "      <div style=\"display:flex; align-items:flex-start; gap:8px; flex-wrap:wrap;\">\n"
        + items
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v3(ctx: dict) -> str:
    """Vertical left-side timeline with numbered dots, alternating accent colors."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    accent_colors = [p, pl, p]
    rows = ""
    for i, (title, desc) in enumerate(steps, 1):
        ac = accent_colors[(i - 1) % len(accent_colors)]
        line = (
            "            <div style=\"position:absolute; top:44px; left:21px; width:2px;"
            " height:calc(100% + 32px); background:rgba(0,0,0,0.06);\"></div>\n"
        ) if i < len(steps) else ""
        rows += (
            f"          <div class=\"reveal\" style=\"display:flex; gap:28px; position:relative; padding-bottom:{'48' if i < len(steps) else '0'}px;\">\n"
            + line
            + "            <div style=\"flex-shrink:0;\">\n"
            f"              <div style=\"width:44px; height:44px; border-radius:50%; background:{ac}; color:#fff;"
            f" display:flex; align-items:center; justify-content:center;"
            f" font-family:'{fh}',sans-serif; font-size:1rem; font-weight:900; position:relative; z-index:1;\">0{i}</div>\n"
            "            </div>\n"
            "            <div style=\"padding-top:8px;\">\n"
            f"              <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:{navy}; margin-bottom:8px;\">{title}</h3>\n"
            f"              <p style=\"font-size:0.94rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "            </div>\n"
            "          </div>\n"
        )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:80px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        "          <span class=\"section-label\">How We Work</span>\n"
        f"          <h2 class=\"section-heading\">From Your Call to the Final Drop</h2>\n"
        "          <p class=\"section-desc\" style=\"margin-top:12px;\">Our process is built around reliability &mdash; consistent pickups, real-time communication, and on-time delivery every time.</p>\n"
        "        </div>\n"
        "        <div style=\"display:flex; flex-direction:column;\">\n"
        + rows
        + "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v4(ctx: dict) -> str:
    """Light bg, each step as wide horizontal row: huge number | divider | title+desc."""
    p = ctx["primary"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    rows = ""
    for i, (title, desc) in enumerate(steps, 1):
        rows += (
            f"        <div class=\"reveal\" style=\"display:flex; align-items:center; background:#fff;"
            " border:1px solid #E2E8F0; border-radius:12px; overflow:hidden;"
            " transition:box-shadow 0.3s;\""
            " onmouseover=\"this.style.boxShadow='0 8px 28px rgba(0,0,0,0.07)'\""
            " onmouseout=\"this.style.boxShadow=''\">\n"
            f"          <div style=\"background:{abl}; padding:40px 36px; min-width:100px; text-align:center; flex-shrink:0;\">\n"
            f"            <span style=\"font-family:'{fh}',sans-serif; font-size:3.5rem; font-weight:900; color:{p}; line-height:1;\">0{i}</span>\n"
            "          </div>\n"
            "          <div style=\"width:1px; background:#E2E8F0; align-self:stretch;\"></div>\n"
            "          <div style=\"padding:32px 36px;\">\n"
            f"            <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:{navy}; margin-bottom:8px;\">{title}</h3>\n"
            f"            <p style=\"font-size:0.94rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
            "          </div>\n"
            "        </div>\n"
        )
    return (
        "  <section class=\"section\" id=\"process\" style=\"background:#fff;\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">Our Process</span>\n"
        "        <h2 class=\"section-heading\">How We Get It Done</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">Every load handled with professionalism from start to finish.</p>\n"
        "      </div>\n"
        "      <div style=\"display:flex; flex-direction:column; gap:16px; max-width:900px; margin:0 auto;\">\n"
        + rows
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _process_v5(ctx: dict) -> str:
    """Dark bg, 3 emoji icon cards in a row, minimal centered text."""
    p = ctx["primary"]; navy = ctx["navy"]; fh = ctx["font_heading"]
    steps = ctx["steps"]
    icons = ["\U0001f4cb", "\U0001f69a", "\u2705"]
    cards = ""
    for i, (title, desc) in enumerate(steps):
        cards += (
            f"        <div class=\"reveal delay-{i+1}\" style=\"text-align:center; padding:48px 28px;"
            " background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.07);"
            " border-radius:12px; transition:border-color 0.3s,transform 0.3s;\""
            f" onmouseover=\"this.style.borderColor='{p}';this.style.transform='translateY(-5px)'\""
            " onmouseout=\"this.style.borderColor='rgba(255,255,255,0.07)';this.style.transform=''\">\n"
            f"          <div style=\"font-size:3rem; margin-bottom:20px;\">{icons[i % len(icons)]}</div>\n"
            f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:#fff; margin-bottom:12px;\">{title}</h3>\n"
            f"          <p style=\"font-size:0.92rem; color:rgba(255,255,255,0.5); line-height:1.65; max-width:280px; margin:0 auto;\">{desc}</p>\n"
            "        </div>\n"
        )
    return (
        f"  <section class=\"section\" style=\"background:{navy};\" id=\"process\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:56px;\">\n"
        "        <span class=\"section-label\">Process</span>\n"
        "        <h2 class=\"section-heading section-heading-light\">How We Work</h2>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:20px;\">\n"
        + cards
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── ABOUT VARIANTS ────────────────────────────────────────────────────────────

def _checklist_html(items):
    return "".join(
        f"<li class=\"check-item\"><span class=\"check-dot\">&#10003;</span> {item}</li>"
        for item in items
    )


def _about_v1(ctx: dict) -> str:
    """Image left, text right with checklist and CTA."""
    p = ctx["primary"]; navy = ctx["navy"]; fh = ctx["font_heading"]
    return (
        "  <section class=\"section\" style=\"background:#fff;\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        f"          <img src=\"images/{ctx['about_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:480px; object-fit:cover; border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,0.1);\">\n"
        "        </div>\n"
        "        <div class=\"reveal-right\">\n"
        "          <span class=\"section-label\">About Us</span>\n"
        f"          <h2 class=\"section-heading\" style=\"margin-bottom:18px;\">{ctx['about_title']}</h2>\n"
        f"          <p style=\"font-size:1rem; color:#64748B; line-height:1.72; margin-bottom:28px;\">{ctx['about_desc']}</p>\n"
        f"          <ul class=\"check-list\" style=\"margin-bottom:32px;\">{_checklist_html(ctx['about_checklist'])}</ul>\n"
        "          <a href=\"#careers\" class=\"btn btn-outline-dark\">View Open Positions</a>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v2(ctx: dict) -> str:
    """Text left, image right, pull-quote in accent color."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; navy = ctx["navy"]; fh = ctx["font_heading"]
    return (
        f"  <section class=\"section\" style=\"background:{ctx['accent_bg_light']};\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        f"          <span class=\"section-label\">About {ctx['company_name']}</span>\n"
        f"          <h2 class=\"section-heading\" style=\"margin-bottom:18px;\">{ctx['about_title']}</h2>\n"
        f"          <p style=\"font-size:1rem; color:#64748B; line-height:1.72; margin-bottom:28px;\">{ctx['about_desc']}</p>\n"
        f"          <blockquote style=\"border-left:4px solid {p}; padding:16px 20px; background:{ab}; border-radius:0 8px 8px 0; margin-bottom:28px;\">\n"
        f"            <p style=\"font-family:'{fh}',sans-serif; font-size:1.05rem; font-weight:700; color:{navy}; font-style:italic;\">&ldquo;We move freight the right way &mdash; safe, on time, and without excuses.&rdquo;</p>\n"
        "          </blockquote>\n"
        f"          <ul class=\"check-list\">{_checklist_html(ctx['about_checklist'][:3])}</ul>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\">\n"
        f"          <img src=\"images/{ctx['about_img']}\" alt=\"{ctx['company_name']}\" style=\"width:100%; height:480px; object-fit:cover; border-radius:12px; box-shadow:0 8px 40px rgba(0,0,0,0.1);\">\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v3(ctx: dict) -> str:
    """Dark bg, heading+desc left, 3 stat boxes right."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    stat_rows = "".join(
        f"          <div style=\"background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);"
        f" border-radius:12px; padding:28px 32px; display:flex; align-items:center; gap:24px;\">\n"
        f"            <div style=\"font-family:'{fh}',sans-serif; font-size:3rem; font-weight:900; color:{pl}; min-width:80px;\">{val}</div>\n"
        f"            <div><div style=\"font-family:'{fh}',sans-serif; font-size:1rem; font-weight:700; color:#fff; margin-bottom:4px;\">{title}</div>"
        f"<div style=\"font-size:0.88rem; color:rgba(255,255,255,0.45);\">{sub}</div></div>\n"
        "          </div>\n"
        for val, title, sub in [
            ("48", "States Covered", "Full lower-48 coverage, year-round freight"),
            ("24/7", "Dispatch Available", "Our team is always on \u2014 day or night"),
            ("CDL", "Class A Drivers", "Professional, vetted, experienced team"),
        ]
    )
    return (
        f"  <section class=\"section\" style=\"background:{navy};\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:80px; align-items:center;\">\n"
        "        <div class=\"reveal-left\">\n"
        "          <span class=\"section-label\">Who We Are</span>\n"
        f"          <h2 class=\"section-heading section-heading-light\" style=\"margin-bottom:22px;\">{ctx['about_title']}</h2>\n"
        f"          <p style=\"font-size:1rem; color:rgba(255,255,255,0.57); line-height:1.75; margin-bottom:32px;\">{ctx['about_desc']}</p>\n"
        "          <a href=\"#careers\" class=\"btn btn-primary\">Join Our Team</a>\n"
        "        </div>\n"
        "        <div class=\"reveal-right\" style=\"display:flex; flex-direction:column; gap:20px;\">\n"
        + stat_rows
        + "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v4(ctx: dict) -> str:
    """3 feature cards: icon + title + desc."""
    p = ctx["primary"]; navy = ctx["navy"]; g50 = ctx["gray_50"]
    fh = ctx["font_heading"]; pr = _hex_to_rgb(p)
    features = [
        ("\U0001f9d1\u200d\u2708\ufe0f", "Professional Drivers",
         "Every driver on our team is vetted, experienced, and committed to safe, on-time delivery. We don't cut corners on who we put behind the wheel."),
        ("\U0001f5fa\ufe0f", "48 State Coverage",
         "We run freight across the entire lower 48 with consistent lanes and year-round volume. Wherever your load needs to go, we have the coverage."),
        ("\U0001f4e6", "No-Touch Dry Van",
         "All freight is strictly no-touch. Our drivers focus on driving \u2014 pickups and deliveries are handled cleanly and professionally."),
    ]
    cards = "".join(
        f"        <div class=\"reveal delay-{i}\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px;"
        f" padding:40px 28px; transition:box-shadow 0.3s,transform 0.3s;\""
        f" onmouseover=\"this.style.boxShadow='0 10px 32px rgba({pr},0.1)';this.style.transform='translateY(-4px)'\""
        " onmouseout=\"this.style.boxShadow='';this.style.transform=''\">\n"
        f"          <div style=\"font-size:2.4rem; margin-bottom:18px;\">{icon}</div>\n"
        f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.2rem; font-weight:800; color:{navy}; margin-bottom:10px;\">{title}</h3>\n"
        f"          <p style=\"font-size:0.93rem; color:#64748B; line-height:1.65;\">{desc}</p>\n"
        "        </div>\n"
        for i, (icon, title, desc) in enumerate(features, 1)
    )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:56px;\">\n"
        "        <span class=\"section-label\">About Us</span>\n"
        "        <h2 class=\"section-heading\">A Carrier Built on the Right Values</h2>\n"
        f"        <p class=\"section-desc\" style=\"margin:0 auto;\">{ctx['about_desc']}</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:24px;\">\n"
        + cards
        + "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _about_v5(ctx: dict) -> str:
    """Alternating rows using about_img and coverage_img."""
    p = ctx["primary"]; navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]

    def _row(img, label, title, desc, checklist, flip=False):
        img_block = (
            f"<div class=\"{'reveal-right' if flip else 'reveal-left'}\">"
            f"<img src=\"images/{img}\" alt=\"{company}\" style=\"width:100%; height:420px; object-fit:cover; border-radius:12px; box-shadow:0 8px 32px rgba(0,0,0,0.08);\"></div>"
        )
        text_block = (
            f"<div class=\"{'reveal-left' if flip else 'reveal-right'}\">"
            f"<span class=\"section-label\">{label}</span>"
            f"<h2 class=\"section-heading\" style=\"margin-bottom:16px;\">{title}</h2>"
            f"<p style=\"font-size:1rem; color:#64748B; line-height:1.72; margin-bottom:24px;\">{desc}</p>"
            f"<ul class=\"check-list\">{_checklist_html(checklist[:3])}</ul></div>"
        )
        order = f"{text_block}\n        {img_block}" if flip else f"{img_block}\n        {text_block}"
        return (
            "      <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:72px; align-items:center;\">\n"
            f"        {order}\n"
            "      </div>\n"
        )

    return (
        "  <section class=\"section\" style=\"background:#fff;\" id=\"about\">\n"
        "    <div class=\"container\">\n"
        + _row(ctx["about_img"], "About Us", ctx["about_title"], ctx["about_desc"], ctx["about_checklist"])
        + "      <div style=\"height:80px;\"></div>\n"
        + _row(ctx["coverage_img"], "Coverage", ctx["coverage_title"], ctx["coverage_desc"], ctx["coverage_checklist"], flip=True)
        + "    </div>\n"
        "  </section>\n"
    )


# ── CAREERS VARIANTS ──────────────────────────────────────────────────────────

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


def _careers_v1(ctx: dict) -> str:
    """Dark navy bg, centered, job title+pay in big text, 4 stat cards, 2-col perks."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]; short = ctx["company_short"]
    return (
        f"  <section class=\"section\" style=\"background:{navy};\" id=\"careers\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:48px;\">\n"
        "        <span class=\"section-label\">Now Hiring</span>\n"
        f"        <h2 class=\"section-heading section-heading-light\">Drive With {short}</h2>\n"
        "        <p class=\"section-desc\" style=\"color:rgba(255,255,255,0.5); margin:0 auto;\">Competitive pay, real home time, and a carrier that backs you up. Here's what we're offering.</p>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"text-align:center; margin-bottom:48px;\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:700; color:#fff; margin-bottom:6px;\">{ctx['job_title']}</h3>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.8rem; font-weight:900; color:{pl};\">{ctx['pay_range']}</div>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"display:grid; grid-template-columns:repeat(4,1fr); gap:16px; max-width:960px; margin:0 auto 48px;\">\n"
        + _stat_cards_dark(ctx)
        + "\n      </div>\n"
        "      <div class=\"reveal\" style=\"display:grid; grid-template-columns:1fr 1fr; gap:12px 40px; max-width:700px; margin:0 auto 40px; color:rgba(255,255,255,0.75);\">\n"
        f"        {ctx['perks_html']}\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"text-align:center;\">\n"
        f"        <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"font-size:1rem; padding:16px 44px;\">Apply Now &mdash; {ctx['job_title']}</a>\n"
        "      </div>\n"
        f"      <p class=\"eeo-text\">{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, or veteran status.</p>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v2(ctx: dict) -> str:
    """Light bg, job title bar with pay badge, colored-border boxes, perks 2-col."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    company = ctx["company_name"]
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"careers\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:48px;\">\n"
        "        <span class=\"section-label\">Open Positions</span>\n"
        "        <h2 class=\"section-heading\">We're Hiring CDL-A Drivers</h2>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"background:#fff; border-radius:12px; border:1px solid #E2E8F0;"
        " padding:28px 36px; display:flex; align-items:center; justify-content:space-between;"
        " flex-wrap:wrap; gap:16px; margin-bottom:32px; box-shadow:0 4px 16px rgba(0,0,0,0.04);\">\n"
        "        <div>\n"
        f"          <div style=\"font-family:'{fh}',sans-serif; font-size:1.3rem; font-weight:800; color:{navy};\">{ctx['job_title']}</div>\n"
        f"          <div style=\"font-size:0.88rem; color:#64748B; margin-top:4px;\">Full-Time &middot; OTR &middot; 48 States &middot; {ctx['city_state']}</div>\n"
        "        </div>\n"
        f"        <div style=\"background:{ab}; color:{p}; font-family:'{fh}',sans-serif; font-size:1.25rem; font-weight:900;"
        f" padding:10px 24px; border-radius:8px; border:2px solid {p};\">{ctx['pay_range']}</div>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:36px;\">\n"
        + "".join(
            f"        <div style=\"background:#fff; border:2px solid {p}; border-radius:10px; padding:22px 16px; text-align:center;\">"
            f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.25rem; font-weight:900; color:{p}; margin-bottom:4px;\">{val}</div>"
            f"<div style=\"font-size:0.78rem; color:#64748B; text-transform:uppercase; letter-spacing:1px;\">{lbl}</div></div>\n"
            for val, lbl in [
                (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
                (ctx["home_time_short"], ctx["home_time_detail"]),
                (ctx["routes"], ctx["routes_type"]),
                (ctx["fourth_card_value"], ctx["fourth_card_label"]),
            ]
        )
        + "      </div>\n"
        "      <div class=\"reveal\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px; padding:32px 36px; margin-bottom:28px;\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1rem; font-weight:800; color:{navy}; margin-bottom:18px; text-transform:uppercase; letter-spacing:1px;\">Benefits &amp; Perks</h3>\n"
        "        <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:10px 40px; color:#334155;\">\n"
        f"          {ctx['perks_html']}\n"
        "        </div>\n"
        "      </div>\n"
        "      <div class=\"reveal\" style=\"text-align:center;\">\n"
        f"        <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:15px 44px;\">Apply for This Position</a>\n"
        "      </div>\n"
        f"      <p class=\"eeo-text-dark\">{company} is an Equal Opportunity Employer.</p>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v3(ctx: dict) -> str:
    """Two-column: dark left with job info+stats, light right with perks."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]; short = ctx["company_short"]
    stat_items = [
        (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
        (ctx["home_time_short"], ctx["home_time_detail"]),
        (ctx["routes"], ctx["routes_type"]),
        (ctx["fourth_card_value"], ctx["fourth_card_label"]),
    ]
    stat_html = "".join(
        f"<div style=\"background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:18px;\">"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.15rem; font-weight:900; color:{pl}; margin-bottom:4px;\">{val}</div>"
        f"<div style=\"font-size:0.78rem; color:rgba(255,255,255,0.4); text-transform:uppercase; letter-spacing:1px;\">{lbl}</div></div>"
        for val, lbl in stat_items
    )
    return (
        f"  <section id=\"careers\" style=\"display:grid; grid-template-columns:1fr 1fr; min-height:600px;\">\n"
        f"    <div style=\"background:{navy}; padding:80px 56px; display:flex; align-items:flex-start; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-left\">\n"
        f"        <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{pl}; display:block; margin-bottom:10px;\">Now Hiring</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.8rem,3vw,2.6rem); font-weight:900; color:#fff; margin-bottom:8px; letter-spacing:-0.5px;\">{ctx['job_title']}</h2>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:800; color:{pl}; margin-bottom:32px;\">{ctx['pay_range']}</div>\n"
        f"        <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:36px;\">{stat_html}</div>\n"
        f"        <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\">Apply Now</a>\n"
        "      </div>\n"
        "    </div>\n"
        "    <div style=\"background:#F8FAFC; padding:80px 56px; display:flex; align-items:flex-start; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-right\" style=\"width:100%;\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.3rem; font-weight:800; color:{navy}; margin-bottom:24px;\">What We Offer</h3>\n"
        "        <div style=\"display:flex; flex-direction:column; gap:12px; color:#334155;\">\n"
        f"          {ctx['perks_html']}\n"
        "        </div>\n"
        f"        <p style=\"font-size:0.77rem; color:#94A3B8; margin-top:32px; line-height:1.65;\">{company} is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, religion, sex, national origin, age, disability, or veteran status.</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v4(ctx: dict) -> str:
    """Accent banner with job title+pay, white section below with stat cards+perks."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    company = ctx["company_name"]
    return (
        "  <section id=\"careers\">\n"
        f"    <div style=\"background:{p}; padding:64px 24px; text-align:center;\">\n"
        "      <div class=\"reveal\">\n"
        f"        <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:rgba(255,255,255,0.65); display:block; margin-bottom:12px;\">Now Hiring</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(2rem,4vw,3rem); font-weight:900; color:#fff; margin-bottom:10px; letter-spacing:-0.5px;\">{ctx['job_title']}</h2>\n"
        f"        <div style=\"font-family:'{fh}',sans-serif; font-size:1.6rem; font-weight:900; color:rgba(255,255,255,0.85);\">{ctx['pay_range']}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "    <div style=\"background:#fff; padding:72px 24px;\">\n"
        "      <div style=\"max-width:1100px; margin:0 auto;\">\n"
        "        <div class=\"reveal\" style=\"display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:52px;\">\n"
        + _stat_cards_light(ctx)
        + "\n        </div>\n"
        "        <div class=\"reveal\" style=\"display:grid; grid-template-columns:1fr 1fr; gap:12px 48px; max-width:720px; margin:0 auto 40px; color:#334155;\">\n"
        f"          {ctx['perks_html']}\n"
        "        </div>\n"
        "        <div class=\"reveal\" style=\"text-align:center;\">\n"
        f"          <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:15px 44px;\">Apply for This Position</a>\n"
        "        </div>\n"
        f"        <p class=\"eeo-text-dark\">{company} is an Equal Opportunity Employer.</p>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _careers_v5(ctx: dict) -> str:
    """Centered card with shadow: job title, pay, stat row, divider, perks 2-col, CTA."""
    p = ctx["primary"]; navy = ctx["navy"]; g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    company = ctx["company_name"]
    stat_items = [
        (ctx["pay_range"].split("/")[0].strip(), "Weekly Pay"),
        (ctx["home_time_short"], ctx["home_time_detail"]),
        (ctx["routes"], ctx["routes_type"]),
        (ctx["fourth_card_value"], ctx["fourth_card_label"]),
    ]
    stats_html = "".join(
        f"<div style=\"text-align:center;\">"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:1.25rem; font-weight:900; color:{navy};\">{val}</div>"
        f"<div style=\"font-size:0.78rem; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; margin-top:4px;\">{lbl}</div></div>"
        + ("<div style=\"width:1px; background:#E2E8F0;\"></div>" if i < len(stat_items) - 1 else "")
        for i, (val, lbl) in enumerate(stat_items)
    )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"careers\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">Careers</span>\n"
        "        <h2 class=\"section-heading\">Join Our Growing Team</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">We're looking for experienced CDL-A drivers who want steady work, honest pay, and a carrier that has their back.</p>\n"
        "      </div>\n"
        f"      <div class=\"reveal\" style=\"background:#fff; border-radius:16px; box-shadow:0 12px 56px rgba(0,0,0,0.09);"
        f" max-width:900px; margin:0 auto; overflow:hidden; border-top:4px solid {p};\">\n"
        "        <div style=\"padding:40px 48px; border-bottom:1px solid #E2E8F0; text-align:center;\">\n"
        f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.5rem; font-weight:800; color:{navy}; margin-bottom:8px;\">{ctx['job_title']}</h3>\n"
        f"          <div style=\"font-family:'{fh}',sans-serif; font-size:1.8rem; font-weight:900; color:{p};\">{ctx['pay_range']}</div>\n"
        "        </div>\n"
        "        <div style=\"padding:32px 48px; border-bottom:1px solid #E2E8F0; display:flex; justify-content:space-around; gap:20px; flex-wrap:wrap; text-align:center;\">\n"
        f"          {stats_html}\n"
        "        </div>\n"
        "        <div style=\"padding:32px 48px; border-bottom:1px solid #E2E8F0;\">\n"
        f"          <h4 style=\"font-family:'{fh}',sans-serif; font-size:0.88rem; font-weight:800; color:{navy}; margin-bottom:18px; text-transform:uppercase; letter-spacing:1px;\">Benefits &amp; Perks</h4>\n"
        "          <div style=\"display:grid; grid-template-columns:1fr 1fr; gap:10px 40px; color:#334155;\">\n"
        f"            {ctx['perks_html']}\n"
        "          </div>\n"
        "        </div>\n"
        "        <div style=\"padding:28px 48px; text-align:center;\">\n"
        f"          <a href=\"mailto:{ctx['email']}\" class=\"btn btn-primary\" style=\"padding:14px 44px;\">Apply Now</a>\n"
        f"          <p style=\"font-size:0.77rem; color:#94A3B8; margin-top:16px;\">{company} is an Equal Opportunity Employer.</p>\n"
        "        </div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── CONTACT VARIANTS ──────────────────────────────────────────────────────────

def _contact_v1(ctx: dict) -> str:
    """Split: dark left with contact info, light right with form."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    contact_rows = "".join(
        f"        <div style=\"display:flex; gap:16px; align-items:flex-start; margin-bottom:24px;\">\n"
        f"          <div style=\"width:42px; height:42px; border-radius:8px; background:rgba(255,255,255,0.07);"
        " display:flex; align-items:center; justify-content:center; font-size:1.1rem; flex-shrink:0;\">"
        f"{icon}</div>\n"
        f"          <div><div style=\"font-family:'{fh}',sans-serif; font-size:0.85rem; font-weight:700; color:#fff; margin-bottom:3px;\">{label}</div>"
        f"<div style=\"font-size:0.9rem; color:rgba(255,255,255,0.5);\">{value}</div></div>\n"
        "        </div>\n"
        for icon, label, value in [
            ("\u2709\ufe0f", "Email", ctx["email"]),
            ("\U0001f4cd", "Address", f"{ctx['address']}<br>{ctx['city_state']}"),
            ("\U0001f550", "Hours", "Dispatch available 24/7"),
        ]
    )
    return (
        "  <section id=\"contact\" style=\"display:grid; grid-template-columns:1fr 1.1fr;\">\n"
        f"    <div style=\"background:{navy}; padding:80px 56px; display:flex; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-left\">\n"
        f"        <span style=\"font-family:'{fh}',sans-serif; font-size:0.72rem; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{pl}; display:block; margin-bottom:12px;\">Get In Touch</span>\n"
        f"        <h2 style=\"font-family:'{fh}',sans-serif; font-size:clamp(1.8rem,3vw,2.4rem); font-weight:900; color:#fff; margin-bottom:36px;\">Let's Talk Freight</h2>\n"
        + contact_rows
        + "      </div>\n"
        "    </div>\n"
        "    <div style=\"background:#F8FAFC; padding:80px 56px; display:flex; flex-direction:column; justify-content:center;\">\n"
        "      <div class=\"reveal-right\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.3rem; font-weight:800; color:{navy}; margin-bottom:24px;\">Send Us a Message</h3>\n"
        "        <form data-blk-form=\"1\">\n"
        "          <div class=\"field-row\"><div class=\"field\"><label>Full Name</label><input type=\"text\" placeholder=\"Your name\" required></div><div class=\"field\"><label>Email</label><input type=\"email\" placeholder=\"you@email.com\" required></div></div>\n"
        "          <div class=\"field\"><label>Subject</label><select><option value=\"\">Select one</option><option>Freight Quote</option><option>Driver Application</option><option>General</option></select></div>\n"
        "          <div class=\"field\"><label>Message</label><textarea placeholder=\"Tell us what you need...\"></textarea></div>\n"
        "          <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:13px;\">Send Message</button>\n"
        "        </form>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _contact_v2(ctx: dict) -> str:
    """Dark full-width, centered, 3 info cards in a row, form below."""
    p = ctx["primary"]; pl = ctx["primary_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    info_cards = "".join(
        f"<div style=\"background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.08);"
        f" border-radius:12px; padding:28px 24px; text-align:center;\">"
        f"<div style=\"font-size:1.8rem; margin-bottom:12px;\">{icon}</div>"
        f"<div style=\"font-family:'{fh}',sans-serif; font-size:0.85rem; font-weight:700; color:#fff; margin-bottom:6px;\">{label}</div>"
        f"<div style=\"font-size:0.88rem; color:rgba(255,255,255,0.45);\">{value}</div></div>"
        for icon, label, value in [
            ("\U0001f4cd", "Location", ctx["city_state"]),
            ("\u2709\ufe0f", "Email", ctx["email"]),
            ("\U0001f550", "Availability", "Dispatch 24/7"),
        ]
    )
    return (
        f"  <section class=\"section\" style=\"background:{navy};\" id=\"contact\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:52px;\">\n"
        "        <span class=\"section-label\">Contact</span>\n"
        "        <h2 class=\"section-heading section-heading-light\">Get in Touch</h2>\n"
        "        <p class=\"section-desc\" style=\"color:rgba(255,255,255,0.5); margin:0 auto;\">Ready to move freight or apply to drive? We respond fast.</p>\n"
        "      </div>\n"
        f"      <div class=\"reveal\" style=\"display:grid; grid-template-columns:repeat(3,1fr); gap:20px; max-width:900px; margin:0 auto 52px;\">{info_cards}</div>\n"
        "      <div class=\"reveal\" style=\"background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);"
        " border-radius:14px; padding:40px 48px; max-width:720px; margin:0 auto;\">\n"
        f"        <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.1rem; font-weight:800; color:#fff; margin-bottom:24px;\">Send a Message</h3>\n"
        "        <form data-blk-form=\"1\">\n"
        "          <div class=\"field-row\"><div class=\"field\"><label style=\"color:rgba(255,255,255,0.6);\">Name</label><input type=\"text\" placeholder=\"Your name\" style=\"background:rgba(255,255,255,0.06); border-color:rgba(255,255,255,0.1); color:#fff;\"></div>"
        "<div class=\"field\"><label style=\"color:rgba(255,255,255,0.6);\">Email</label><input type=\"email\" placeholder=\"you@email.com\" style=\"background:rgba(255,255,255,0.06); border-color:rgba(255,255,255,0.1); color:#fff;\"></div></div>\n"
        "          <div class=\"field\"><label style=\"color:rgba(255,255,255,0.6);\">Message</label><textarea placeholder=\"Tell us what you need...\" style=\"background:rgba(255,255,255,0.06); border-color:rgba(255,255,255,0.1); color:#fff;\"></textarea></div>\n"
        "          <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:13px;\">Send</button>\n"
        "        </form>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _contact_v3(ctx: dict) -> str:
    """Light bg, form on left, contact info cards stacked on right."""
    p = ctx["primary"]; ab = ctx["accent_bg"]; navy = ctx["navy"]
    g50 = ctx["gray_50"]; fh = ctx["font_heading"]
    contact_cards = "".join(
        f"<div style=\"background:#fff; border:1px solid #E2E8F0; border-radius:10px; padding:24px;"
        " display:flex; gap:16px; align-items:flex-start; margin-bottom:16px;\">"
        f"<div style=\"width:40px; height:40px; background:{ab}; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:1rem; flex-shrink:0;\">{icon}</div>"
        f"<div><div style=\"font-family:'{fh}',sans-serif; font-size:0.88rem; font-weight:800; color:{navy}; margin-bottom:3px;\">{label}</div>"
        f"<div style=\"font-size:0.88rem; color:#64748B;\">{value}</div></div></div>"
        for icon, label, value in [
            ("\u2709\ufe0f", "Email Us", ctx["email"]),
            ("\U0001f4cd", "Our Location", f"{ctx['address']}<br>{ctx['city_state']}"),
            ("\U0001f550", "Dispatch Hours", "Available 24 hours a day, 7 days a week"),
        ]
    )
    return (
        f"  <section class=\"section\" style=\"background:{g50};\" id=\"contact\">\n"
        "    <div class=\"container\">\n"
        "      <div class=\"section-header-center reveal\" style=\"margin-bottom:56px;\">\n"
        "        <span class=\"section-label\">Contact Us</span>\n"
        "        <h2 class=\"section-heading\">Ready to Talk?</h2>\n"
        "        <p class=\"section-desc\" style=\"margin:0 auto;\">Whether you need a freight quote or want to apply, we'll get back to you the same day.</p>\n"
        "      </div>\n"
        "      <div style=\"display:grid; grid-template-columns:1.1fr 1fr; gap:52px; max-width:1000px; margin:0 auto; align-items:start;\">\n"
        "        <div class=\"reveal-left\" style=\"background:#fff; border:1px solid #E2E8F0; border-radius:12px; padding:36px;\">\n"
        f"          <h3 style=\"font-family:'{fh}',sans-serif; font-size:1.1rem; font-weight:800; color:{navy}; margin-bottom:24px;\">Send a Message</h3>\n"
        "          <form data-blk-form=\"1\">\n"
        "            <div class=\"field-row\"><div class=\"field\"><label>Name</label><input type=\"text\" placeholder=\"Your full name\" required></div><div class=\"field\"><label>Company</label><input type=\"text\" placeholder=\"Optional\"></div></div>\n"
        "            <div class=\"field\"><label>Email</label><input type=\"email\" placeholder=\"you@email.com\" required></div>\n"
        "            <div class=\"field\"><label>Inquiry</label><select><option value=\"\">Select...</option><option>Freight Quote</option><option>Driver Application</option><option>General</option></select></div>\n"
        "            <div class=\"field\"><label>Message</label><textarea placeholder=\"Describe your freight or ask a question...\"></textarea></div>\n"
        "            <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%;\">Submit</button>\n"
        "          </form>\n"
        "        </div>\n"
        f"        <div class=\"reveal-right\">{contact_cards}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


def _contact_v4(ctx: dict) -> str:
    """Minimal centered form with colored top border, contact details below."""
    p = ctx["primary"]; abl = ctx["accent_bg_light"]
    navy = ctx["navy"]; fh = ctx["font_heading"]
    details = "".join(
        f"<div style=\"text-align:center;\"><div style=\"font-size:1.2rem; margin-bottom:4px;\">{icon}</div>"
        f"<div style=\"font-size:0.82rem; font-weight:700; color:{navy}; margin-bottom:2px;\">{label}</div>"
        f"<div style=\"font-size:0.82rem; color:#64748B;\">{value}</div></div>"
        for icon, label, value in [
            ("\u2709\ufe0f", "Email", ctx["email"]),
            ("\U0001f4cd", "Location", ctx["city_state"]),
            ("\U0001f550", "Dispatch", "24/7 Available"),
        ]
    )
    return (
        f"  <section class=\"section\" style=\"background:{abl};\" id=\"contact\">\n"
        "    <div class=\"container\">\n"
        f"      <div class=\"reveal\" style=\"max-width:680px; margin:0 auto; background:#fff;"
        f" border-radius:14px; border-top:4px solid {p}; box-shadow:0 8px 40px rgba(0,0,0,0.07); padding:48px;\">\n"
        "        <div style=\"text-align:center; margin-bottom:36px;\">\n"
        "          <span class=\"section-label\">Contact</span>\n"
        "          <h2 class=\"section-heading\" style=\"margin-bottom:8px;\">Let's Connect</h2>\n"
        "          <p style=\"font-size:0.95rem; color:#64748B;\">Freight quote or driver inquiry &mdash; we respond the same day.</p>\n"
        "        </div>\n"
        "        <form data-blk-form=\"1\">\n"
        "          <div class=\"field-row\"><div class=\"field\"><label>Name</label><input type=\"text\" placeholder=\"Your name\" required></div><div class=\"field\"><label>Email</label><input type=\"email\" placeholder=\"you@email.com\" required></div></div>\n"
        "          <div class=\"field\"><label>Inquiry</label><select><option value=\"\">Select type</option><option>Freight Quote</option><option>Driver Application</option><option>General</option></select></div>\n"
        "          <div class=\"field\"><label>Message</label><textarea placeholder=\"How can we help?\"></textarea></div>\n"
        "          <button type=\"submit\" class=\"btn btn-primary\" style=\"width:100%; padding:14px;\">Send Message</button>\n"
        "        </form>\n"
        f"        <div style=\"margin-top:36px; padding-top:28px; border-top:1px solid #E2E8F0; display:flex; justify-content:center; gap:36px; flex-wrap:wrap;\">{details}</div>\n"
        "      </div>\n"
        "    </div>\n"
        "  </section>\n"
    )


# ── MAIN ENTRY POINT ──────────────────────────────────────────────────────────

def generate_website_from_blocks(info: dict) -> str:
    """
    Generate a trucking company website by randomly combining section blocks.
    Returns the path to a zip file containing index.html + images/.

    Uses the same info dict as generate_website().
    """
    color = random.choice(COLOR_SCHEMES)
    font  = random.choice(FONT_PAIRS)
    ctx   = _build_ctx(info, color, font)

    hero    = random.choice([_hero_v1, _hero_v2, _hero_v3, _hero_v4, _hero_v5])(ctx)
    process = random.choice([_process_v1, _process_v2, _process_v3, _process_v4, _process_v5])(ctx)
    about   = random.choice([_about_v1, _about_v2, _about_v3, _about_v4, _about_v5])(ctx)
    careers = random.choice([_careers_v1, _careers_v2, _careers_v3, _careers_v4, _careers_v5])(ctx)
    contact = random.choice([_contact_v1, _contact_v2, _contact_v3, _contact_v4])(ctx)

    body = _nav(ctx) + hero + process + about + careers + contact + _footer(ctx)
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
