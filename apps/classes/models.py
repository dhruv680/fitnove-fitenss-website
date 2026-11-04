from django.db import models
from django.utils import timezone
from apps.accounts.models import GymOrganization, GymBranch

class FitnessClass(models.Model):
    organization = models.ForeignKey(
        GymOrganization,
        on_delete=models.CASCADE,
        related_name='classes'
    )
    branch = models.ForeignKey(
        GymBranch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes'
    )
    name = models.CharField(max_length=150)
    trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='classes'
    )
    capacity = models.PositiveIntegerField(default=20)
    room = models.CharField(max_length=100, default='Main Studio')
    schedule_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    days_of_week = models.CharField(max_length=100, default='Monday, Wednesday, Friday')
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['schedule_time']
        verbose_name = 'Fitness Class'
        verbose_name_plural = 'Fitness Classes'

    def __str__(self):
        return f"{self.name} ({self.schedule_time.strftime('%I:%M %p')}) - {self.room}"

    def active_bookings_count(self, date=None):
        date = date or timezone.now().date()
        return self.bookings.filter(booking_date=date, status='CONFIRMED').count()

    def available_slots(self, date=None):
        return max(0, self.capacity - self.active_bookings_count(date))


class ClassBooking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        ATTENDED = 'ATTENDED', 'Attended'
        CANCELLED = 'CANCELLED', 'Cancelled'
        NO_SHOW = 'NO_SHOW', 'No Show'

    fitness_class = models.ForeignKey(
        FitnessClass,
        on_delete=models.CASCADE,
        related_name='bookings'
    )
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='class_bookings'
    )
    booking_date = models.DateField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED
    )
    booked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-booked_at']
        unique_together = ('fitness_class', 'member', 'booking_date')
        verbose_name = 'Class Booking'
        verbose_name_plural = 'Class Bookings'

    def __str__(self):
        return f"{self.member.full_name} - {self.fitness_class.name} on {self.booking_date}"

