from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.trainers.models import Trainer
from apps.facilities.models import (
    GymEquipment, CardioProgram, SprintTurfSession,
    RecoveryFacility, FuelBarItem
)


class Command(BaseCommand):
    help = 'Seeds realistic equipment, programs, recovery facilities, and fuel bar items.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding FitNova gym facilities and performance zones...")

        trainer1 = Trainer.objects.first()

        # 1. Olympic Free-Weight Zone
        free_weight_items = [
            {
                'name': 'Eleiko IWF Competition Olympic Barbell (20kg)',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Olympic Barbells',
                'brand': 'Eleiko Sweden',
                'quantity': 6,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Platform 1 - 4',
                'description': 'Precision Swedish steel with 215,000 PSI tensile strength, needle bearing sleeves, and aggressive Olympic knurling.',
                'specs': '20 kg weight • 28mm shaft diameter • 415mm loadable sleeve • Dual IWF markings',
                'instructions': 'Always secure weight plates with barbell collars before lifting. Return barbell to storage rack after set completion.',
            },
            {
                'name': 'Rogue Monster Lite Power Rack 3.0',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Power Racks & Cages',
                'brand': 'Rogue Fitness',
                'quantity': 4,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Rack Bay 1 - 4',
                'description': 'Heavy-duty 3x3 11-gauge steel construction with Westside hole spacing, sandwich J-cups, and reinforced safety spotter arms.',
                'specs': '90" upright height • 49" exterior width • 1,000+ lb static capacity • Textured pull-up bar',
                'instructions': 'Adjust safety spotter bars to sternum height for squats and bench presses. Never drop loaded barbells on bare spotters.',
            },
            {
                'name': 'Eleiko Calibrated Steel Competition Bumpers',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Bumper Plates & Discs',
                'brand': 'Eleiko Sweden',
                'quantity': 18,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Plate Trees Bay A',
                'description': 'IPF & IWF certified slim-profile competition discs calibrated to within +10g accuracy with chrome center hubs.',
                'specs': 'Available in 25kg, 20kg, 15kg, 10kg, 5kg, 2.5kg, 1.25kg • Color-coded Olympic standard',
                'instructions': 'Store plates by weight denomination on dedicated trees. Do not drop bumper plates directly on wooden platforms without mats.',
            },
            {
                'name': 'Rogue Olympic Flat Bench Press Station',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Bench Press',
                'brand': 'Rogue Fitness',
                'quantity': 3,
                'status': GymEquipment.Status.IN_USE,
                'location_bay': 'Platform Row B',
                'description': 'Competition standard bench press with wide Thompson Fat Pad to promote scapular stabilization and prevent shoulder impingement.',
                'specs': '12" pad width • 17" height from floor • Diamond tread spotter deck included',
                'instructions': 'Ensure feet remain flat on the platform. Request coach or peer spotting when attempting near-maximal loads.',
            },
            {
                'name': 'Commercial Pro-Style Rubber Hex Dumbbells (5–150 lbs)',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Dumbbell Arrays',
                'brand': 'FitNova Elite',
                'quantity': 60,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Dumbbell Tier Rack (East Wall)',
                'description': 'Solid cast steel core with vulcanized virgin rubber heads and hardened chrome ergonomic knurled handles.',
                'specs': '5 lb to 150 lbs in 5 lb increments • Low-odor rubber • Non-roll hexagonal design',
                'instructions': 'Always re-rack dumbbells in ascending numerical order. Do not drop dumbbells from shoulder height.',
            },
            {
                'name': 'Hammer Strength Iso-Lateral High Row Station',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Plate-Loaded Machines',
                'brand': 'Hammer Strength',
                'quantity': 2,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Machine Row C',
                'description': 'Independent arm converging motion path replicates natural human movement for optimal latissimus dorsi recruitment.',
                'specs': 'Plate-loaded 50mm horns • Adjustable thigh pads • Multi-position neutral and pronated grips',
                'instructions': 'Adjust seat height so chest pad aligns comfortably with mid-sternum. Control eccentric phase for 2 seconds.',
            },
            {
                'name': 'Preacher & Spider Curl Isolation Bench',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Arm Isolation',
                'brand': 'Rogue Fitness',
                'quantity': 1,
                'status': GymEquipment.Status.MAINTENANCE,
                'location_bay': 'Bay A-8 (Service Hold)',
                'description': 'Dual-angle dense foam arm rest with EZ-curl barbell cradle for strict bicep peak isolation.',
                'specs': 'Vinyl upholstery scheduled for quarterly conditioning • Returning to floor by tomorrow 10:00 AM',
                'instructions': 'Temporarily out of service for preventative maintenance. Please use adjustable incline bench for curls.',
            },
            {
                'name': 'Rogue Olympic Trap Bar / Hex Bar (Chrome)',
                'zone': GymEquipment.Zone.FREE_WEIGHTS,
                'category': 'Specialty Barbells',
                'brand': 'Rogue Fitness',
                'quantity': 3,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Specialty Bar Rack',
                'description': 'Dual raised and flush knurled handles to reduce spinal shear during heavy deadlifts, shrugs, and farmer walks.',
                'specs': '60 lbs unloaded • 1.34" knurled handles • 16.25" Olympic loadable sleeves',
                'instructions': 'Center your body directly between handles. Keep spine neutral and drive through mid-foot during hip hinge.',
            },
        ]

        for item in free_weight_items:
            GymEquipment.objects.get_or_create(
                name=item['name'],
                zone=item['zone'],
                defaults=item
            )

        # 2. Cardio Theater & HIIT Lab
        cardio_items = [
            {
                'name': 'Woodway Curve Non-Motorized Treadmill',
                'zone': GymEquipment.Zone.CARDIO_HIIT,
                'category': 'Self-Powered Treadmills',
                'brand': 'Woodway USA',
                'quantity': 6,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Cardio Deck 1 - 6',
                'description': 'Patented slatted running surface with frictionless ball bearings. Burns up to 30% more calories than conventional motorized treadmills.',
                'specs': 'No top speed limit • Self-powered curved deck • Wireless heart rate telemetric display',
                'instructions': 'Step onto curved deck and lean slightly forward to accelerate. Step backward toward curve base to decelerate.',
            },
            {
                'name': 'Concept2 Model D Indoor Rower (PM5 Performance Monitor)',
                'zone': GymEquipment.Zone.CARDIO_HIIT,
                'category': 'Ergometer Rowing',
                'brand': 'Concept2',
                'quantity': 8,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Rowing Row A',
                'description': 'Air-resistance flywheel delivers smooth, continuous resistance matching the athlete’s effort on every stroke.',
                'specs': 'PM5 back-lit monitor • Bluetooth/ANT+ connectivity • Damper settings 1 to 10',
                'instructions': 'Maintain order of movement: Drive legs -> Hinge hips -> Pull handle. Recover arms -> Hinge -> Slide forward.',
            },
            {
                'name': 'Concept2 SkiErg with Floor Stand',
                'zone': GymEquipment.Zone.CARDIO_HIIT,
                'category': 'Upper Body Ergometers',
                'brand': 'Concept2',
                'quantity': 4,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'SkiErg Station 1 - 4',
                'description': 'Builds aerobic endurance and core stability through poling movement used in cross-country skiing.',
                'specs': 'Dual drive cords • Air flywheel resistance • PM5 interval display',
                'instructions': 'Initiate pull with high elbows and abdominal crunch; finish with tricep extension past hips.',
            },
            {
                'name': 'Assault AirBike Elite Heavy-Duty',
                'zone': GymEquipment.Zone.CARDIO_HIIT,
                'category': 'Air Resistance Bikes',
                'brand': 'Assault Fitness',
                'quantity': 6,
                'status': GymEquipment.Status.IN_USE,
                'location_bay': 'Assault Station 1 - 6',
                'description': 'Steel fan air bike engineered for brutal anaerobic sprint intervals and lactate threshold tolerance conditioning.',
                'specs': '27" steel resistance fan • Integrated HIIT interval timers • Sealed cartridge bearings',
                'instructions': 'Adjust seat pin so knee has a 5-10 degree bend at bottom pedal stroke. Push and pull handlebars concurrently.',
            },
            {
                'name': 'StairMaster 10G Gauntlet OverDrive Revolving Staircase',
                'zone': GymEquipment.Zone.CARDIO_HIIT,
                'category': 'Step Climbers',
                'brand': 'StairMaster',
                'quantity': 3,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Climb Deck B',
                'description': 'Revolving revolving staircase with OverDrive mode simulating farmer carry and pushing resistance under load.',
                'specs': '24 to 190 steps/min • 15" LCD console • Landmark challenge programs',
                'instructions': 'Hold side rails lightly for balance. Keep torso upright without leaning forward heavily onto handrails.',
            },
        ]

        for item in cardio_items:
            GymEquipment.objects.get_or_create(
                name=item['name'],
                zone=item['zone'],
                defaults=item
            )

        cardio_programs = [
            {
                'title': 'Tabata MetCon 45: High-Output Intervals',
                'target_hr_zone': 'Zone 4 & 5 (85-95% HRmax)',
                'duration_minutes': 45,
                'calories_burn': 580,
                'difficulty': 'High Intensity / Advanced',
                'equipment_used': 'Woodway Curve Treadmills, SkiErg & AirBikes',
                'schedule_time': 'Mon, Wed, Fri • 07:00 AM & 06:30 PM',
                'trainer': trainer1,
                'description': 'Engineered to maximize post-exercise oxygen consumption (EPOC). 20 seconds maximum wattage work followed by 10 seconds active recovery across 8 grueling rounds per station.',
                'workout_breakdown': 'Warmup: 8 min Zone 2 • Block 1: Curve Sprints (4 sets) • Block 2: SkiErg Pulls (4 sets) • Block 3: Assault Bike Burnout • Cooldown: 5 min',
            },
            {
                'title': 'Concept2 Ergometer 2,000m Pacing & Threshold',
                'target_hr_zone': 'Zone 3 & 4 (75-85% HRmax)',
                'duration_minutes': 50,
                'calories_burn': 520,
                'difficulty': 'All Skill Levels',
                'equipment_used': 'Concept2 Model D PM5 Rowers',
                'schedule_time': 'Tue, Thu • 06:00 PM & Sat 08:30 AM',
                'trainer': trainer1,
                'description': 'Master stroke efficiency, split times (/500m), and aerobic base conditioning. Ideal for athletes targeting endurance capacity without joint impact.',
                'workout_breakdown': 'Mobility prep: 6 min • Pyramid: 500m / 1000m / 500m @ 24-28 SPM • 5x 250m max sprint intervals • Breathwork recovery',
            },
        ]

        for cp in cardio_programs:
            CardioProgram.objects.get_or_create(
                title=cp['title'],
                defaults=cp
            )

        # 3. Functional Sprint Turf
        turf_items = [
            {
                'name': 'Torque M4 Tank Magnetic Resistance Sled',
                'zone': GymEquipment.Zone.SPRINT_TURF,
                'category': 'Sprint Sleds',
                'brand': 'Torque Fitness',
                'quantity': 2,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Turf Lane 1',
                'description': 'Dual-magnetic braking technology that adapts dynamically: the faster you push, the heavier the resistance becomes without damaging turf.',
                'specs': '4 magnetic resistance levels • Bidirectional handlebars • Pneumatic turf tires',
                'instructions': 'Select resistance level 1-3. Keep hips low, drive through balls of feet with full triple extension.',
            },
            {
                'name': 'Rogue Echo Dog Sled 2.0 with UHMW Plastic Skis',
                'zone': GymEquipment.Zone.SPRINT_TURF,
                'category': 'Push & Pull Sleds',
                'brand': 'Rogue Fitness',
                'quantity': 3,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Turf Lane 2',
                'description': 'Heavy welded steel sled with removable upright push poles and carabiner attachment for pulling harnesses.',
                'specs': '105 lbs base weight • Compatible with Olympic bumper plates • 40m sprint capability',
                'instructions': 'Attach harness to waist or push low on upright poles. Clear lane of kettlebells before pushing.',
            },
            {
                'name': 'Rogue Foam Soft Plyo Boxes (12", 20", 24", 30")',
                'zone': GymEquipment.Zone.SPRINT_TURF,
                'category': 'Plyometrics',
                'brand': 'Rogue Fitness',
                'quantity': 8,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Plyo Bay (East End)',
                'description': 'High-density foam core with vinyl textured shell to prevent shin injuries during explosive box jumps and step-downs.',
                'specs': 'Multi-sided 3-in-1 geometry • Anti-slip landing surface • Reinforced zipper enclosure',
                'instructions': 'Land softly in athletic quarter-squat position. Step down between reps instead of jumping backward.',
            },
            {
                'name': 'SKLZ Agility Ladders & Micro Hurdle Acceleration Set',
                'zone': GymEquipment.Zone.SPRINT_TURF,
                'category': 'Footwork & Speed',
                'brand': 'SKLZ Pro',
                'quantity': 4,
                'status': GymEquipment.Status.AVAILABLE,
                'location_bay': 'Agility Lane (West End)',
                'description': '30-foot quick ladder rungs with 6" and 12" micro hurdle barriers for rapid foot velocity and reactive agility drills.',
                'specs': 'Adjustable nylon webbing • Shatter-resistant PVC rungs • Quick-connect clips',
                'instructions': 'Maintain forward eye gaze. Pump arms in coordination with rapid foot cadence.',
            },
        ]

        for item in turf_items:
            GymEquipment.objects.get_or_create(
                name=item['name'],
                zone=item['zone'],
                defaults=item
            )

        turf_sessions = [
            {
                'title': 'Elite Acceleration & Sled Power Drills',
                'trainer': trainer1,
                'schedule_info': 'Tue, Thu • 06:30 PM - 07:20 PM',
                'duration_minutes': 50,
                'capacity': 15,
                'booked_count': 6,
                'intensity': 'High Intensity Athletic',
                'focus': 'Sprint Mechanics, Sled Pushes, Deceleration Control',
                'description': 'Designed for explosive first-step velocity and lower body power. Focuses on horizontal force production through weighted sled sprints and bounding.',
                'drills_overview': '10m Sled Drives (4 sets) • Resisted Lateral Shuffles • Medicine Ball Rotational Slams • 40m Shuttle Relays',
            },
            {
                'title': 'Footwork Speed & Plyometric Jump Mechanics',
                'trainer': trainer1,
                'schedule_info': 'Mon, Wed • 07:00 AM - 07:45 AM',
                'duration_minutes': 45,
                'capacity': 12,
                'booked_count': 4,
                'intensity': 'Moderate to High',
                'focus': 'Ankle Stiffness, Quick Lateral Footwork & Box Jumps',
                'description': 'Refine kinetic chain efficiency, multi-directional agility, and reactive ground contact time for field athletes and fitness enthusiasts.',
                'drills_overview': 'Icky Shuffle Ladder Drills • 24" Soft Box Depth Jumps • Cone Agility 5-10-5 Drills • Broad Jump into Sprint',
            },
        ]

        for ts in turf_sessions:
            SprintTurfSession.objects.get_or_create(
                title=ts['title'],
                defaults=ts
            )

        # 4. Recovery & Cryo Spa
        recovery_items = [
            {
                'name': 'Whole-Body Cryotherapy Chamber (-110°C)',
                'facility_type': RecoveryFacility.FacilityType.CRYO,
                'temperature': '-110°C (-166°F)',
                'duration_minutes': 3,
                'capacity_per_slot': 1,
                'description': 'State-of-the-art electric sub-zero nitrogen-free walk-in chamber. Rapid exposure to extreme cold triggers systemic anti-inflammatory responses and endorphin release.',
                'benefits': 'Reduces muscle soreness (DOMS), accelerates tissue healing, stimulates collagen synthesis, and boosts systemic metabolic rate.',
                'preparation_tips': 'Skin must be completely dry of sweat. Clean cotton socks, slippers, and protective gloves are provided upon entry.',
            },
            {
                'name': 'Nordic Infrared Cedar Sauna (75°C)',
                'facility_type': RecoveryFacility.FacilityType.SAUNA,
                'temperature': '75°C (167°F)',
                'duration_minutes': 30,
                'capacity_per_slot': 6,
                'description': 'Full-spectrum infrared heating panels penetrate deep into muscle tissues, promoting vascular dilation, lymphatic detoxification, and parasympathetic relaxation.',
                'benefits': 'Enhances cardiovascular circulation, eases joint stiffness, promotes restorative deep sleep, and flushes cellular metabolic waste.',
                'preparation_tips': 'Hydrate with at least 500ml water prior to entry. Towel provided. Shower required before session.',
            },
            {
                'name': 'Ice Bath Cold Plunge Pool (4°C)',
                'facility_type': RecoveryFacility.FacilityType.COLD_PLUNGE,
                'temperature': '4°C (39°F)',
                'duration_minutes': 10,
                'capacity_per_slot': 2,
                'description': 'Ozone-filtered stainless steel immersion cold tubs with continuous circulation. Promotes intense vasoconstriction and rapid autonomic nervous system resets.',
                'benefits': 'Reduces chronic systemic inflammation, sharpens mental resilience, and accelerates recovery between heavy training days.',
                'preparation_tips': 'Submerge up to collarbones. Control breathing through deep diaphragmatic inhales and long exhales.',
            },
            {
                'name': 'Normatec 3 Pneumatic Compression Lounge',
                'facility_type': RecoveryFacility.FacilityType.COMPRESSION,
                'temperature': 'Room Temp (22°C)',
                'duration_minutes': 30,
                'capacity_per_slot': 4,
                'description': 'Medical-grade dynamic air compression boots utilizing biomimicking peristallic pulse patterns to mobilize venous fluid and eliminate lactic accumulation.',
                'benefits': 'Relieves heavy leg syndrome, accelerates lymphatic drainage, improves flexibility, and restores muscle freshness.',
                'preparation_tips': 'Comfortable gym tights or shorts recommended. Relax in zero-gravity recliner with personal iPad entertainment.',
            },
            {
                'name': 'Theragun Pro Percussive Massage Station',
                'facility_type': RecoveryFacility.FacilityType.MASSAGE,
                'temperature': 'Ambient',
                'duration_minutes': 20,
                'capacity_per_slot': 3,
                'description': 'QuietForce brushless motor percussive therapy devices delivering 16mm amplitude deep tissue penetration at up to 2,400 percussions per minute.',
                'benefits': 'Breaks up fascial adhesions, releases muscular trigger points, and increases localized blood flow prior to or following training.',
                'preparation_tips': 'Use provided interchangeable dampener heads for sensitive muscle bellies and wedge attachments for IT bands.',
            },
        ]

        for rf in recovery_items:
            RecoveryFacility.objects.get_or_create(
                name=rf['name'],
                facility_type=rf['facility_type'],
                defaults=rf
            )

        # 5. Athlete Fuel Bar & Lounge
        fuel_items = [
            {
                'name': 'Anabolic Double Dark Chocolate Whey Isolate Smoothie',
                'category': FuelBarItem.Category.SMOOTHIE,
                'price': Decimal('8.50'),
                'calories': 380,
                'protein_grams': 42,
                'carbs_grams': 28,
                'fats_grams': 7,
                'description': 'Grass-fed cold-processed whey isolate, raw organic cacao, unsweetened almond milk, frozen bananas, and dark chocolate nibs.',
                'ingredients': 'Whey Protein Isolate (Chocolate), Raw Cacao, Organic Banana, Almond Milk, Chia Seeds',
                'dietary_tags': 'Gluten-Free, 42g Protein, No Added Sugars',
            },
            {
                'name': 'Organic Peanut Butter & Banana Power Fuel Shake',
                'category': FuelBarItem.Category.SMOOTHIE,
                'price': Decimal('9.00'),
                'calories': 480,
                'protein_grams': 45,
                'carbs_grams': 36,
                'fats_grams': 14,
                'description': 'All-natural single-ingredient peanut butter, vanilla whey isolate, rolled oats, Ceylon cinnamon, and organic dates.',
                'ingredients': 'Peanut Butter, Vanilla Whey Isolate, Rolled Oats, Organic Banana, Dates, Oat Milk',
                'dietary_tags': 'High Calorie Macro Builder, 45g Protein',
            },
            {
                'name': 'Wild Berry Antioxidant BCAA Electrolyte Blast',
                'category': FuelBarItem.Category.SHAKE,
                'price': Decimal('7.50'),
                'calories': 140,
                'protein_grams': 15,
                'carbs_grams': 18,
                'fats_grams': 1,
                'description': 'Fermented plant BCAAs (2:1:1), organic blueberries, blackberries, Himalayan pink crystal salt, and cold-pressed coconut water.',
                'ingredients': 'BCAA Complex, Wild Blueberries, Blackberries, Coconut Water, Electrolytes',
                'dietary_tags': 'Vegan, Rapid Intra/Post Hydration',
            },
            {
                'name': 'Cold Brew Nitro Espresso & Grass-Fed Collagen',
                'category': FuelBarItem.Category.BEVERAGE,
                'price': Decimal('6.50'),
                'calories': 90,
                'protein_grams': 20,
                'carbs_grams': 3,
                'fats_grams': 0,
                'description': '16-hour steeped single-origin Ethiopian cold brew infused with nitrogen bubbles and unflavored hydrolyzed bovine collagen peptides.',
                'ingredients': 'Cold Brew Nitro Coffee, Hydrolyzed Collagen Peptides, Stevia',
                'dietary_tags': 'Zero Sugar, Joint & Tendon Support, Keto Friendly',
            },
            {
                'name': 'Grilled Lemon Herb Chicken & Quinoa Macro Bowl',
                'category': FuelBarItem.Category.MEAL,
                'price': Decimal('13.50'),
                'calories': 560,
                'protein_grams': 52,
                'carbs_grams': 48,
                'fats_grams': 12,
                'description': 'Free-range chicken breast grilled with rosemary and lemon, tricolor Andean quinoa, roasted asparagus, and extra virgin olive oil.',
                'ingredients': 'Chicken Breast (200g), Tricolor Quinoa, Roasted Asparagus, Cherry Tomatoes, Olive Oil',
                'dietary_tags': 'High Protein Clean Carb, Dairy-Free, Gluten-Free',
            },
            {
                'name': 'Overnight Vanilla Whey Rolled Oats with Chia & Honey',
                'category': FuelBarItem.Category.MEAL,
                'price': Decimal('7.00'),
                'calories': 390,
                'protein_grams': 32,
                'carbs_grams': 45,
                'fats_grams': 8,
                'description': 'Slow-soaked rolled oats steeped in almond milk with whey isolate, black chia seeds, toasted sliced almonds, and raw wildflower honey.',
                'ingredients': 'Rolled Oats, Vanilla Whey, Chia Seeds, Almond Milk, Sliced Almonds, Raw Honey',
                'dietary_tags': 'Slow-Burning Complex Carbs, Pre-Workout Fuel',
            },
            {
                'name': 'Raw Coconut Electrolyte Hydration Tonic',
                'category': FuelBarItem.Category.BEVERAGE,
                'price': Decimal('5.50'),
                'calories': 45,
                'protein_grams': 1,
                'carbs_grams': 10,
                'fats_grams': 0,
                'description': 'Fresh young green coconut water with cold-pressed lime juice, magnesium citrate, and pink Himalayan sea salt.',
                'ingredients': 'Raw Coconut Water, Lime Juice, Magnesium, Sea Salt',
                'dietary_tags': '100% Natural Electrolytes, Zero Artificial Flavor',
            },
        ]

        for item in fuel_items:
            FuelBarItem.objects.get_or_create(
                name=item['name'],
                category=item['category'],
                defaults=item
            )

        self.stdout.write(self.style.SUCCESS("All 6 FitNova facilities successfully populated with authentic enterprise data!"))
