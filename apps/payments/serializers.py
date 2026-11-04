from rest_framework import serializers
from .models import Payment, Invoice, Expense

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'issue_date', 'due_date', 'subtotal', 'tax', 'total', 'status']


class PaymentSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.full_name')
    member_code = serializers.ReadOnlyField(source='member.member_id')
    invoice = InvoiceSerializer(read_only=True)
    currency = serializers.ReadOnlyField(source='organization.currency')

    class Meta:
        model = Payment
        fields = [
            'id', 'organization', 'branch', 'member', 'member_name',
            'member_code', 'membership', 'amount', 'tax_amount',
            'total_amount', 'currency', 'payment_method', 'transaction_id',
            'status', 'payment_date', 'notes', 'invoice'
        ]


class ExpenseSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.ReadOnlyField(source='recorded_by.get_full_name')

    class Meta:
        model = Expense
        fields = [
            'id', 'organization', 'branch', 'category', 'title',
            'amount', 'date', 'paid_to', 'recorded_by', 'recorded_by_name', 'notes'
        ]

