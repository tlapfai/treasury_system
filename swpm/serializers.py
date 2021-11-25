from rest_framework import serializers
from swpm.models import *


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'
        #fields = ('id', 'song', 'singer', 'last_modify_date', 'created')