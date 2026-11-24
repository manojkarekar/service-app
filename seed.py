import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from api.models import User, ServiceCategory, ProviderProfile, CustomerProfile

# 1. Seed 24 PDF Service Categories
CATEGORIES = [
    # Home Services
    {'name': 'Plumber', 'group': 'HOME', 'icon_name': 'drop.fill', 'description': 'Leak detection, pipe repair, drain cleaning'},
    {'name': 'Electrician', 'group': 'HOME', 'icon_name': 'bolt.fill', 'description': 'Wiring, fuse repair, lighting & appliance fix'},
    {'name': 'Carpenter', 'group': 'HOME', 'icon_name': 'hammer.fill', 'description': 'Furniture assembly, doors, woodwork'},
    {'name': 'Painter', 'group': 'HOME', 'icon_name': 'paintpalette.fill', 'description': 'Interior & exterior home painting'},
    {'name': 'AC Repair', 'group': 'HOME', 'icon_name': 'snowflake', 'description': 'Air conditioner servicing, gas refill & install'},
    {'name': 'Refrigerator Repair', 'group': 'HOME', 'icon_name': 'refrigerator.fill', 'description': 'Cooling issues, compressor, gasket repair'},
    {'name': 'Washing Machine Repair', 'group': 'HOME', 'icon_name': 'washer.fill', 'description': 'Drum repair, motor, drainage fixing'},

    # Automobile Services
    {'name': 'Car Mechanic', 'group': 'AUTOMOBILE', 'icon_name': 'car.fill', 'description': 'Engine tuning, brakes, oil change, diagnostics'},
    {'name': 'Bike Mechanic', 'group': 'AUTOMOBILE', 'icon_name': 'bicycle', 'description': 'Two-wheeler servicing, chain, clutch repair'},
    {'name': 'Car Wash', 'group': 'AUTOMOBILE', 'icon_name': 'shower.fill', 'description': 'Foam wash, interior detailing, polishing'},
    {'name': 'Tire Repair', 'group': 'AUTOMOBILE', 'icon_name': 'circle.circle.fill', 'description': 'Punctures, wheel alignment, tire change'},
    {'name': 'Battery Service', 'group': 'AUTOMOBILE', 'icon_name': 'battery.100.bolt', 'description': 'Jumpstart, battery testing & replacement'},

    # Construction Services
    {'name': 'Mason', 'group': 'CONSTRUCTION', 'icon_name': 'square.stack.3d.up.fill', 'description': 'Brickwork, plastering, tile flooring'},
    {'name': 'Welder', 'group': 'CONSTRUCTION', 'icon_name': 'flame.fill', 'description': 'Metal welding, iron grills, gate repair'},
    {'name': 'Fabricator', 'group': 'CONSTRUCTION', 'icon_name': 'wrench.and.screwdriver.fill', 'description': 'Shed fabrication, aluminum fixtures'},
    {'name': 'Civil Contractor', 'group': 'CONSTRUCTION', 'icon_name': 'building.2.fill', 'description': 'Renovation, waterproofing, building works'},

    # Technology Services
    {'name': 'Computer Repair', 'group': 'TECHNOLOGY', 'icon_name': 'desktopcomputer', 'description': 'Desktop PC troubleshooting, hardware upgrade'},
    {'name': 'Laptop Repair', 'group': 'TECHNOLOGY', 'icon_name': 'laptopcomputer', 'description': 'Motherboard, display & battery repair'},
    {'name': 'CCTV Installation', 'group': 'TECHNOLOGY', 'icon_name': 'video.fill', 'description': 'Security camera setup, DVR configuration'},
    {'name': 'Mobile Repair', 'group': 'TECHNOLOGY', 'icon_name': 'iphone', 'description': 'Screen fix, charging port, battery replacement'},

    # Personal Services
    {'name': 'Tutor', 'group': 'PERSONAL', 'icon_name': 'book.closed.fill', 'description': 'Home tutoring for math, science & languages'},
    {'name': 'Fitness Trainer', 'group': 'PERSONAL', 'icon_name': 'figure.walk', 'description': 'Personal workout coaching & diet planning'},
    {'name': 'Photographer', 'group': 'PERSONAL', 'icon_name': 'camera.fill', 'description': 'Events, weddings, portrait photography'},
    {'name': 'Event Planner', 'group': 'PERSONAL', 'icon_name': 'calendar.badge.clock', 'description': 'Birthday, party & family function organizing'},
]

