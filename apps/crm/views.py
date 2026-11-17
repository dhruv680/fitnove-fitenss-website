from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import viewsets, serializers
from apps.accounts.permissions import staff_or_admin, IsStaffOrAdminUser
from .models import Lead

class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = '__all__'


@login_required
@staff_or_admin
def lead_list(request):
    base_leads = Lead.objects.all()
    if not request.user.is_super_admin:
        base_leads = base_leads.filter(organization=request.user.organization)

    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    # Search filter applied to pipeline
    if search:
        search_qs = base_leads.filter(
            Q(full_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search)
        )
    else:
        search_qs = base_leads

    # Accurate pipeline counts across all stages
    counts = {
        'total': base_leads.count(),
        'new': base_leads.filter(status=Lead.Status.NEW).count(),
        'contacted': base_leads.filter(status=Lead.Status.CONTACTED).count(),
        'trial': base_leads.filter(status=Lead.Status.TRIAL_SCHEDULED).count(),
        'converted': base_leads.filter(status=Lead.Status.CONVERTED).count(),
        'lost': base_leads.filter(status=Lead.Status.LOST).count(),
    }

    leads = search_qs
    if status_filter:
        leads = leads.filter(status=status_filter)

    paginator = Paginator(leads, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'crm/lead_list.html', {
        'page_obj': page_obj,
        'search_query': search,
        'status_filter': status_filter,
        'counts': counts,
        'statuses': Lead.Status.choices
    })


@login_required
@staff_or_admin
def lead_create(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        source = request.POST.get('source', 'WALK_IN')
        interest = request.POST.get('interest', 'General Gym Membership').strip()
        trial_date = request.POST.get('trial_date') or None
        follow_up_date = request.POST.get('follow_up_date') or None
        notes = request.POST.get('notes', '').strip()

        if not full_name:
            messages.error(request, "Prospect full name is required.")
            return render(request, 'crm/lead_form.html', {
                'sources': Lead.Source.choices,
                'form_data': request.POST
            })

        if not phone:
            messages.error(request, "Contact phone number is required.")
            return render(request, 'crm/lead_form.html', {
                'sources': Lead.Source.choices,
                'form_data': request.POST
            })

        lead = Lead.objects.create(
            organization=request.user.organization,
            branch=request.user.branch,
            full_name=full_name,
            phone=phone,
            email=email,
            source=source,
            interest=interest,
            trial_date=trial_date,
            follow_up_date=follow_up_date,
            notes=notes,
            status=Lead.Status.NEW
        )
        messages.success(request, f"Inquiry lead for {lead.full_name} captured successfully!")
        return redirect('crm:lead_list')

    return render(request, 'crm/lead_form.html', {
        'sources': Lead.Source.choices
    })


@login_required
@staff_or_admin
def lead_update_status(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if not request.user.is_super_admin and lead.organization != request.user.organization:
        messages.error(request, "Permission denied.")
        return redirect('crm:lead_list')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        note = request.POST.get('note', '').strip()
        if new_status in Lead.Status.values:
            lead.status = new_status
            if note:
                lead.notes += f"\n[{lead.get_status_display()}]: {note}"
            lead.save()
            msg = f"Lead status updated to {lead.get_status_display()}."
            messages.success(request, msg)

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': lead.status,
                    'status_display': lead.get_status_display(),
                    'message': msg
                })

    return redirect('crm:lead_list')


class LeadViewSet(viewsets.ModelViewSet):
    serializer_class = LeadSerializer
    permission_classes = [IsStaffOrAdminUser]

    def get_queryset(self):
        user = self.request.user
        if user.is_super_admin:
            return Lead.objects.all()
        return Lead.objects.filter(organization=user.organization)

