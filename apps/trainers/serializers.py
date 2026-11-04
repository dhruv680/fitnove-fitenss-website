from rest_framework import serializers
from .models import Trainer
from apps.accounts.serializers import UserSerializer

class TrainerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField()
    phone = serializers.ReadOnlyField()
    assigned_members_count = serializers.ReadOnlyField()

    class Meta:
        model = Trainer
        fields = [
            'id', 'user', 'organization', 'branch', 'employee_id',
            'full_name', 'email', 'phone', 'specialization', 'bio',
            'experience_years', 'certifications', 'hourly_rate',
            'rating', 'status', 'joined_date', 'assigned_members_count'
        ]
