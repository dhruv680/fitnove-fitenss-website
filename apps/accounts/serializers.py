from rest_framework import serializers
from .models import User, GymOrganization, GymBranch

class GymOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GymOrganization
        fields = ['id', 'name', 'slug', 'email', 'phone', 'website', 'tax_id', 'currency', 'is_active', 'created_at']


class GymBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = GymBranch
        fields = ['id', 'organization', 'name', 'code', 'address', 'city', 'state', 'zip_code', 'phone', 'email', 'manager_name', 'is_main_branch', 'is_active']


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    branch_name = serializers.ReadOnlyField(source='branch.name')

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'organization', 'organization_name', 'branch', 'branch_name',
            'phone', 'profile_picture', 'gender', 'date_of_birth', 'address', 'is_verified', 'date_joined'
        ]
        read_only_fields = ['id', 'date_joined']

