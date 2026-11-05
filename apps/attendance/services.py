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
        import re
        today = timezone.now().date()
        clean_input = member_identifier.strip().strip('\'"').strip()

        # Parse QR code format flexibly with regex
        member = None

        # 1. Check FITNOVA:ID:TOKEN pattern
        fn_token_match = re.search(r'FITNOVA:([A-Za-z0-9\-]+)(?::([a-f0-9\-]+))?', clean_input, re.IGNORECASE)
        if fn_token_match:
            mid = fn_token_match.group(1).strip()
            tok = fn_token_match.group(2).strip() if fn_token_match.group(2) else None
            if tok:
                member = Member.objects.filter(member_id__iexact=mid, qr_token=tok).select_related('user', 'organization', 'branch').first()
                if not member:
                    # Token was provided but failed verification -> Invalid / forged QR token!
                    return False, "Invalid QR Code: Security token verification failed.", None, "INVALID_QR"
            else:
                member = Member.objects.filter(member_id__iexact=mid).select_related('user', 'organization', 'branch').first()

        # 2. Check FN-YYYY-XXXX pattern anywhere in string
        if not member:
            id_match = re.search(r'FN-\d{4}-\d{4}', clean_input, re.IGNORECASE)
            if id_match:
                member = Member.objects.filter(member_id__iexact=id_match.group(0)).select_related('user', 'organization', 'branch').first()

        # 3. Exact member_id, phone, or username
        if not member:
            member = Member.objects.filter(member_id__iexact=clean_input).select_related('user', 'organization', 'branch').first()
        if not member:
            member = Member.objects.filter(user__phone=clean_input).select_related('user', 'organization', 'branch').first()
        if not member:
            member = Member.objects.filter(user__username__iexact=clean_input).select_related('user', 'organization', 'branch').first()

        if not member:
            return False, "Invalid QR pass: Member record not found in database.", None, "NOT_FOUND"

        # Check account status
        if member.status == Member.Status.INACTIVE:
            dummy_att = Attendance(member=member, date=today)
            return False, f"Account for {member.full_name} is marked INACTIVE. Check-in blocked.", dummy_att, "INACTIVE"

        # Validate Membership Expiry
        if not member.is_membership_active:
            dummy_att = Attendance(member=member, date=today)
            expiry_str = ""
            if member.current_membership and member.current_membership.end_date:
                expiry_str = f" (Expired on {member.current_membership.end_date.strftime('%b %d, %Y')})"
            return False, f"Membership expired{expiry_str} for {member.full_name}. Check-in blocked, please renew.", dummy_att, "EXPIRED"

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
                return True, f"SUCCESS – CHECK-OUT RECORDED! Goodbye {member.full_name}. Workout duration: {duration} mins.", existing, "CHECK_OUT"
            else:
                return False, f"Already checked in today: {member.full_name} has already completed attendance today for {today.strftime('%b %d, %Y')}.", existing, "DUPLICATE"

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
        return True, f"SUCCESS – ATTENDANCE MARKED! Welcome {member.full_name} to FitNova.", attendance, "CHECK_IN"

