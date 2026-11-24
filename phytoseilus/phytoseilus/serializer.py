from rest_framework import serializers
from api.models import ReceivedPredator


class ReceivedPredatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceivedPredator
        fields = '__all__'