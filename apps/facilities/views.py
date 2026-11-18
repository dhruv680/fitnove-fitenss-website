import json
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from apps.accounts.permissions import staff_or_admin
from apps.members.models import Member
from apps.trainers.models import Trainer
from apps.attendance.models import Attendance, MemberFaceProfile
from apps.attendance.services import AttendanceService
from apps.accounts.face_service import FaceAuthService
from .models import (
    GymEquipment, CardioProgram, SprintTurfSession, TurfBooking,
    RecoveryFacility, RecoveryBooking, FuelBarItem, FuelBarOrder
)


# ==============================================================================
# 1. OLYMPIC FREE-WEIGHT ZONE
# ==============================================================================

@login_required
def free_weights_view(request):
    """
    Dedicated Olympic Free-Weight Zone Page.
    Displays equipment roster, live status, specs, safety instructions, and management controls.
    """
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()

    equipments = GymEquipment.objects.filter(zone=GymEquipment.Zone.FREE_WEIGHTS)

    if search_query:
        equipments = equipments.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(specs__icontains=search_query)
        )

    if status_filter:
        equipments = equipments.filter(status=status_filter)

    if category_filter:
        equipments = equipments.filter(category=category_filter)

    categories = GymEquipment.objects.filter(
        zone=GymEquipment.Zone.FREE_WEIGHTS
    ).values_list('category', flat=True).distinct()

    total_equipment = equipments.count()
    available_count = equipments.filter(status=GymEquipment.Status.AVAILABLE).count()
    in_use_count = equipments.filter(status=GymEquipment.Status.IN_USE).count()
    maintenance_count = equipments.filter(status=GymEquipment.Status.MAINTENANCE).count()

    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']

    return render(request, 'facilities/free_weights.html', {
        'equipments': equipments,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'categories': categories,
        'total_equipment': total_equipment,
        'available_count': available_count,
        'in_use_count': in_use_count,
        'maintenance_count': maintenance_count,
        'is_staff': is_staff,
    })


