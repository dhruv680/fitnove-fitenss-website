import re
from apps.accounts.models import GymOrganization

def global_fitnova_context(request):
    unread_count = 0
    recent_notifications = []
    current_org = None
    current_branch = None

    if request.user.is_authenticated:
        try:
            notifications_qs = request.user.notifications.all()
            unread_count = notifications_qs.filter(is_read=False).count()
            recent_notifications = notifications_qs[:5]
        except Exception:
            pass

        current_org = getattr(request.user, 'organization', None)
        current_branch = getattr(request.user, 'branch', None)

    if not current_org:
        try:
            current_org = GymOrganization.objects.first()
        except Exception:
            current_org = None

    # Resolve phone for direct WhatsApp chat (format wa.me/<digits>)
    wa_number = "15557492000"
    if current_org and current_org.phone:
        cleaned = re.sub(r'\D', '', current_org.phone)
        if cleaned:
            wa_number = cleaned

    whatsapp_url = f"https://wa.me/{wa_number}?text=Hello%20FitNova!%20I%20would%20like%20to%20inquire%20about%20gym%20memberships."

    social_links = {
        'instagram': getattr(current_org, 'instagram_url', None) or 'https://www.instagram.com/fitnova_fitness/',
        'linkedin': getattr(current_org, 'linkedin_url', None) or 'https://www.linkedin.com/company/fitnova-fitness/',
        'whatsapp': whatsapp_url,
        'twitter': getattr(current_org, 'twitter_url', None) or 'https://twitter.com/fitnovafit',
    }

    return {
        'unread_notifications_count': unread_count,
        'recent_notifications': recent_notifications,
        'current_org': current_org,
        'current_branch': current_branch,
        'social_links': social_links,
    }


