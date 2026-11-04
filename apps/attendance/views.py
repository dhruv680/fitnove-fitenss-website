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
    return render(request, 'attendance/scanner.html')


@login_required
@staff_or_admin
def api_scan_qr(request):
    if request.method == 'POST':
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
            member_data = {
                'id': member.id,
                'name': member.full_name,
                'member_id': member.member_id,
                'plan': member.current_membership.plan.name if member.current_membership else 'No Plan',
                'photo_url': member.user.profile_picture.url if member.user.profile_picture else None,
                'check_in_time': attendance.check_in_time.strftime('%I:%M %p') if attendance.check_in_time else '',
                'check_out_time': attendance.check_out_time.strftime('%I:%M %p') if attendance.check_out_time else '',
                'duration': f"{attendance.duration_minutes} mins" if attendance.duration_minutes else None,
            }

        return JsonResponse({
            'success': success,
            'message': message,
            'action': action_type,
            'member': member_data
        })

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)


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
