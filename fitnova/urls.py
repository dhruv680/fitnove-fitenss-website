from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('members/', include('apps.members.urls', namespace='members')),
    path('memberships/', include('apps.memberships.urls', namespace='memberships')),
    path('attendance/', include('apps.attendance.urls', namespace='attendance')),
    path('payments/', include('apps.payments.urls', namespace='payments')),
    path('trainers/', include('apps.trainers.urls', namespace='trainers')),
    path('fitness/', include('apps.fitness.urls', namespace='fitness')),
    path('classes/', include('apps.classes.urls', namespace='classes')),
    path('crm/', include('apps.crm.urls', namespace='crm')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
