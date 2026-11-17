from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from rest_framework import viewsets, serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'action_url', 'created_at']


@login_required
def notification_list(request):
    all_notifications = request.user.notifications.all()
    unread_count = all_notifications.filter(is_read=False).count()
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'unread':
        notifications = all_notifications.filter(is_read=False)
    else:
        notifications = all_notifications

    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'filter_type': filter_type,
        'unread_count': unread_count,
        'total_count': all_notifications.count()
    })


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.is_read = True
    notification.save()

    unread_count = request.user.notifications.filter(is_read=False).count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({
            'success': True,
            'id': notification.id,
            'unread_count': unread_count,
            'action_url': notification.action_url or ''
        })

    if request.GET.get('navigate') == '1' and notification.action_url:
        return redirect(notification.action_url)

    referer = request.META.get('HTTP_REFERER')
    if referer and 'notifications' in referer:
        return redirect(referer)
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('ajax') == '1':
        return JsonResponse({'success': True, 'unread_count': 0})

    referer = request.META.get('HTTP_REFERER')
    if referer and 'notifications' in referer:
        return redirect(referer)
    return redirect('notifications:list')


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.all()

