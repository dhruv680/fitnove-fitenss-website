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
    notifications = request.user.notifications.all()
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)

    return render(request, 'notifications/notification_list.html', {
        'notifications': notifications,
        'filter_type': filter_type,
        'unread_count': request.user.notifications.filter(is_read=False).count()
    })


@login_required
def mark_read(request, pk):
    notification = get_object_or_404(request.user.notifications, pk=pk)
    notification.is_read = True
    notification.save()
    if notification.action_url:
        return redirect(notification.action_url)
    return redirect('notifications:list')


@login_required
def mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:list')


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return self.request.user.notifications.all()
