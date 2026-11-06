from django.utils import timezone
from django.db import transaction, IntegrityError
from .models import Attendance
from apps.members.models import Member

class AttendanceService:
    @staticmethod
    def normalize_identifier(value):
        if value is None:
            return ''
        if isinstance(value, (list, tuple)):
            value = value[0] if value else ''
        return str(value).strip().strip("'\"")

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
        clean_input = AttendanceService.normalize_identifier(member_identifier)
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
                    return None, "Invalid QR Code. Security token verification failed.", "INVALID_QR"
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
            return None, "Invalid QR Code. Member not found.", "NOT_FOUND"

        return member, None, None

    @staticmethod
    def verify_member_for_attendance(member_identifier):
        """
        Verifies member status, membership expiry, and today's attendance state
        WITHOUT modifying the database.
        Returns: (can_confirm: bool, message: str, member: Member|None, action: str, existing_attendance: Attendance|None)
        """
        today = timezone.localdate()
        member, err_msg, action_code = AttendanceService.resolve_member(member_identifier)
        if not member:
            return False, err_msg or "Member Not Found.", None, action_code or "NOT_FOUND", None

        # Check account status
        if member.status == Member.Status.INACTIVE:
            return False, f"Account for {member.full_name} is marked INACTIVE. Check-in blocked.", member, "INACTIVE", None

        # Validate Membership Expiry
        if not member.is_membership_active:
            expiry_str = ""
            if member.current_membership and member.current_membership.end_date:
                expiry_str = f" (Expired on {member.current_membership.end_date.strftime('%b %d, %Y')})"
            return False, f"Membership Expired. Membership expired{expiry_str} for {member.full_name}. Please renew.", member, "EXPIRED", None

        # Check existing attendance for today (Duplicate Protection)
        existing = Attendance.objects.filter(member=member, date=today).first()
        if existing:
            check_in_formatted = timezone.localtime(existing.check_in_time).strftime('%I:%M %p') if existing.check_in_time else "earlier today"
            return False, f"Already Checked In. {member.full_name} checked in at {check_in_formatted}.", member, "DUPLICATE", existing

        return True, "Member verified! Ready for Check-In.", member, "READY_CHECK_IN", None

    @staticmethod
    @transaction.atomic
    def process_check_in(member_identifier, verified_by=None, method=Attendance.CheckInMethod.QR_CODE, is_test=False):
        """
        Processes check-in via QR payload (FITNOVA:member_id:qr_token) or raw member_id.
        Returns a tuple (success: bool, message: str, attendance: Attendance|None, action: str)
        """
        today = timezone.localdate()
        now = timezone.now()

        # If running in Test Mode: verify member without writing to database
        if is_test:
            member, err_msg, action_code = AttendanceService.resolve_member(member_identifier)
            if not member:
                return False, err_msg or "Invalid QR Code.", None, action_code or "INVALID_QR"
            dummy_att = Attendance(member=member, date=today, check_in_time=now, status=Attendance.Status.PRESENT)
            return True, f"Attendance Successful! Test scan verified for {member.full_name} (No fake record created).", dummy_att, "TEST_SUCCESS"

        can_confirm, message, member, action_code, existing = AttendanceService.verify_member_for_attendance(member_identifier)

        if not can_confirm:
            dummy_att = existing if existing else (Attendance(member=member, date=today) if member else None)
            return False, message, dummy_att, action_code

        try:
            existing_attendance = Attendance.objects.select_for_update().filter(member=member, date=today).first()
            if existing_attendance:
                check_in_formatted = timezone.localtime(existing_attendance.check_in_time).strftime('%I:%M %p') if existing_attendance.check_in_time else 'earlier today'
                return False, f"Already Checked In. {member.full_name} checked in at {check_in_formatted}.", existing_attendance, "DUPLICATE"

            attendance = Attendance.objects.create(
                member=member,
                branch=member.branch,
                date=today,
                check_in_time=now,
                method=method,
                verified_by=verified_by,
                status=Attendance.Status.PRESENT
            )
            return True, f"Attendance Successful! Welcome {member.full_name} to FitNova.", attendance, "CHECK_IN"
        except IntegrityError:
            duplicate_attendance = Attendance.objects.filter(member=member, date=today).first()
            if duplicate_attendance:
                check_in_formatted = timezone.localtime(duplicate_attendance.check_in_time).strftime('%I:%M %p') if duplicate_attendance.check_in_time else 'earlier today'
                return False, f"Already Checked In. {member.full_name} checked in at {check_in_formatted}.", duplicate_attendance, "DUPLICATE"
            raise
