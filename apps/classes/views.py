from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from apps.members.models import Member
from apps.trainers.models import Trainer
from .models import FitnessClass, ClassBooking
from .serializers import FitnessClassSerializer, ClassBookingSerializer

@login_required
def class_list(request):
    classes = FitnessClass.objects.filter(is_active=True).select_related('trainer__user', 'organization')
    if not request.user.is_super_admin:
        classes = classes.filter(organization=request.user.organization)

    today = timezone.now().date()
    # Annotate class with slots
    class_cards = []
    for cls in classes:
        booked = cls.active_bookings_count(today)
        slots_left = max(0, cls.capacity - booked)
        class_cards.append({
            'obj': cls,
            'booked': booked,
            'slots_left': slots_left,
            'is_full': slots_left <= 0
        })

    members = Member.objects.filter(status='ACTIVE')
    if not request.user.is_super_admin:
        members = members.filter(organization=request.user.organization)

    return render(request, 'classes/class_list.html', {
        'class_cards': class_cards,
        'today': today,
        'members': members
    })


@login_required
@staff_or_admin
def class_create(request):
    trainers = Trainer.objects.filter(status='ACTIVE')
    if not request.user.is_super_admin:
        trainers = trainers.filter(organization=request.user.organization)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        trainer_id = request.POST.get('trainer_id')
        capacity = int(request.POST.get('capacity', '20'))
        room = request.POST.get('room', 'Studio A').strip()
        schedule_time = request.POST.get('schedule_time')
        duration = int(request.POST.get('duration_minutes', '60'))
        days = request.POST.get('days_of_week', 'Mon, Wed, Fri').strip()
        description = request.POST.get('description', '').strip()

        trainer = trainers.filter(id=trainer_id).first() if trainer_id else None

        cls = FitnessClass.objects.create(
            organization=request.user.organization,
            branch=request.user.branch,
            name=name,
            trainer=trainer,
            capacity=capacity,
            room=room,
            schedule_time=schedule_time,
            duration_minutes=duration,
            days_of_week=days,
            description=description
        )
        messages.success(request, f"Class '{cls.name}' scheduled successfully!")
        return redirect('classes:class_list')

    return render(request, 'classes/class_form.html', {'trainers': trainers})


@login_required
def class_detail(request, pk):
    cls = get_object_or_404(FitnessClass, pk=pk)
    today = timezone.now().date()
    bookings = cls.bookings.filter(booking_date__gte=today).select_related('member__user').order_by('booking_date')

    return render(request, 'classes/class_detail.html', {
        'cls': cls,
        'bookings': bookings,
        'today': today,
        'slots_left': cls.available_slots(today)
    })


@login_required
def book_class(request, pk):
    cls = get_object_or_404(FitnessClass, pk=pk)
    today = timezone.now().date()

    if request.user.is_member:
        member = request.user.member_profile
    else:
        member_id = request.POST.get('member_id')
        member = get_object_or_404(Member, id=member_id)

    if not member.is_membership_active:
        messages.error(request, f"Member {member.full_name} does not have an active membership subscription.")
        return redirect('classes:class_list')

    if cls.available_slots(today) <= 0:
        messages.error(request, f"Sorry, '{cls.name}' is already at full capacity ({cls.capacity} seats).")
        return redirect('classes:class_list')

    booking, created = ClassBooking.objects.get_or_create(
        fitness_class=cls,
        member=member,
        booking_date=today,
        defaults={'status': ClassBooking.Status.CONFIRMED}
    )

    if not created:
        messages.info(request, f"{member.full_name} is already booked for this class today.")
    else:
        messages.success(request, f"Seat confirmed for {member.full_name} in {cls.name}!")

    return redirect('classes:class_detail', pk=cls.pk)


class FitnessClassViewSet(viewsets.ModelViewSet):
    serializer_class = FitnessClassSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return FitnessClass.objects.all()
        return FitnessClass.objects.filter(organization=user.organization)