@login_required
@staff_or_admin
def add_equipment_view(request):
    """Allows staff/admin to add new gym equipment."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        zone = request.POST.get('zone', GymEquipment.Zone.FREE_WEIGHTS)
        category = request.POST.get('category', 'Free Weights').strip()
        brand = request.POST.get('brand', 'Eleiko').strip()
        quantity = int(request.POST.get('quantity', 1) or 1)
        location_bay = request.POST.get('location_bay', 'Bay A').strip()
        description = request.POST.get('description', '').strip()
        specs = request.POST.get('specs', '').strip()
        instructions = request.POST.get('instructions', '').strip()

        if name:
            GymEquipment.objects.create(
                name=name,
                zone=zone,
                category=category,
                brand=brand,
                quantity=quantity,
                location_bay=location_bay,
                description=description,
                specs=specs,
                instructions=instructions,
                status=GymEquipment.Status.AVAILABLE
            )
            messages.success(request, f"Equipment '{name}' added successfully to {zone}!")
        else:
            messages.error(request, "Equipment name is required.")

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'facilities:free_weights')


@login_required
@staff_or_admin
def toggle_equipment_status_view(request, pk):
    """Allows staff to toggle equipment status (AVAILABLE -> IN_USE -> MAINTENANCE)."""
    equipment = get_object_or_404(GymEquipment, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [s.value for s in GymEquipment.Status]:
            equipment.status = new_status
            equipment.save()
            messages.success(request, f"Updated '{equipment.name}' status to {equipment.get_status_display()}.")

    referer = request.META.get('HTTP_REFERER')
    return redirect(referer or 'facilities:free_weights')


# ==============================================================================
# 2. CARDIO THEATER & HIIT LAB
# ==============================================================================

@login_required
def cardio_hiit_view(request):
    """
    Dedicated Cardio Theater & HIIT Lab Page.
    Displays treadmills, rowers, SkiErgs, assault bikes, plus cardio programs and schedules.
    """
    machines = GymEquipment.objects.filter(zone=GymEquipment.Zone.CARDIO_HIIT)
    programs = CardioProgram.objects.filter(is_active=True)

    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        machines = machines.filter(status=status_filter)

    total_machines = machines.count()
    available_machines = machines.filter(status=GymEquipment.Status.AVAILABLE).count()
    in_use_machines = machines.filter(status=GymEquipment.Status.IN_USE).count()
    trainers = Trainer.objects.filter(status='ACTIVE')

    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']

    return render(request, 'facilities/cardio_hiit.html', {
        'machines': machines,
        'programs': programs,
        'status_filter': status_filter,
        'total_machines': total_machines,
        'available_machines': available_machines,
        'in_use_machines': in_use_machines,
        'trainers': trainers,
        'is_staff': is_staff,
    })


@login_required
@staff_or_admin
def add_cardio_program_view(request):
    """Allows staff/trainers to schedule a new cardio/HIIT program."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        target_hr_zone = request.POST.get('target_hr_zone', 'Zone 4 (80-90% HRmax)').strip()
        duration_minutes = int(request.POST.get('duration_minutes', 45) or 45)
        calories_burn = int(request.POST.get('calories_burn', 500) or 500)
        difficulty = request.POST.get('difficulty', 'Intermediate')
        equipment_used = request.POST.get('equipment_used', 'Curve Treadmills & Concept2 Rowers')
        schedule_time = request.POST.get('schedule_time', 'Mon, Wed, Fri • 07:00 AM')
        trainer_id = request.POST.get('trainer_id')
        description = request.POST.get('description', '').strip()
        workout_breakdown = request.POST.get('workout_breakdown', '').strip()

        trainer = Trainer.objects.filter(id=trainer_id).first() if trainer_id else None

        if title:
            CardioProgram.objects.create(
                title=title,
                target_hr_zone=target_hr_zone,
                duration_minutes=duration_minutes,
                calories_burn=calories_burn,
                difficulty=difficulty,
                equipment_used=equipment_used,
                schedule_time=schedule_time,
                trainer=trainer,
                description=description,
                workout_breakdown=workout_breakdown
            )
            messages.success(request, f"Cardio Program '{title}' scheduled successfully!")
        else:
            messages.error(request, "Program title is required.")

    return redirect('facilities:cardio_hiit')


# ==============================================================================
# 3. FUNCTIONAL SPRINT TURF
# ==============================================================================

@login_required
def sprint_turf_view(request):
    """
    Dedicated Functional Sprint Turf Page.
    Displays 40m indoor astroturf track features, sleds, plyometric boxes, sprint drills,
    and allows trainers to schedule sessions and athletes to book spots.
    """
    turf_equipment = GymEquipment.objects.filter(zone=GymEquipment.Zone.SPRINT_TURF)
    sessions = SprintTurfSession.objects.filter(is_active=True).prefetch_related('bookings')
    trainers = Trainer.objects.filter(status='ACTIVE')

    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']
    is_trainer = request.user.is_trainer or is_staff

    # Check member bookings
    member = getattr(request.user, 'member_profile', None)
    my_turf_bookings = []
    if member:
        my_turf_bookings = TurfBooking.objects.filter(member=member, booking_date__gte=timezone.now().date())

    my_booked_session_ids = [b.session_id for b in my_turf_bookings]

    return render(request, 'facilities/sprint_turf.html', {
        'turf_equipment': turf_equipment,
        'sessions': sessions,
        'trainers': trainers,
        'is_staff': is_staff,
        'is_trainer': is_trainer,
        'member': member,
        'my_turf_bookings': my_turf_bookings,
        'my_booked_session_ids': my_booked_session_ids,
    })