print("Seeding categories...")
cat_map = {}
for item in CATEGORIES:
    cat, created = ServiceCategory.objects.update_or_create(
        name=item['name'],
        defaults={
            'group': item['group'],
            'icon_name': item['icon_name'],
            'description': item['description'],
        }
    )
    cat_map[item['name']] = cat
    status = "Created" if created else "Updated"
    print(f"  [{status}] {cat.name} ({cat.get_group_display()})")

# 2. Update Sample Providers with Avatars, Addresses, and Contact Info
PROVIDERS_DATA = [
    {
        'email': 'plumber1@service.com',
        'username': 'plumber1',
        'phone': '+91 98765 43210',
        'business_name': 'Super Plumbers Ltd',
        'category_name': 'Plumber',
        'experience_years': 8,
        'bio': 'Certified master plumbers with 8+ years experience. Specialists in pipe repair, leak detection, bathroom fittings, and 24/7 emergency water restoration.',
        'address': 'Shop 14, Prime Mall, Linking Road, Bandra West, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 5.0,
    },
    {
        'email': 'electrician1@service.com',
        'username': 'electrician1',
        'phone': '+91 98220 11223',
        'business_name': 'JD Electrical Solutions',
        'category_name': 'Electrician',
        'experience_years': 5,
        'bio': 'Licensed electricians for domestic and commercial wiring, short circuit troubleshooting, switchboards, MCB, and heavy appliance connections.',
        'address': 'Unit 4, Techno Park, Andheri East, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 4.8,
    },
    {
        'email': 'mechanic1@service.com',
        'username': 'mechanic1',
        'phone': '+91 98334 55667',
        'business_name': 'Alex Auto Garage',
        'category_name': 'Car Mechanic',
        'experience_years': 4,
        'bio': 'Comprehensive four-wheeler servicing, computerized engine diagnostics, brake pad overhaul, clutch repairs, and on-spot roadside breakdown help.',
        'address': 'Plot 22, MIDC Industrial Area, Powai, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 4.7,
    },
    {
        'email': 'acrepair@service.com',
        'username': 'acrepair1',
        'phone': '+91 98112 33445',
        'business_name': 'Swift Cool AC Care',
        'category_name': 'AC Repair',
        'experience_years': 6,
        'bio': 'Expert split & inverter AC jet cleaning, gas top-up, PCB circuit repairs, and professional uninstallation/reinstallation.',
        'address': 'B-102, Sunrise Towers, Goregaon West, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 4.9,
    },
    {
        'email': 'techfix@service.com',
        'username': 'techfix1',
        'phone': '+91 98440 99881',
        'business_name': 'TechFix Laptop Lab',
        'category_name': 'Laptop Repair',
        'experience_years': 7,
        'bio': 'Motherboard chip-level servicing, broken screen replacement, water damage repair, and genuine SSD/RAM speed upgrades.',
        'address': 'Office 301, IT Plaza, Malad West, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 4.85,
    },
    {
        'email': 'trainer@service.com',
        'username': 'trainer1',
        'phone': '+91 98771 22334',
        'business_name': 'ProFit Training Studio',
        'category_name': 'Fitness Trainer',
        'experience_years': 5,
        'bio': 'Certified ACE personal fitness trainer. Weight loss transformation, functional muscle building, HIIT routines, and diet coaching.',
        'address': '12th Floor, Fitness First Hub, Juhu, Mumbai',
        'avatar_url': 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=240&h=240&fit=crop&crop=face',
        'is_verified': True,
        'is_online': True,
        'rating_avg': 4.95,
    },
]

print("\nUpdating Provider profiles...")
for pdata in PROVIDERS_DATA:
    user, u_created = User.objects.get_or_create(
        email=pdata['email'],
        defaults={
            'username': pdata['username'],
            'role': User.Role.PROVIDER,
            'phone': pdata['phone'],
        }
    )
    if u_created:
        user.set_password('password123')
        user.save()
    else:
        user.phone = pdata['phone']
        user.save()

    profile, _ = ProviderProfile.objects.get_or_create(user=user)
    profile.business_name = pdata['business_name']
    profile.category = cat_map.get(pdata['category_name'])
    profile.experience_years = pdata['experience_years']
    profile.bio = pdata['bio']
    profile.address = pdata['address']
    profile.avatar_url = pdata['avatar_url']
    profile.is_verified = pdata['is_verified']
    profile.is_online = pdata['is_online']
    if profile.rating_avg == 0:
        profile.rating_avg = pdata['rating_avg']
    profile.save()
    print(f"  [Configured] {profile.business_name} | {user.phone} | {profile.address[:30]}...")

print("\nSeeding complete!")
