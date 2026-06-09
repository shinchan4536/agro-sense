from rest_framework import serializers
from .models import Crop, Prediction

class CropSerializers(serializers.ModelSerializer):
    class Meta:
        model = Crop
        fields = '__all__'

class PredictionSerializer(serializers.ModelSerializer):
    crop_details = CropSerializers(source='crop',read_only=True)
    class Meta:
        model = Prediction
        fields = ['id', 'crop', 'crop_details', 'location', 'weather_temp', 'weather_humidity', 'disease_probability', 'yield_risk', 'created_at']