from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.utils import timezone
from rest_framework import viewsets
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from apps.members.models import Member
from apps.memberships.models import MembershipPlan
from .models import Payment, Invoice, Expense
from .services import PaymentService
from .serializers import PaymentSerializer, InvoiceSerializer, ExpenseSerializer

@login_required
@staff_or_admin
def payment_list(request):
    payments = PaymentService.get_scoped_payments(request.user)

    search_query = request.GET.get('search', '').strip()
    method_filter = request.GET.get('method', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        payments = payments.filter(
            Q(member__user__first_name__icontains=search_query) |
            Q(member__user__last_name__icontains=search_query) |
            Q(transaction_id__icontains=search_query) |
            Q(member__member_id__icontains=search_query)
        )

    if method_filter:
        payments = payments.filter(payment_method=method_filter)

    if status_filter:
        payments = payments.filter(status=status_filter)

    total_revenue = payments.filter(status=Payment.Status.COMPLETED).aggregate(Sum('total_amount'))['total_amount__sum'] or 0

    paginator = Paginator(payments, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/payment_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'method_filter': method_filter,
        'status_filter': status_filter,
        'total_revenue': total_revenue,
        'total_payments': payments.count()
    })


@login_required
@staff_or_admin
def payment_create(request):
    org = request.user.organization
    members = Member.objects.all()
    plans = MembershipPlan.objects.filter(is_active=True)
    if not request.user.is_super_admin:
        members = members.filter(organization=org)
        plans = plans.filter(organization=org)

    preselected_member = request.GET.get('member')

    if request.method == 'POST':
        member_id = request.POST.get('member_id')
        plan_id = request.POST.get('plan_id')
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method', 'UPI')
        transaction_id = request.POST.get('transaction_id', '').strip()
        notes = request.POST.get('notes', '').strip()

        member = get_object_or_404(members, id=member_id)
        plan = get_object_or_404(plans, id=plan_id)

        try:
            payment, invoice = PaymentService.record_membership_payment(
                member=member,
                plan=plan,
                amount=amount,
                payment_method=payment_method,
                recorded_by=request.user,
                transaction_id=transaction_id or None,
                notes=notes
            )
            messages.success(request, f"Payment of {member.organization.currency}{payment.total_amount} recorded! Invoice #{invoice.invoice_number} created.")
            return redirect('payments:invoice_detail', pk=invoice.pk)
        except Exception as e:
            messages.error(request, f"Failed to record payment: {str(e)}")

    return render(request, 'payments/payment_form.html', {
        'members': members,
        'plans': plans,
        'preselected_member': preselected_member
    })


@login_required
def invoice_list(request):
    invoices = PaymentService.get_scoped_invoices(request.user)

    if request.user.is_member:
        invoices = invoices.filter(payment__member__user=request.user)

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if search_query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search_query) |
            Q(payment__member__user__first_name__icontains=search_query) |
            Q(payment__member__user__last_name__icontains=search_query)
        )

    if status_filter:
        invoices = invoices.filter(status=status_filter)

    paginator = Paginator(invoices, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/invoice_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter
    })


@login_required
def invoice_detail(request, pk):
    invoices = PaymentService.get_scoped_invoices(request.user)
    if request.user.is_member:
        invoices = invoices.filter(payment__member__user=request.user)

    invoice = get_object_or_404(invoices, pk=pk)
    return render(request, 'payments/invoice_detail.html', {'invoice': invoice})


@login_required
@staff_or_admin
def expense_list(request):
    expenses = PaymentService.get_scoped_expenses(request.user)

    category_filter = request.GET.get('category', '').strip()
    search_query = request.GET.get('search', '').strip()

    if category_filter:
        expenses = expenses.filter(category=category_filter)

    if search_query:
        expenses = expenses.filter(
            Q(title__icontains=search_query) |
            Q(paid_to__icontains=search_query)
        )

    total_expense = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    paginator = Paginator(expenses, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'payments/expense_list.html', {
        'page_obj': page_obj,
        'category_filter': category_filter,
        'search_query': search_query,
        'total_expense': total_expense,
        'categories': Expense.Category.choices
    })


@login_required
@staff_or_admin
def expense_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'OTHER')
        amount = request.POST.get('amount', '0.00')
        date = request.POST.get('date') or timezone.now().date()
        paid_to = request.POST.get('paid_to', '').strip()
        notes = request.POST.get('notes', '').strip()

        Expense.objects.create(
            organization=request.user.organization,
            branch=request.user.branch,
            title=title,
            category=category,
            amount=amount,
            date=date,
            paid_to=paid_to,
            recorded_by=request.user,
            notes=notes
        )
        messages.success(request, f"Expense '{title}' recorded successfully.")
        return redirect('payments:expense_list')

    return render(request, 'payments/expense_form.html', {
        'categories': Expense.Category.choices
    })


class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return PaymentService.get_scoped_payments(self.request.user)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return PaymentService.get_scoped_invoices(self.request.user)


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        return PaymentService.get_scoped_expenses(self.request.user)
