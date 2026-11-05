from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from .models import Attendance
from .services import AttendanceService
from .serializers import AttendanceSerializer

@login_required
@staff_or_admin
def attendance_list(request):
    attendances = AttendanceService.get_scoped_attendance(request.user)

    search_query = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        attendances = attendances.filter(
            member__user__first_name__icontains=search_query
        ) | attendances.filter(
            member__user__last_name__icontains=search_query
        ) | attendances.filter(
            member__member_id__icontains=search_query
        )

    if date_filter:
        attendances = attendances.filter(date=date_filter)

    if status_filter:
        attendances = attendances.filter(status=status_filter)

    today = timezone.now().date()
    today_total = Attendance.objects.filter(date=today)
    if not request.user.is_super_admin:
        today_total = today_total.filter(member__organization=request.user.organization)

    today_count = today_total.count()
    active_now = today_total.filter(status=Attendance.Status.PRESENT, check_out_time__isnull=True).count()
    completed_today = today_total.filter(status=Attendance.Status.CHECKED_OUT).count()

    paginator = Paginator(attendances, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'attendance/attendance_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'today_count': today_count,
        'active_now': active_now,
        'completed_today': completed_today,
    })


@login_required
@staff_or_admin
def attendance_scanner(request):
    from apps.members.services import MemberService
    scoped_members = MemberService.get_scoped_members(request.user)
    demo_members = scoped_members.filter(status='ACTIVE')[:6]

    today = timezone.now().date()
    today_total = AttendanceService.get_scoped_attendance(request.user).filter(date=today)
    today_count = today_total.count()
    active_now = today_total.filter(status=Attendance.Status.PRESENT, check_out_time__isnull=True).count()
    completed_today = today_total.filter(status=Attendance.Status.CHECKED_OUT).count()
    recent_logs = today_total.select_related('member__user').prefetch_related('member__memberships__plan').order_by('-id')[:8]

    return render(request, 'attendance/scanner.html', {
        'demo_members': demo_members,
        'today_count': today_count,
        'active_now': active_now,
        'completed_today': completed_today,
        'recent_logs': recent_logs,
    })


