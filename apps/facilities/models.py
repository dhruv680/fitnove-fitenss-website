import json
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class GymEquipment(models.Model):
    class Zone(models.TextChoices):
        FREE_WEIGHTS = 'FREE_WEIGHTS', 'Olympic Free-Weight Zone'
        CARDIO_HIIT = 'CARDIO_HIIT', 'Cardio Theater & HIIT Lab'
        SPRINT_TURF = 'SPRINT_TURF', 'Functional Sprint Turf'

    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available & Operational'
        IN_USE = 'IN_USE', 'Currently In Use'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'

    name = models.CharField(max_length=150)
    zone = models.CharField(max_length=30, choices=Zone.choices, default=Zone.FREE_WEIGHTS, db_index=True)
    category = models.CharField(max_length=100, default='Free Weights')
    brand = models.CharField(max_length=100, default='Eleiko')
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    location_bay = models.CharField(max_length=100, default='Bay A')
    description = models.TextField(blank=True, default='')
    specs = models.TextField(blank=True, default='', help_text="Technical specifications")
    instructions = models.TextField(blank=True, default='', help_text="Usage and safety guidelines")
    image_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['zone', 'name']
        verbose_name = 'Gym Equipment'
        verbose_name_plural = 'Gym Equipment Roster'

    def __str__(self):
        return f"{self.name} ({self.get_zone_display()}) - {self.get_status_display()}"


class CardioProgram(models.Model):
    title = models.CharField(max_length=150)
    target_hr_zone = models.CharField(max_length=100, default='Zone 4 (80-90% HRmax)')
    duration_minutes = models.PositiveIntegerField(default=45)
    calories_burn = models.PositiveIntegerField(default=550)
    difficulty = models.CharField(max_length=50, default='Intermediate to Advanced')
    equipment_used = models.CharField(max_length=200, default='Woodway Curve Treadmills & Concept2 Rowers')
    schedule_time = models.CharField(max_length=150, default='Mon, Wed, Fri • 07:00 AM & 06:00 PM')
    trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cardio_programs'
    )
    description = models.TextField()
    workout_breakdown = models.TextField(blank=True, default='', help_text="Interval stages and target wattage")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Cardio & HIIT Program'
        verbose_name_plural = 'Cardio & HIIT Programs'

    def __str__(self):
        return f"{self.title} ({self.duration_minutes} min • {self.calories_burn} kcal)"


class SprintTurfSession(models.Model):
    title = models.CharField(max_length=150)
    trainer = models.ForeignKey(
        'trainers.Trainer',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turf_sessions'
    )
    schedule_info = models.CharField(max_length=150, default='Tue, Thu • 06:30 PM - 07:20 PM')
    duration_minutes = models.PositiveIntegerField(default=50)
    capacity = models.PositiveIntegerField(default=15)
    booked_count = models.PositiveIntegerField(default=0)
    intensity = models.CharField(max_length=50, default='High Intensity')
    focus = models.CharField(max_length=150, default='Acceleration, Deceleration & Lateral Agility')
    description = models.TextField()
    drills_overview = models.TextField(blank=True, default='', help_text="List of drills (Sled Pushes, Ladder, Plyometrics)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Sprint Turf Session'
        verbose_name_plural = 'Sprint Turf Sessions'

    def __str__(self):
        return f"{self.title} ({self.schedule_info})"

    @property
    def available_slots(self):
        confirmed_count = self.bookings.filter(status='CONFIRMED').count()
        total_booked = self.booked_count + confirmed_count
        return max(0, self.capacity - total_booked)


class TurfBooking(models.Model):
    session = models.ForeignKey(SprintTurfSession, on_delete=models.CASCADE, related_name='bookings')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='turf_bookings')
    booking_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, default='CONFIRMED')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-created_at']
        unique_together = ('session', 'member', 'booking_date')
        verbose_name = 'Turf Session Booking'
        verbose_name_plural = 'Turf Session Bookings'

    def __str__(self):
        return f"{self.member.full_name} -> {self.session.title} on {self.booking_date}"


