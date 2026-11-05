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
    def resolve_member(member_identifier):
        """
        Parses member_identifier and returns (member, error_msg, action_code).
        If resolution fails, member is None, error_msg is str, action_code is 'INVALID_QR' | 'NOT_FOUND'.
        """
        import re
        clean_input = member_identifier.strip().strip('\'"').strip()
        member = None

        # 1. Check FITNOVA:ID:TOKEN pattern
        if clean_input.upper().startswith('FITNOVA:'):
            parts = clean_input.split(':', 2)
            if len(parts) >= 3 and parts[2].strip():
                mid = parts[1].strip()
                tok = parts[2].strip()
                try:
                    import uuid
                    uuid_val = uuid.UUID(tok)
                    member = Member.objects.filter(member_id__iexact=mid, qr_token=uuid_val).select_related('user', 'organization', 'branch').first()
                except (ValueError, TypeError, Exception):
                    member = None
                if not member:
                    return None, "Invalid QR Code: Security token verification failed.", "INVALID_QR"
            elif len(parts) >= 2:
                mid = parts[1].strip()
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
            return None, "Member Not Found: Invalid QR pass.", "NOT_FOUND"

        return member, None, None

    @staticmethod
    def verify_member_for_attendance(member_identifier):
        """
        Verifies member status, membership expiry, and today's attendance state
        WITHOUT modifying the database.
        Returns: (can_confirm: bool, message: str, member: Member|None, action: str, existing_attendance: Attendance|None)
        """
        today = timezone.now().date()
        member, err_msg, action_code = AttendanceService.resolve_member(member_identifier)
        if not member:
            return False, err_msg, None, action_code, None

        # Check account status
        if member.status == Member.Status.INACTIVE:
            return False, f"Account for {member.full_name} is marked INACTIVE. Check-in blocked.", member, "INACTIVE", None

        # Validate Membership Expiry
        if not member.is_membership_active:
            expiry_str = ""
            if member.current_membership and member.current_membership.end_date:
                expiry_str = f" (Expired on {member.current_membership.end_date.strftime('%b %d, %Y')})"
            return False, f"Membership Expired – Attendance Denied: Membership expired{expiry_str} for {member.full_name}. Please renew.", member, "EXPIRED", None

        # Check existing attendance for today
        existing = Attendance.objects.filter(member=member, date=today).first()
        if existing:
            if existing.status == Attendance.Status.PRESENT and not existing.check_out_time:
                return True, f"Member verified! Currently checked in. Next scan will record Check-Out.", member, "READY_CHECK_OUT", existing
            else:
                return False, f"Attendance Already Marked Today: {member.full_name} has already completed attendance today for {today.strftime('%b %d, %Y')}.", member, "DUPLICATE", existing

        return True, f"Member verified! Ready for Check-In.", member, "READY_CHECK_IN", None

    @staticmethod
    @transaction.atomic
    def process_check_in(member_identifier, verified_by=None, method=Attendance.CheckInMethod.QR_CODE):
        """
        Processes check-in/out via QR payload (FITNOVA:member_id:qr_token) or raw member_id.
        Returns a tuple (success: bool, message: str, attendance: Attendance|None, action: str)
        """
        today = timezone.now().date()
        can_confirm, message, member, action_code, existing = AttendanceService.verify_member_for_attendance(member_identifier)

        if not can_confirm:
            dummy_att = Attendance(member=member, date=today) if member else None
            return False, message, dummy_att, action_code

        now = timezone.now()
        if action_code == "READY_CHECK_OUT" and existing:
            existing.check_out_time = now
            existing.status = Attendance.Status.CHECKED_OUT
            existing.save(update_fields=['check_out_time', 'status'])
            duration = existing.duration_minutes
            return True, f"✓ CHECK-OUT RECORDED! Goodbye {member.full_name}. Workout duration: {duration} mins.", existing, "CHECK_OUT"

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
        return True, f"✓ ATTENDANCE MARKED SUCCESSFULLY! Welcome {member.full_name} to FitNova.", attendance, "CHECK_IN"
