import datetime
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User, GymOrganization, GymBranch
from apps.trainers.models import Trainer
from apps.trainers.services import TrainerService
from apps.members.models import Member
from apps.members.services import MemberService
from apps.memberships.models import MembershipPlan, Membership
from apps.memberships.services import MembershipService
from apps.attendance.models import Attendance
from apps.payments.models import Payment, Invoice, Expense
from apps.payments.services import PaymentService
from apps.fitness.models import Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, DietPlan, DietMeal, MemberProgress
from apps.classes.models import FitnessClass, ClassBooking
from apps.crm.models import Lead
from apps.notifications.models import Notification

class Command(BaseCommand):
    help = 'Seeds FitNova Gym SaaS with rich realistic demo data, plans, members, and transactions.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting FitNova database seeding...")

        # 1. Organization & Branch
        org, _ = GymOrganization.objects.get_or_create(
            slug='fitnova-metro',
            defaults={
                'name': 'FitNova Elite Fitness',
                'email': 'contact@fitnova.com',
                'phone': '+1 (555) 749-2000',
                'website': 'https://fitnova.fitness',
                'tax_id': 'GST-US-99824',
                'currency': '$',
                'is_active': True,
            }
        )

        branch, _ = GymBranch.objects.get_or_create(
            code='FN-METRO-01',
            defaults={
                'organization': org,
                'name': 'Downtown Metropolis Center',
                'address': '742 Evergreen Fitness Way, Suite 400',
                'city': 'Metropolis',
                'state': 'NY',
                'zip_code': '10001',
                'phone': '+1 (555) 749-2001',
                'email': 'metropolis@fitnova.com',
                'manager_name': 'Eleanor Vance',
                'is_main_branch': True,
                'is_active': True,
            }
        )

        # 2. Super Admin & Gym Admin
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@fitnova.com',
                'first_name': 'Alexander',
                'last_name': 'Cross',
                'role': User.Role.GYM_ADMIN,
                'organization': org,
                'branch': branch,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin_user.set_password('FitNova@Admin2026')
            admin_user.save()

        # Staff user
        staff_user, created = User.objects.get_or_create(
            username='staff1',
            defaults={
                'email': 'staff@fitnova.com',
                'first_name': 'Sophia',
                'last_name': 'Reyes',
                'role': User.Role.STAFF,
                'organization': org,
                'branch': branch,
                'is_staff': True,
            }
        )
        if created:
            staff_user.set_password('Staff@FitNova2026')
            staff_user.save()

        # 3. Trainers
        trainers_data = [
            {
                'username': 'alex_trainer',
                'first_name': 'Alex',
                'last_name': 'Mercer',
                'email': 'alex.mercer@fitnova.com',
                'phone': '+1 555-0101',
                'specialization': 'Strength & Hypertrophy',
                'experience': 7,
                'rate': 55.00,
                'rating': 4.9,
                'bio': 'Specializes in biomechanics, powerbuilding, and physique transformations.',
                'cert': 'CSCS, NASM Master Trainer'
            },
            {
                'username': 'sarah_trainer',
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'email': 'sarah.jenkins@fitnova.com',
                'phone': '+1 555-0102',
                'specialization': 'HIIT & Cardiovascular Conditioning',
                'experience': 5,
                'rate': 50.00,
                'rating': 4.8,
                'bio': 'Passionate about athletic performance, speed, and endurance conditioning.',
                'cert': 'ACE CPT, Spinning Certified'
            },
            {
                'username': 'david_trainer',
                'first_name': 'David',
                'last_name': 'Chen',
                'email': 'david.chen@fitnova.com',
                'phone': '+1 555-0103',
                'specialization': 'Mobility, Calisthenics & Yoga',
                'experience': 6,
                'rate': 45.00,
                'rating': 5.0,
                'bio': 'Focuses on functional flexibility, posture correction, and joint longevity.',
                'cert': 'RYT-500, FMS Level 2'
            }
        ]

        created_trainers = []
        for t_info in trainers_data:
            t_user, c = User.objects.get_or_create(
                username=t_info['username'],
                defaults={
                    'email': t_info['email'],
                    'first_name': t_info['first_name'],
                    'last_name': t_info['last_name'],
                    'phone': t_info['phone'],
                    'role': User.Role.TRAINER,
                    'organization': org,
                    'branch': branch,
                }
            )
            if c:
                t_user.set_password('Trainer@FitNova2026')
                t_user.save()

            trainer, _ = Trainer.objects.get_or_create(
                user=t_user,
                defaults={
                    'organization': org,
                    'branch': branch,
                    'employee_id': f"TRN-000{len(created_trainers)+1}",
                    'specialization': t_info['specialization'],
                    'experience_years': t_info['experience'],
                    'hourly_rate': Decimal(str(t_info['rate'])),
                    'rating': Decimal(str(t_info['rating'])),
                    'bio': t_info['bio'],
                    'certifications': t_info['cert'],
                    'status': Trainer.Status.ACTIVE,
                }
            )
            created_trainers.append(trainer)

        # 4. Membership Plans
        plans_data = [
            {
                'name': 'Standard Monthly',
                'slug': 'standard-monthly',
                'type': MembershipPlan.DurationType.MONTHLY,
                'days': 30,
                'price': Decimal('59.00'),
                'signup': Decimal('15.00'),
                'features': 'Full gym floor access\nStandard locker room & showers\nMobile app check-in\n1 Free fitness consultation',
                'popular': False,
            },
            {
                'name': 'Pro Quarterly',
                'slug': 'pro-quarterly',
                'type': MembershipPlan.DurationType.QUARTERLY,
                'days': 90,
                'price': Decimal('149.00'),
                'signup': Decimal('0.00'),
                'features': 'Full gym & cardio theater access\nUnlimited group fitness classes\nPremium locker & sauna access\nFree guest pass every month\nBody composition analysis',
                'popular': True,
            },
            {
                'name': 'Semi-Annual Elite',
                'slug': 'semi-annual-elite',
                'type': MembershipPlan.DurationType.HALF_YEARLY,
                'days': 180,
                'price': Decimal('269.00'),
                'signup': Decimal('0.00'),
                'features': 'Priority access to all facilities\nUnlimited studio classes\nPrivate locker reservation\nMonthly personal coach review\n10% discount on gym supplements',
                'popular': False,
            },
            {
                'name': 'VIP Black Annual',
                'slug': 'vip-black-annual',
                'type': MembershipPlan.DurationType.YEARLY,
                'days': 365,
                'price': Decimal('499.00'),
                'signup': Decimal('0.00'),
                'features': 'VIP 24/7 all-access\n1-on-1 Personal Trainer monthly\nCustom Nutrition & Macro programming\nUnlimited studio & recovery lounge\nComplimentary laundry service\nExclusive FitNova merchandise',
                'popular': False,
            }
        ]

        created_plans = []
        for p_info in plans_data:
            plan, _ = MembershipPlan.objects.get_or_create(
                organization=org,
                slug=p_info['slug'],
                defaults={
                    'name': p_info['name'],
                    'duration_type': p_info['type'],
                    'duration_days': p_info['days'],
                    'price': p_info['price'],
                    'signup_fee': p_info['signup'],
                    'features': p_info['features'],
                    'is_popular': p_info['popular'],
                    'has_trainer_included': (p_info['days'] == 365),
                    'has_classes_included': True,
                    'is_active': True,
                }
            )
            created_plans.append(plan)

        # 5. Exercise Library
        exercises_data = [
            ('Barbell Bench Press', Exercise.Category.CHEST, Exercise.Difficulty.INTERMEDIATE, 'Barbell & Bench', 'Lower bar with control to mid-chest, press upward driving feet into floor.'),
            ('Incline Dumbbell Press', Exercise.Category.CHEST, Exercise.Difficulty.INTERMEDIATE, 'Dumbbells & Incline Bench', 'Press bells vertically while maintaining retracted scapulae.'),
            ('Barbell Back Squat', Exercise.Category.LEGS, Exercise.Difficulty.ADVANCED, 'Barbell & Squat Rack', 'Brace core, descend to parallel, drive up through midfoot.'),
            ('Romanian Deadlift', Exercise.Category.LEGS, Exercise.Difficulty.INTERMEDIATE, 'Barbell', 'Hinge at the hips with soft knees, feel stretch in hamstrings and drive hips through.'),
            ('Barbell Deadlift', Exercise.Category.BACK, Exercise.Difficulty.ADVANCED, 'Barbell & Plates', 'Pull slack out of bar, drive floor away, maintain neutral spine.'),
            ('Wide-Grip Pull-Ups', Exercise.Category.BACK, Exercise.Difficulty.INTERMEDIATE, 'Pull-Up Bar', 'Pull chest toward bar engaging lats, lower with slow controlled eccentric.'),
            ('Overhead Barbell Press', Exercise.Category.SHOULDERS, Exercise.Difficulty.INTERMEDIATE, 'Barbell', 'Press bar vertically in a straight bar path locking out overhead.'),
            ('Dumbbell Lateral Raise', Exercise.Category.SHOULDERS, Exercise.Difficulty.BEGINNER, 'Dumbbells', 'Raise arms laterally to shoulder height with slight forward pitch.'),
            ('Barbell Bicep Curl', Exercise.Category.ARMS, Exercise.Difficulty.BEGINNER, 'EZ Bar', 'Curl weight upward keeping elbows pinned, squeeze biceps at peak.'),
            ('Parallel Bar Dips', Exercise.Category.ARMS, Exercise.Difficulty.INTERMEDIATE, 'Dip Station', 'Descend to 90 degrees elbow flexion, press upward engaging triceps and chest.'),
            ('Plank Hold', Exercise.Category.CORE, Exercise.Difficulty.BEGINNER, 'Floor Mat', 'Maintain rigid straight line from head to heels engaging abdominal wall.'),
            ('Treadmill High Intensity Sprints', Exercise.Category.CARDIO, Exercise.Difficulty.INTERMEDIATE, 'Treadmill', '20-second maximal effort sprints followed by 40-second recovery walks.'),
        ]

        for name, cat, diff, equip, instr in exercises_data:
            Exercise.objects.get_or_create(
                name=name,
                defaults={
                    'organization': org,
                    'category': cat,
                    'difficulty': diff,
                    'equipment': equip,
                    'instructions': instr
                }
            )

        # 6. Gym Members
        members_data = [
            ('john_doe', 'John', 'Doe', 'john.doe@example.com', '+1 555-0110', 'MALE', 'O+', 'Build functional strength', created_trainers[0]),
            ('emily_stone', 'Emily', 'Stone', 'emily.stone@example.com', '+1 555-0111', 'FEMALE', 'A+', 'Marathon endurance & core toning', created_trainers[1]),
            ('michael_clark', 'Michael', 'Clark', 'michael.clark@example.com', '+1 555-0112', 'MALE', 'B+', 'Hypertrophy & shoulder recovery', created_trainers[0]),
            ('jessica_taylor', 'Jessica', 'Taylor', 'jessica.taylor@example.com', '+1 555-0113', 'FEMALE', 'AB+', 'Flexibility and yoga alignment', created_trainers[2]),
            ('robert_miller', 'Robert', 'Miller', 'robert.miller@example.com', '+1 555-0114', 'MALE', 'O-', 'Weight loss (15kg goal)', created_trainers[1]),
            ('amanda_white', 'Amanda', 'White', 'amanda.white@example.com', '+1 555-0115', 'FEMALE', 'A-', 'Powerlifting squat and bench PRs', created_trainers[0]),
            ('david_wilson', 'David', 'Wilson', 'david.wilson@example.com', '+1 555-0116', 'MALE', 'B-', 'Cardiovascular health', None),
            ('olivia_harris', 'Olivia', 'Harris', 'olivia.harris@example.com', '+1 555-0117', 'FEMALE', 'O+', 'HIIT conditioning', created_trainers[1]),
            ('marcus_vance', 'Marcus', 'Vance', 'marcus.vance@example.com', '+1 555-0118', 'MALE', 'A+', 'General athletic maintenance', None),
            ('sophia_bennett', 'Sophia', 'Bennett', 'sophia.bennett@example.com', '+1 555-0119', 'FEMALE', 'O+', 'Strength and post-injury rehab', created_trainers[2]),
        ]

        today = timezone.now().date()
        created_members = []

        for idx, (uname, fname, lname, email, phone, gender, blood, goals, coach) in enumerate(members_data):
            u, uc = User.objects.get_or_create(
                username=uname,
                defaults={
                    'email': email,
                    'first_name': fname,
                    'last_name': lname,
                    'phone': phone,
                    'role': User.Role.MEMBER,
                    'gender': gender,
                    'organization': org,
                    'branch': branch,
                }
            )
            if uc:
                u.set_password('Member@FitNova2026')
                u.save()

            m_id = f"FN-2026-{idx+1:04d}"
            member, _ = Member.objects.get_or_create(
                user=u,
                defaults={
                    'organization': org,
                    'branch': branch,
                    'member_id': m_id,
                    'blood_group': blood,
                    'emergency_contact_name': f"Family Contact of {fname}",
                    'emergency_contact_phone': '+1 555-0999',
                    'fitness_goals': goals,
                    'assigned_trainer': coach,
                    'status': Member.Status.ACTIVE,
                    'joined_date': today - datetime.timedelta(days=random.randint(15, 120)),
                }
            )
            created_members.append(member)

            # Assign membership plans with staggered expiration dates
            chosen_plan = created_plans[idx % len(created_plans)]
            
            # Make 2 members have memberships expiring in next 7-10 days
            if idx in [1, 4]:
                start_d = today - datetime.timedelta(days=chosen_plan.duration_days - 8)
                end_d = today + datetime.timedelta(days=8)
            elif idx == 6:
                # 1 expired member
                start_d = today - datetime.timedelta(days=60)
                end_d = today - datetime.timedelta(days=2)
                member.status = Member.Status.EXPIRED
                member.save()
            else:
                start_d = today - datetime.timedelta(days=10)
                end_d = start_d + datetime.timedelta(days=chosen_plan.duration_days)

            Membership.objects.get_or_create(
                member=member,
                plan=chosen_plan,
                defaults={
                    'start_date': start_d,
                    'end_date': end_d,
                    'status': Membership.Status.EXPIRED if end_d < today else Membership.Status.ACTIVE,
                    'notes': 'Initial onboarding enrollment'
                }
            )

        # 7. Past & Present Transactions for Realistic Revenue & Charts
        methods = [Payment.Method.UPI, Payment.Method.CREDIT_CARD, Payment.Method.CASH, Payment.Method.NET_BANKING]
        for m in created_members:
            sub = m.current_membership or m.memberships.first()
            if sub:
                txn_code = f"TXN-2026-{m.id:04d}-{random.randint(1000, 9999)}"
                p_date = timezone.now() - datetime.timedelta(days=random.randint(1, 90))
                amt = sub.plan.price

                p, _ = Payment.objects.get_or_create(
                    transaction_id=txn_code,
                    defaults={
                        'organization': org,
                        'branch': branch,
                        'member': m,
                        'membership': sub,
                        'amount': amt,
                        'total_amount': amt,
                        'payment_method': random.choice(methods),
                        'status': Payment.Status.COMPLETED,
                        'payment_date': p_date,
                        'recorded_by': admin_user
                    }
                )

                inv_num = f"INV-2026-{p.id:05d}"
                Invoice.objects.get_or_create(
                    payment=p,
                    defaults={
                        'invoice_number': inv_num,
                        'issue_date': p_date.date(),
                        'due_date': p_date.date(),
                        'subtotal': amt,
                        'tax': Decimal('0.00'),
                        'total': amt,
                        'status': Invoice.Status.PAID
                    }
                )

        # Also add historical monthly payments so past 6 months revenue chart shows upward SaaS growth
        for month_offset in [1, 2, 3, 4, 5]:
            d = timezone.now() - datetime.timedelta(days=month_offset * 30)
            for j in range(random.randint(3, 6)):
                m_choice = random.choice(created_members)
                p_plan = random.choice(created_plans)
                p_amt = p_plan.price
                hist_txn = f"TXN-HIST-{month_offset}-{j}-{random.randint(1000, 9999)}"
                hp, _ = Payment.objects.get_or_create(
                    transaction_id=hist_txn,
                    defaults={
                        'organization': org,
                        'branch': branch,
                        'member': m_choice,
                        'amount': p_amt,
                        'total_amount': p_amt,
                        'payment_method': random.choice(methods),
                        'status': Payment.Status.COMPLETED,
                        'payment_date': d,
                        'recorded_by': admin_user
                    }
                )
                Invoice.objects.get_or_create(
                    payment=hp,
                    defaults={
                        'invoice_number': f"INV-HIST-{month_offset}-{j:04d}",
                        'issue_date': d.date(),
                        'due_date': d.date(),
                        'subtotal': p_amt,
                        'total': p_amt,
                        'status': Invoice.Status.PAID
                    }
                )

        # 8. Attendance Logs (Today + Last 7 days)
        for days_back in range(7):
            att_date = today - datetime.timedelta(days=days_back)
            # Pick a subset of members
            sample_members = random.sample(created_members[:8], k=random.randint(4, 7))
            for sm in sample_members:
                in_time = timezone.now().replace(year=att_date.year, month=att_date.month, day=att_date.day, hour=random.randint(6, 17), minute=random.randint(10, 50))
                out_time = in_time + datetime.timedelta(minutes=random.randint(45, 90))
                
                # If today and the first member, leave checked in
                if days_back == 0 and sm == sample_members[0]:
                    Attendance.objects.get_or_create(
                        member=sm,
                        date=att_date,
                        defaults={
                            'branch': branch,
                            'check_in_time': in_time,
                            'check_out_time': None,
                            'method': Attendance.CheckInMethod.QR_CODE,
                            'verified_by': admin_user,
                            'status': Attendance.Status.PRESENT
                        }
                    )
                else:
                    Attendance.objects.get_or_create(
                        member=sm,
                        date=att_date,
                        defaults={
                            'branch': branch,
                            'check_in_time': in_time,
                            'check_out_time': out_time,
                            'method': Attendance.CheckInMethod.QR_CODE,
                            'verified_by': admin_user,
                            'status': Attendance.Status.CHECKED_OUT
                        }
                    )

        # 9. Gym Operating Expenses
        expenses_data = [
            ('Commercial Space Lease - Metropolis Plaza', Expense.Category.RENT, Decimal('2800.00'), 'Metropolis Real Estate Corp'),
            ('Hammer Strength Equipment Servicing & Cable Replacement', Expense.Category.EQUIPMENT, Decimal('450.00'), 'Apex Gym Maintenance LLC'),
            ('Staff & Coaching Team Payroll (Semi-Monthly)', Expense.Category.SALARIES, Decimal('3200.00'), 'Payroll Distribution Account'),
            ('Municipal Power & HVAC Utilities', Expense.Category.UTILITIES, Decimal('680.00'), 'City Electric & Power'),
            ('Towels, Sanitation & Locker Room Supplies', Expense.Category.CLEANING, Decimal('180.00'), 'EcoClean Commercial Goods'),
            ('Instagram & Meta Ad Campaign', Expense.Category.MARKETING, Decimal('350.00'), 'Meta Ads'),
        ]

        for title, cat, amt, vendor in expenses_data:
            Expense.objects.get_or_create(
                organization=org,
                title=title,
                defaults={
                    'branch': branch,
                    'category': cat,
                    'amount': amt,
                    'date': today - datetime.timedelta(days=random.randint(2, 25)),
                    'paid_to': vendor,
                    'recorded_by': admin_user,
                    'notes': 'Approved operational disbursement'
                }
            )

        # 10. Fitness Classes
        classes_data = [
            ('Power Spin Cycling', created_trainers[1], 'Spin Lab', '07:00:00', 45, 25, 'High-intensity interval cadence cycling with heart rate tracking.'),
            ('Sunrise Vinyasa Flow', created_trainers[2], 'Mind & Body Studio', '08:30:00', 60, 20, 'Breath-synchronized dynamic mobility and restorative stretching.'),
            ('CrossFit WOD & Kettlebells', created_trainers[0], 'CrossFit Bay', '17:30:00', 60, 16, 'Olympic lifting progressions, kettlebell swings, and metabolic sprints.'),
            ('HIIT Cardio Blast', created_trainers[1], 'Main Studio', '18:45:00', 45, 25, 'Full-body functional circuit designed for maximal caloric burn.'),
        ]

        for c_name, coach, room, sched, dur, cap, desc in classes_data:
            fclass, _ = FitnessClass.objects.get_or_create(
                organization=org,
                name=c_name,
                defaults={
                    'branch': branch,
                    'trainer': coach,
                    'room': room,
                    'schedule_time': sched,
                    'duration_minutes': dur,
                    'capacity': cap,
                    'description': desc,
                    'days_of_week': 'Mon, Wed, Fri',
                    'is_active': True,
                }
            )

            # Book a few members into the classes for today
            for bm in created_members[:3]:
                ClassBooking.objects.get_or_create(
                    fitness_class=fclass,
                    member=bm,
                    booking_date=today,
                    defaults={'status': ClassBooking.Status.CONFIRMED}
                )

        # 11. Workouts & Diet Plans for first member
        m1 = created_members[0]
        wp, _ = WorkoutPlan.objects.get_or_create(
            member=m1,
            name='Push-Pull-Legs Hypertrophy Protocol',
            defaults={
                'trainer': created_trainers[0],
                'goal': 'Hypertrophy & Upper Body Thickness',
                'level': WorkoutPlan.Level.INTERMEDIATE,
                'start_date': today - datetime.timedelta(days=14),
                'end_date': today + datetime.timedelta(days=45),
                'notes': 'Focus on progressive overload on compound lifts. Maintain 2-3 RIR on accessories.'
            }
        )

        d1 = WorkoutDay.objects.create(workout_plan=wp, day_name='Day 1 – Push (Chest, Shoulders & Triceps)', day_number=1, focus_area='Chest & Anterior Deltoids')
        d2 = WorkoutDay.objects.create(workout_plan=wp, day_name='Day 2 – Pull (Back, Rear Delts & Biceps)', day_number=2, focus_area='Lats, Upper Back & Arms')
        d3 = WorkoutDay.objects.create(workout_plan=wp, day_name='Day 3 – Legs & Core', day_number=3, focus_area='Quads, Hamstrings & Abs')

        bench_ex = Exercise.objects.filter(name='Barbell Bench Press').first()
        ohp_ex = Exercise.objects.filter(name='Overhead Barbell Press').first()
        dip_ex = Exercise.objects.filter(name='Parallel Bar Dips').first()
        dl_ex = Exercise.objects.filter(name='Barbell Deadlift').first()
        pu_ex = Exercise.objects.filter(name='Wide-Grip Pull-Ups').first()
        sq_ex = Exercise.objects.filter(name='Barbell Back Squat').first()

        if bench_ex: WorkoutExercise.objects.create(workout_day=d1, exercise=bench_ex, sets=4, reps='6-8 reps', rest_seconds=120)
        if ohp_ex: WorkoutExercise.objects.create(workout_day=d1, exercise=ohp_ex, sets=3, reps='8-10 reps', rest_seconds=90)
        if dip_ex: WorkoutExercise.objects.create(workout_day=d1, exercise=dip_ex, sets=3, reps='10-12 reps', rest_seconds=60)
        if dl_ex: WorkoutExercise.objects.create(workout_day=d2, exercise=dl_ex, sets=4, reps='5 reps', rest_seconds=180)
        if pu_ex: WorkoutExercise.objects.create(workout_day=d2, exercise=pu_ex, sets=4, reps='To failure', rest_seconds=90)
        if sq_ex: WorkoutExercise.objects.create(workout_day=d3, exercise=sq_ex, sets=4, reps='8-10 reps', rest_seconds=120)

        # Diet plan
        dp, _ = DietPlan.objects.get_or_create(
            member=m1,
            name='Clean Bulking & Performance Fueling',
            defaults={
                'trainer': created_trainers[0],
                'daily_calories': 2850,
                'protein_grams': 185,
                'carbs_grams': 330,
                'fats_grams': 75,
                'water_liters': Decimal('3.5'),
                'notes': 'Consume 1g protein per pound of bodyweight. Pre-workout meal 90 minutes prior to lifting.'
            }
        )
        DietMeal.objects.create(diet_plan=dp, meal_type='BREAKFAST', time_slot='07:30 AM', items='4 Whole eggs, 80g rolled oats with berries, 1 scoop whey protein', calories=700)
        DietMeal.objects.create(diet_plan=dp, meal_type='LUNCH', time_slot='12:30 PM', items='200g Grilled chicken breast, 150g jasmine rice, steamed broccoli with olive oil', calories=800)
        DietMeal.objects.create(diet_plan=dp, meal_type='PRE_WORKOUT', time_slot='04:30 PM', items='2 Slices sourdough toast with almond butter and sliced banana', calories=450)
        DietMeal.objects.create(diet_plan=dp, meal_type='DINNER', time_slot='08:30 PM', items='220g Wild salmon, roasted sweet potato wedges, avocado garden salad', calories=900)

        # Progress logs
        MemberProgress.objects.create(member=m1, date=today - datetime.timedelta(days=30), weight_kg=Decimal('78.0'), body_fat_percentage=Decimal('15.5'), chest_cm=Decimal('102.0'), waist_cm=Decimal('84.0'))
        MemberProgress.objects.create(member=m1, date=today - datetime.timedelta(days=15), weight_kg=Decimal('79.2'), body_fat_percentage=Decimal('15.0'), chest_cm=Decimal('103.5'), waist_cm=Decimal('83.5'))
        MemberProgress.objects.create(member=m1, date=today, weight_kg=Decimal('80.1'), body_fat_percentage=Decimal('14.8'), chest_cm=Decimal('105.0'), waist_cm=Decimal('83.0'))

        # 12. CRM Leads
        leads_data = [
            ('Claire Redfield', '+1 555-0301', 'claire@example.com', Lead.Source.WALK_IN, Lead.Status.NEW, 'VIP Annual Membership'),
            ('Leon Kennedy', '+1 555-0302', 'leon@example.com', Lead.Source.INSTAGRAM, Lead.Status.TRIAL_SCHEDULED, 'Personal Training 3x / week'),
            ('Jill Valentine', '+1 555-0303', 'jill@example.com', Lead.Source.WEBSITE, Lead.Status.CONTACTED, 'Pro Quarterly Tier'),
            ('Chris Redfield', '+1 555-0304', 'chris@example.com', Lead.Source.REFERRAL, Lead.Status.CONVERTED, 'CrossFit & Strength Pass'),
            ('Albert Wesker', '+1 555-0305', 'albert@example.com', Lead.Source.GOOGLE, Lead.Status.LOST, 'Inquired about corporate rates'),
        ]

        for fname, phone, email, src, st, interest in leads_data:
            Lead.objects.get_or_create(
                organization=org,
                full_name=fname,
                defaults={
                    'branch': branch,
                    'phone': phone,
                    'email': email,
                    'source': src,
                    'status': st,
                    'interest': interest,
                    'trial_date': today + datetime.timedelta(days=2) if st == Lead.Status.TRIAL_SCHEDULED else None,
                    'notes': 'Captured via front reception inquiry form.'
                }
            )

        # 13. Notifications for Admin & Member
        Notification.objects.get_or_create(
            recipient=admin_user,
            title='Membership Renewal Due Alert',
            defaults={
                'message': 'Emily Stone and Robert Miller have subscriptions expiring within 8 days.',
                'notification_type': Notification.NotificationType.EXPIRY,
                'action_url': '/members/'
            }
        )
        Notification.objects.get_or_create(
            recipient=admin_user,
            title='Daily Revenue Milestone Achieved',
            defaults={
                'message': 'Over $1,500 collected in membership dues this week.',
                'notification_type': Notification.NotificationType.PAYMENT,
                'action_url': '/payments/'
            }
        )

        self.stdout.write(self.style.SUCCESS("FitNova database successfully populated with rich enterprise SaaS data!"))

