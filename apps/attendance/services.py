from django.utils import timezone
from django.db import transaction
from .models import Attendance
from apps.members.models import Member

class AttendanceService:
    @staticmethod
    def get_scoped_attendance(user):
        if user.is_super_admin:
            return Attendance.objects.select_related('member__user', 'branch', 'verified_by').all()
        return Attendance.objects.select_related('member__user', 'branch', 'verified_by').filter(member__organization=user.organization)

    @staticmethod
    @transaction.atomic
    def process_check_in(member_identifier, verified_by=None, method=Attendance.CheckInMethod.QR_CODE):
        """
        Processes check-in/out via QR payload (FITNOVA:member_id:qr_token) or raw member_id.
        Returns a tuple (success: bool, message: str, attendance: Attendance|None, action: str)
        """
        today = timezone.now().date()
        clean_input = member_identifier.strip()

        # Parse QR code format
        member = None
        if clean_input.startswith("FITNOVA:"):
            parts = clean_input.split(":")
            if len(parts) >= 3:
                member_id = parts[1]
                qr_token = parts[2]
                member = Member.objects.filter(member_id=member_id, qr_token=qr_token).select_related('user', 'organization').first()
            elif len(parts) == 2:
                member_id = parts[1]
                member = Member.objects.filter(member_id=member_id).select_related('user', 'organization').first()
        else:
            member = Member.objects.filter(member_id__iexact=clean_input).select_related('user', 'organization').first()
            if not member:
                member = Member.objects.filter(user__phone=clean_input).select_related('user', 'organization').first()

        if not member:
            return False, "Member not found. Please verify member ID or QR pass.", None, "NOT_FOUND"

        # Validate Membership
        if not member.is_membership_active:
            return False, f"Membership expired or inactive for {member.full_name}. Please renew membership.", None, "EXPIRED"

        # Check existing attendance for today
        existing = Attendance.objects.filter(member=member, date=today).first()
        now = timezone.now()

        if existing:
            if existing.status == Attendance.Status.PRESENT and not existing.check_out_time:
                # Perform Check-out
                existing.check_out_time = now
                existing.status = Attendance.Status.CHECKED_OUT
                existing.save(update_fields=['check_out_time', 'status'])
                duration = existing.duration_minutes
                return True, f"Check-out successful for {member.full_name}! Workout duration: {duration} mins.", existing, "CHECK_OUT"
            else:
                return False, f"{member.full_name} has already completed attendance today ({existing.check_in_time.strftime('%I:%M %p')} - {existing.check_out_time.strftime('%I:%M %p') if existing.check_out_time else ''}). Duplicate check-in prevented.", existing, "DUPLICATE"

        # Create New Check-in
        attendance = Attendance.objects.create(
            member=member,
            branch=member.branch,
            date=today,
            check_in_time=now,
            method=method,
            verified_by=verified_by,
            status=Attendance.Status.PRESENT
        )
        return True, f"Check-in successful! Welcome {member.full_name} to FitNova.", attendance, "CHECK_IN"
