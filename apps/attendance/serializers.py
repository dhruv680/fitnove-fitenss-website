from rest_framework import serializers
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source='member.full_name')
    member_code = serializers.ReadOnlyField(source='member.member_id')
    branch_name = serializers.ReadOnlyField(source='branch.name')
    duration_minutes = serializers.ReadOnlyField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'member', 'member_name', 'member_code', 'branch',
            'branch_name', 'date', 'check_in_time', 'check_out_time',
            'method', 'verified_by', 'status', 'duration_minutes'
        ]

