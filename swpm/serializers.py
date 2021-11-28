from rest_framework import serializers
from swpm.models import *


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = '__all__'
        #fields = ('name')


class FXOSerializer(serializers.ModelSerializer):
    class Meta:
        model = FXO
        fields = '__all__'
