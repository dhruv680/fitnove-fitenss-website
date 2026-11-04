from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'payments'

router = DefaultRouter()
router.register(r'payments', views.PaymentViewSet, basename='api-payments')
router.register(r'invoices', views.InvoiceViewSet, basename='api-invoices')
router.register(r'expenses', views.ExpenseViewSet, basename='api-expenses')

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('add/', views.payment_create, name='payment_create'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('api/', include(router.urls)),
]