@login_required
def book_turf_session_view(request, session_id):
    """Allows an authenticated member to book a spot on a sprint turf training session."""
    session = get_object_or_404(SprintTurfSession, id=session_id, is_active=True)
    member = getattr(request.user, 'member_profile', None)

    if not member:
        messages.error(request, "Only registered gym members can reserve sprint turf sessions.")
        return redirect('facilities:sprint_turf')

    if session.available_slots <= 0:
        messages.error(request, f"Sorry, '{session.title}' is fully booked.")
        return redirect('facilities:sprint_turf')

    today = timezone.now().date()
    existing = TurfBooking.objects.filter(session=session, member=member, booking_date=today).first()
    if existing:
        messages.warning(request, f"You are already booked for '{session.title}' today.")
        return redirect('facilities:sprint_turf')

    TurfBooking.objects.create(
        session=session,
        member=member,
        booking_date=today,
        status='CONFIRMED'
    )
    messages.success(request, f"Spot confirmed for '{session.title}'! Sleds and track lanes are reserved.")
    return redirect('facilities:sprint_turf')


@login_required
def add_turf_session_view(request):
    """Allows trainers and staff to add new sprint turf drill sessions."""
    is_authorized = request.user.is_trainer or request.user.is_staff or request.user.is_superuser
    if not is_authorized:
        messages.error(request, "Permission denied.")
        return redirect('facilities:sprint_turf')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        schedule_info = request.POST.get('schedule_info', 'Tue, Thu • 06:30 PM')
        duration_minutes = int(request.POST.get('duration_minutes', 50) or 50)
        capacity = int(request.POST.get('capacity', 15) or 15)
        intensity = request.POST.get('intensity', 'High Intensity')
        focus = request.POST.get('focus', 'Acceleration, Deceleration & Lateral Agility')
        description = request.POST.get('description', '')
        drills_overview = request.POST.get('drills_overview', '')

        trainer = None
        if hasattr(request.user, 'trainer_profile'):
            trainer = request.user.trainer_profile
        else:
            trainer_id = request.POST.get('trainer_id')
            if trainer_id:
                trainer = Trainer.objects.filter(id=trainer_id).first()

        if title:
            SprintTurfSession.objects.create(
                title=title,
                trainer=trainer,
                schedule_info=schedule_info,
                duration_minutes=duration_minutes,
                capacity=capacity,
                intensity=intensity,
                focus=focus,
                description=description,
                drills_overview=drills_overview
            )
            messages.success(request, f"Sprint Turf session '{title}' created successfully!")
        else:
            messages.error(request, "Session title is required.")

    return redirect('facilities:sprint_turf')


# ==============================================================================
# 4. SMART BIOMETRIC ACCESS
# ==============================================================================

@login_required
def biometric_access_view(request):
    """
    Dedicated Smart Biometric Access Terminal Page.
    Live camera viewport with face scanning radar, turnstile hardware simulation,
    real identity verification against member face profiles, attendance records, and QR fallback.
    """
    today = timezone.localdate()
    today_attendances = Attendance.objects.filter(date=today).select_related('member__user').order_by('-id')[:10]
    total_today = Attendance.objects.filter(date=today).count()
    active_now = Attendance.objects.filter(date=today, status=Attendance.Status.PRESENT, check_out_time__isnull=True).count()
    enrolled_count = MemberFaceProfile.objects.filter(is_active=True).count()

    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']
    member = getattr(request.user, 'member_profile', None)

    return render(request, 'facilities/biometric_access.html', {
        'today_attendances': today_attendances,
        'total_today': total_today,
        'active_now': active_now,
        'enrolled_count': enrolled_count,
        'is_staff': is_staff,
        'member': member,
    })


