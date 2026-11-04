def global_fitnova_context(request):
    if not request.user.is_authenticated:
        return {}

    unread_count = 0
    recent_notifications = []
    try:
        notifications_qs = request.user.notifications.all()
        unread_count = notifications_qs.filter(is_read=False).count()
        recent_notifications = notifications_qs[:5]
    except Exception:
        pass

    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'current_org': getattr(request.user, 'organization', None),
        'current_branch': getattr(request.user, 'branch', None),
    }
