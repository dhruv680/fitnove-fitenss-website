from django.urls import path
from . import views

app_name = 'facilities'

urlpatterns = [
    # 1. Olympic Free-Weight Zone
    path('free-weights/', views.free_weights_view, name='free_weights'),
    path('equipment/add/', views.add_equipment_view, name='add_equipment'),
    path('equipment/<int:pk>/status/', views.toggle_equipment_status_view, name='toggle_equipment_status'),

    # 2. Cardio Theater & HIIT Lab
    path('cardio-hiit/', views.cardio_hiit_view, name='cardio_hiit'),
    path('cardio-hiit/program/add/', views.add_cardio_program_view, name='add_cardio_program'),

    # 3. Functional Sprint Turf
    path('sprint-turf/', views.sprint_turf_view, name='sprint_turf'),
    path('sprint-turf/book/<int:session_id>/', views.book_turf_session_view, name='book_turf_session'),
    path('sprint-turf/session/add/', views.add_turf_session_view, name='add_turf_session'),

    # 4. Smart Biometric Access
    path('biometric-access/', views.biometric_access_view, name='biometric_access'),
    path('api/biometric-verify/', views.api_biometric_verify_view, name='api_biometric_verify'),

    # 5. Recovery & Cryo Spa
    path('recovery-spa/', views.recovery_spa_view, name='recovery_spa'),
    path('recovery-spa/book/', views.book_recovery_view, name='book_recovery'),
    path('recovery-spa/booking/<int:booking_id>/status/', views.update_recovery_booking_status_view, name='update_recovery_booking_status'),

    # 6. Athlete Fuel Bar & Lounge
    path('fuel-bar/', views.fuel_bar_view, name='fuel_bar'),
    path('fuel-bar/order/', views.create_fuel_order_view, name='create_fuel_order'),
    path('fuel-bar/order/<int:order_id>/status/', views.update_fuel_order_status_view, name='update_fuel_order_status'),
    path('fuel-bar/item/add/', views.add_fuel_item_view, name='add_fuel_item'),
    path('fuel-bar/item/<int:pk>/availability/', views.toggle_fuel_item_availability_view, name='toggle_fuel_item_availability'),
]
