from django.contrib import admin
from .models import Payment, Invoice, Expense


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'member', 'total_amount', 'payment_method', 'status', 'payment_date', 'branch')
    list_filter = ('status', 'payment_method', 'payment_date', 'branch', 'organization')
    search_fields = ('transaction_id', 'member__member_id', 'member__user__username', 'member__user__first_name', 'member__user__last_name')
    date_hierarchy = 'payment_date'


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'payment', 'total', 'status', 'issue_date', 'due_date')
    list_filter = ('status', 'issue_date', 'due_date')
    search_fields = ('invoice_number', 'payment__transaction_id', 'payment__member__user__username')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'amount', 'date', 'branch', 'organization')
    list_filter = ('category', 'date', 'branch', 'organization')
    search_fields = ('title', 'vendor', 'invoice_reference')
    date_hierarchy = 'date'