class RecoveryFacility(models.Model):
    class FacilityType(models.TextChoices):
        CRYO = 'CRYO', 'Whole-Body Cryo Chamber (-110°C)'
        SAUNA = 'SAUNA', 'Nordic Infrared Cedar Sauna (75°C)'
        COLD_PLUNGE = 'COLD_PLUNGE', 'Ice Bath Cold Plunge (4°C)'
        COMPRESSION = 'COMPRESSION', 'Normatec 3 Pneumatic Compression'
        MASSAGE = 'MASSAGE', 'Theragun Pro Percussive Lounge'

    name = models.CharField(max_length=150)
    facility_type = models.CharField(max_length=30, choices=FacilityType.choices, default=FacilityType.CRYO)
    temperature = models.CharField(max_length=50, blank=True, default='')
    duration_minutes = models.PositiveIntegerField(default=30)
    capacity_per_slot = models.PositiveIntegerField(default=4)
    description = models.TextField()
    benefits = models.TextField(help_text="Key physiological benefits")
    preparation_tips = models.TextField(blank=True, default='')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['facility_type', 'name']
        verbose_name = 'Recovery Facility'
        verbose_name_plural = 'Recovery Facilities & Spa'

    def __str__(self):
        return f"{self.name} ({self.get_facility_type_display()})"


class RecoveryBooking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    facility = models.ForeignKey(RecoveryFacility, on_delete=models.CASCADE, related_name='bookings')
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='recovery_bookings')
    booking_date = models.DateField(default=timezone.now)
    time_slot = models.CharField(max_length=50, default='10:00 AM - 10:30 AM')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-booking_date', '-created_at']
        verbose_name = 'Recovery Spa Booking'
        verbose_name_plural = 'Recovery Spa Bookings'

    def __str__(self):
        return f"{self.member.full_name} - {self.facility.name} ({self.booking_date} {self.time_slot})"


class FuelBarItem(models.Model):
    class Category(models.TextChoices):
        SMOOTHIE = 'SMOOTHIE', 'Protein Smoothies'
        SHAKE = 'SHAKE', 'Post-Workout Isolate Shakes'
        MEAL = 'MEAL', 'Clean Macro Bowls & Food'
        BEVERAGE = 'BEVERAGE', 'Tonics, Cold Brew & BCAA'
        SNACK = 'SNACK', 'Anabolic Protein Snacks'

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.SMOOTHIE, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('8.50'))
    calories = models.PositiveIntegerField(default=350)
    protein_grams = models.PositiveIntegerField(default=35)
    carbs_grams = models.PositiveIntegerField(default=25)
    fats_grams = models.PositiveIntegerField(default=8)
    ingredients = models.TextField(blank=True, default='')
    dietary_tags = models.CharField(max_length=150, default='Gluten-Free, Whey Isolate')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Fuel Bar Menu Item'
        verbose_name_plural = 'Fuel Bar Menu Items'

    def __str__(self):
        return f"{self.name} - ${self.price} ({self.protein_grams}g Protein)"


class FuelBarOrder(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'RECEIVED', 'Order Received'
        PREPARING = 'PREPARING', 'In Preparation'
        READY = 'READY', 'Ready for Pickup'
        COMPLETED = 'COMPLETED', 'Picked Up & Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    member = models.ForeignKey('members.Member', on_delete=models.CASCADE, related_name='fuel_orders')
    items_json = models.TextField(help_text="JSON payload of ordered items")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PREPARING, db_index=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Fuel Bar Order'
        verbose_name_plural = 'Fuel Bar Orders'

    def __str__(self):
        return f"Order #{self.order_number} - {self.member.full_name} (${self.total_price})"

    @property
    def items_list(self):
        try:
            return json.loads(self.items_json)
        except Exception:
            return []