@login_required
@staff_or_admin
def api_verify_member(request):
    """
    Step 1 of Smart Focus Scanner:
    Verifies a scanned QR code or member ID on backend.
    Returns member details and validation status WITHOUT recording attendance.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    identifier = request.POST.get('identifier', '').strip()
    if not identifier:
        return JsonResponse({'success': False, 'message': 'No identifier provided.'}, status=400)

    can_confirm, message, member, action_code, existing = AttendanceService.verify_member_for_attendance(identifier)

    member_data = None
    if member:
        curr_sub = member.current_membership
        today = timezone.now().date()
        photo_url = None
        if member.user.profile_picture and hasattr(member.user.profile_picture, 'url'):
            try:
                photo_url = member.user.profile_picture.url
            except Exception:
                photo_url = None

        member_data = {
            'id': member.id,
            'name': member.full_name,
            'member_id': member.member_id,
            'phone': member.user.phone or '—',
            'plan': curr_sub.plan.name if curr_sub else 'No Plan Assigned',
            'plan_expiry': curr_sub.end_date.strftime('%b %d, %Y') if curr_sub and curr_sub.end_date else '—',
            'is_membership_active': member.is_membership_active,
            'status': member.status,
            'status_display': member.get_status_display(),
            'photo_url': photo_url,
            'existing_check_in': existing.check_in_time.strftime('%I:%M %p') if (existing and existing.check_in_time) else None,
            'existing_check_out': existing.check_out_time.strftime('%I:%M %p') if (existing and existing.check_out_time) else None,
            'identifier': identifier,
        }

    return JsonResponse({
        'success': can_confirm,
        'message': message,
        'action': action_code,
        'member': member_data,
    })


@login_required
@staff_or_admin
def api_confirm_attendance(request):
    """
    Step 2 of Smart Focus Scanner:
    Called when the user clicks [OK - CONFIRM ATTENDANCE].
    Re-verifies on backend and atomically records attendance/check-out.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    identifier = request.POST.get('identifier', '').strip()
    if not identifier:
        return JsonResponse({'success': False, 'message': 'No identifier provided.'}, status=400)

    success, message, attendance, action_type = AttendanceService.process_check_in(
        member_identifier=identifier,
        verified_by=request.user,
        method=Attendance.CheckInMethod.QR_CODE
    )

    member_data = None
    if attendance and attendance.member:
        member = attendance.member
        curr_sub = member.current_membership
        today = timezone.now().date()
        photo_url = None
        if member.user.profile_picture and hasattr(member.user.profile_picture, 'url'):
            try:
                photo_url = member.user.profile_picture.url
            except Exception:
                photo_url = None

        member_data = {
            'id': member.id,
            'name': member.full_name,
            'member_id': member.member_id,
            'phone': member.user.phone or '—',
            'plan': curr_sub.plan.name if curr_sub else 'No Plan Assigned',
            'plan_expiry': curr_sub.end_date.strftime('%b %d, %Y') if curr_sub and curr_sub.end_date else '—',
            'photo_url': photo_url,
            'check_in_date': today.strftime('%b %d, %Y'),
            'check_in_time': attendance.check_in_time.strftime('%I:%M %p') if attendance.check_in_time else '',
            'check_out_time': attendance.check_out_time.strftime('%I:%M %p') if attendance.check_out_time else '',
            'duration': f"{attendance.duration_minutes} mins" if attendance.duration_minutes else None,
            'status': member.status,
            'status_display': member.get_status_display(),
        }

    # Live statistics
    today_total_qs = AttendanceService.get_scoped_attendance(request.user).filter(date=timezone.now().date())
    today_total = today_total_qs.count()
    active_now = today_total_qs.filter(status=Attendance.Status.PRESENT, check_out_time__isnull=True).count()
    completed_today = today_total_qs.filter(status=Attendance.Status.CHECKED_OUT).count()

    return JsonResponse({
        'success': success,
        'message': message,
        'action': action_type,
        'member': member_data,
        'stats': {
            'today_total': today_total,
            'active_now': active_now,
            'completed_today': completed_today,
        }
    })


@login_required
@staff_or_admin
def api_scan_qr(request):
    """Direct scan endpoint (also routes to api_confirm_attendance for unified handling)."""
    return api_confirm_attendance(request)


@login_required
@staff_or_admin
def api_reset_today_attendance(request):
    """Allows staff/admins to reset today's attendance for a specific member during kiosk testing."""
    if request.method == 'POST':
        member_id = request.POST.get('member_id', '').strip()
        if not member_id:
            return JsonResponse({'success': False, 'message': 'Member ID required.'}, status=400)
        today = timezone.now().date()
        from django.db.models import Q
        deleted_count, _ = Attendance.objects.filter(
            Q(member__member_id__iexact=member_id) | Q(member__id__iexact=int(member_id) if member_id.isdigit() else 0),
            date=today
        ).delete()
        return JsonResponse({
            'success': True,
            'message': f"Today's attendance record cleared ({deleted_count} deleted). You can now re-test check-in for this member."
        })
    return JsonResponse({'success': False, 'message': 'Method not allowed.'}, status=405)


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return AttendanceService.get_scoped_attendance(self.request.user)

    @action(detail=False, methods=['post'])
    def scan(self, request):
        identifier = request.data.get('identifier', '').strip()
        if not identifier:
            return Response({'success': False, 'message': 'Identifier required.'}, status=400)

        success, msg, att, action_type = AttendanceService.process_check_in(
            member_identifier=identifier,
            verified_by=request.user,
            method=Attendance.CheckInMethod.QR_CODE
        )
        return Response({'success': success, 'message': msg, 'action': action_type})