@login_required
def api_biometric_verify_view(request):
    """
    Live AI Facial Recognition Access Control Endpoint.
    Strictly verifies camera frame against stored biometric templates.
    Never opens the gate without a verified member match.
    Records attendance automatically upon match.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid HTTP method.'}, status=405)

    face_image = request.POST.get('image', '').strip()
    if not face_image:
        return JsonResponse({'success': False, 'message': 'No face camera frame captured.'}, status=400)

    # 1. Decode and check image quality
    pil_img = FaceAuthService.decode_base64_image(face_image)
    if not pil_img:
        return JsonResponse({'success': False, 'message': 'Invalid image encoding.'}, status=400)

    is_valid, quality_msg = FaceAuthService.check_liveness_and_quality(pil_img)
    if not is_valid:
        return JsonResponse({'success': False, 'message': quality_msg}, status=400)

    # 2. Extract feature vector
    query_vec = FaceAuthService.compute_visual_features(pil_img)
    if not query_vec:
        return JsonResponse({'success': False, 'message': 'Could not extract facial geometry.'}, status=400)

    # 3. Match against enrolled members
    # Match against MemberFaceProfile (or UserFaceProfile)
    enrolled_profiles = MemberFaceProfile.objects.filter(is_active=True).select_related('member__user')
    best_member = None
    best_sim = 0.0

    for prof in enrolled_profiles:
        if prof.feature_vector:
            try:
                prof_vec = json.loads(prof.feature_vector)
                sim = float(sum(a * b for a, b in zip(query_vec, prof_vec)))
                if sim > best_sim:
                    best_sim = sim
                    best_member = prof.member
            except Exception:
                continue

    # Also check UserFaceProfiles if member face profile wasn't synced
    if best_sim < 0.52:
        from apps.accounts.models import UserFaceProfile
        user_profiles = UserFaceProfile.objects.filter(is_active=True).select_related('user__member_profile')
        for uprof in user_profiles:
            if uprof.feature_vector and hasattr(uprof.user, 'member_profile') and uprof.user.member_profile:
                try:
                    prof_vec = json.loads(uprof.feature_vector)
                    sim = float(sum(a * b for a, b in zip(query_vec, prof_vec)))
                    if sim > best_sim:
                        best_sim = sim
                        best_member = uprof.user.member_profile
                except Exception:
                    continue

    THRESHOLD = 0.52  # Calibrated threshold
    if not best_member or best_sim < THRESHOLD:
        conf_pct = round(best_sim * 100, 1)
        return JsonResponse({
            'success': False,
            'access_granted': False,
            'message': f"Access Denied: Unrecognized Face ({conf_pct}% similarity). Please register your face or use QR Pass.",
            'confidence': conf_pct
        })

    # 4. Identity Verified! Check active membership status
    curr_sub = best_member.current_membership
    is_sub_active = best_member.is_membership_active

    if not is_sub_active:
        return JsonResponse({
            'success': False,
            'access_granted': False,
            'message': f"Access Denied: Membership expired for {best_member.full_name}. Please renew your plan.",
            'member_name': best_member.full_name,
            'member_id': best_member.member_id,
        })

    # 5. Record actual attendance
    success, att_msg, attendance, action_type = AttendanceService.process_check_in(
        member_identifier=best_member.member_id,
        verified_by=request.user,
        method=Attendance.CheckInMethod.FACE_RECOGNITION,
        is_test=False
    )

    conf_pct = round(best_sim * 100, 1)
    now_time = timezone.localtime().strftime('%I:%M %p')

    photo_url = None
    if best_member.user.profile_picture and hasattr(best_member.user.profile_picture, 'url'):
        try:
            photo_url = best_member.user.profile_picture.url
        except Exception:
            photo_url = None

    return JsonResponse({
        'success': True,
        'access_granted': True,
        'action': action_type,
        'message': f"ACCESS GRANTED • Welcome {best_member.full_name}!",
        'member': {
            'id': best_member.id,
            'name': best_member.full_name,
            'member_id': best_member.member_id,
            'plan': curr_sub.plan.name if curr_sub else 'Standard Access',
            'time': now_time,
            'photo_url': photo_url,
            'confidence': conf_pct,
        }
    })


# ==============================================================================
# 5. RECOVERY & CRYO SPA
# ==============================================================================

@login_required
def recovery_spa_view(request):
    """
    Dedicated Recovery & Cryo Spa Page.
    Displays Cryotherapy, Infrared Sauna, Ice Baths, Normatec compression, and Theragun stations.
    Allows members to schedule recovery appointments and staff to manage reservations.
    """
    facilities = RecoveryFacility.objects.filter(is_available=True)
    member = getattr(request.user, 'member_profile', None)

    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']

    # Bookings
    my_bookings = []
    if member:
        my_bookings = RecoveryBooking.objects.filter(member=member).select_related('facility').order_by('-booking_date')[:10]

    all_bookings = []
    if is_staff:
        all_bookings = RecoveryBooking.objects.select_related('member__user', 'facility').order_by('-booking_date')[:25]

    time_slots = [
        '08:00 AM - 08:30 AM',
        '09:00 AM - 09:30 AM',
        '10:00 AM - 10:30 AM',
        '11:30 AM - 12:00 PM',
        '02:00 PM - 02:30 PM',
        '03:30 PM - 04:00 PM',
        '05:00 PM - 05:30 PM',
        '06:30 PM - 07:00 PM',
        '08:00 PM - 08:30 PM',
    ]

    return render(request, 'facilities/recovery_spa.html', {
        'facilities': facilities,
        'member': member,
        'my_bookings': my_bookings,
        'all_bookings': all_bookings,
        'time_slots': time_slots,
        'is_staff': is_staff,
    })


@login_required
def book_recovery_view(request):
    """Processes member appointment booking for recovery services."""
    if request.method != 'POST':
        return redirect('facilities:recovery_spa')

    member = getattr(request.user, 'member_profile', None)
    if not member:
        messages.error(request, "Only registered gym members can reserve recovery spa sessions.")
        return redirect('facilities:recovery_spa')

    facility_id = request.POST.get('facility_id')
    facility = get_object_or_404(RecoveryFacility, id=facility_id, is_available=True)
    booking_date_str = request.POST.get('booking_date')
    time_slot = request.POST.get('time_slot')
    notes = request.POST.get('notes', '').strip()

    try:
        booking_date = timezone.datetime.strptime(booking_date_str, '%Y-%m-%d').date()
    except Exception:
        booking_date = timezone.now().date()

    # Check slot capacity
    existing_count = RecoveryBooking.objects.filter(
        facility=facility,
        booking_date=booking_date,
        time_slot=time_slot,
        status__in=['CONFIRMED', 'PENDING']
    ).count()

    if existing_count >= facility.capacity_per_slot:
        messages.error(request, f"Sorry, '{facility.name}' is already fully booked for {time_slot} on {booking_date}.")
        return redirect('facilities:recovery_spa')

    RecoveryBooking.objects.create(
        facility=facility,
        member=member,
        booking_date=booking_date,
        time_slot=time_slot,
        notes=notes,
        status=RecoveryBooking.Status.CONFIRMED
    )

    messages.success(request, f"Recovery session for '{facility.name}' confirmed on {booking_date} at {time_slot}!")
    return redirect('facilities:recovery_spa')


@login_required
@staff_or_admin
def update_recovery_booking_status_view(request, booking_id):
    """Allows staff to confirm, complete, or cancel a recovery booking."""
    booking = get_object_or_404(RecoveryBooking, id=booking_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [s.value for s in RecoveryBooking.Status]:
            booking.status = new_status
            booking.save()
            messages.success(request, f"Booking #{booking.id} updated to {booking.get_status_display()}.")

    return redirect('facilities:recovery_spa')


# ==============================================================================
# 6. ATHLETE FUEL BAR & LOUNGE
# ==============================================================================

@login_required
def fuel_bar_view(request):
    """
    Dedicated Athlete Fuel Bar & Lounge Page.
    Displays organic smoothies, isolate shakes, macro bowls, and nitro beverages.
    Allows members to order pickup items and staff to manage menu and order queue.
    """
    category_filter = request.GET.get('category', '').strip()
    items = FuelBarItem.objects.all()

    if category_filter:
        items = items.filter(category=category_filter)

    categories = FuelBarItem.Category.choices
    member = getattr(request.user, 'member_profile', None)
    is_staff = request.user.is_staff or request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'GYM_ADMIN', 'STAFF']

    # Member's recent orders
    my_orders = []
    if member:
        my_orders = FuelBarOrder.objects.filter(member=member).order_by('-created_at')[:8]

    # Live kitchen queue for staff
    kitchen_orders = []
    if is_staff:
        kitchen_orders = FuelBarOrder.objects.filter(
            status__in=['RECEIVED', 'PREPARING', 'READY']
        ).select_related('member__user').order_by('created_at')[:20]

    return render(request, 'facilities/fuel_bar.html', {
        'items': items,
        'categories': categories,
        'category_filter': category_filter,
        'member': member,
        'my_orders': my_orders,
        'kitchen_orders': kitchen_orders,
        'is_staff': is_staff,
    })


@login_required
def create_fuel_order_view(request):
    """Processes member order placement from the Fuel Bar menu."""
    if request.method != 'POST':
        return redirect('facilities:fuel_bar')

    member = getattr(request.user, 'member_profile', None)
    if not member:
        messages.error(request, "Only registered gym members can place Fuel Bar orders.")
        return redirect('facilities:fuel_bar')

    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1) or 1)
    notes = request.POST.get('notes', '').strip()

    item = get_object_or_404(FuelBarItem, id=item_id, is_available=True)
    total_price = item.price * quantity

    order_payload = [{
        'id': item.id,
        'name': item.name,
        'category': item.get_category_display(),
        'price': float(item.price),
        'quantity': quantity,
        'subtotal': float(total_price),
    }]

    order_number = f"ORD-{timezone.now().strftime('%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    FuelBarOrder.objects.create(
        order_number=order_number,
        member=member,
        items_json=json.dumps(order_payload),
        total_price=total_price,
        status=FuelBarOrder.Status.PREPARING,
        notes=notes
    )

    messages.success(request, f"Order #{order_number} received! Your {item.name} is now being blended in the Fuel Lounge.")
    return redirect('facilities:fuel_bar')


@login_required
@staff_or_admin
def update_fuel_order_status_view(request, order_id):
    """Allows bar staff to update order status (Preparing -> Ready for Pickup -> Completed)."""
    order = get_object_or_404(FuelBarOrder, id=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [s.value for s in FuelBarOrder.Status]:
            order.status = new_status
            order.save()
            messages.success(request, f"Order #{order.order_number} marked as {order.get_status_display()}.")

    return redirect('facilities:fuel_bar')


@login_required
@staff_or_admin
def add_fuel_item_view(request):
    """Allows staff/admin to add new items to the Fuel Bar menu."""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category = request.POST.get('category', FuelBarItem.Category.SMOOTHIE)
        description = request.POST.get('description', '').strip()
        price = Decimal(request.POST.get('price', '8.50') or '8.50')
        calories = int(request.POST.get('calories', 350) or 350)
        protein_grams = int(request.POST.get('protein_grams', 30) or 30)
        carbs_grams = int(request.POST.get('carbs_grams', 25) or 25)
        fats_grams = int(request.POST.get('fats_grams', 8) or 8)
        ingredients = request.POST.get('ingredients', '').strip()
        dietary_tags = request.POST.get('dietary_tags', 'Whey Isolate, Gluten-Free').strip()

        if name:
            FuelBarItem.objects.create(
                name=name,
                category=category,
                description=description,
                price=price,
                calories=calories,
                protein_grams=protein_grams,
                carbs_grams=carbs_grams,
                fats_grams=fats_grams,
                ingredients=ingredients,
                dietary_tags=dietary_tags,
                is_available=True
            )
            messages.success(request, f"Menu item '{name}' added successfully!")
        else:
            messages.error(request, "Item name is required.")

    return redirect('facilities:fuel_bar')


@login_required
@staff_or_admin
def toggle_fuel_item_availability_view(request, pk):
    """Allows staff to toggle stock status for an item (In Stock vs Sold Out)."""
    item = get_object_or_404(FuelBarItem, pk=pk)
    if request.method == 'POST':
        item.is_available = not item.is_available
        item.save()
        status_str = "In Stock" if item.is_available else "Sold Out"
        messages.info(request, f"'{item.name}' is now {status_str}.")

    return redirect('facilities:fuel_bar')
