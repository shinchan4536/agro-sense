import os
import pandas as pd
import numpy as np
import joblib
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework import status
from PIL import Image
from rest_framework.response import Response

from .models import Crop, Prediction, DiseaseScan
from .serializers import CropSerializers, PredictionSerializer
from .utils import get_live_weather, get_disease_forecast

# TensorFlow / Keras imports for the Vision Model
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

# Silence TensorFlow's C++ informational logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

RF_MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'crop_risk_model.pkl')
try:
    ml_model = joblib.load(RF_MODEL_PATH)
except Exception as e:
    print(f"⚠️ Warning: Could not load Tabular ML model: {e}")
    ml_model = None

CNN_MODEL_PATH = os.path.join(settings.BASE_DIR, 'ml_models', 'plant_disease_model.h5')
try:
    cnn_model = load_model(CNN_MODEL_PATH)
except Exception as e:
    print(f"⚠️ Warning: Could not load CNN Vision model: {e}")
    cnn_model = None

CLASS_NAMES = [
    'Apple___Apple_scab', 'Apple___Black_rot', 'Apple___Cedar_apple_rust', 'Apple___healthy', 
    'Blueberry___healthy', 'Cherry_(including_sour)___Powdery_mildew', 'Cherry_(including_sour)___healthy', 
    'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', 'Corn_(maize)___Common_rust_', 
    'Corn_(maize)___Northern_Leaf_Blight', 'Corn_(maize)___healthy', 'Grape___Black_rot', 
    'Grape___Esca_(Black_Measles)', 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', 'Grape___healthy', 
    'Orange___Haunglongbing_(Citrus_greening)', 'Peach___Bacterial_spot', 'Peach___healthy', 
    'Pepper,_bell___Bacterial_spot', 'Pepper,_bell___healthy', 'Potato___Early_blight', 
    'Potato___Late_blight', 'Potato___healthy', 'Raspberry___healthy', 'Soybean___healthy', 
    'Squash___Powdery_mildew', 'Strawberry___Leaf_scorch', 'Strawberry___healthy', 
    'Tomato___Bacterial_spot', 'Tomato___Early_blight', 'Tomato___Late_blight', 'Tomato___Leaf_Mold', 
    'Tomato___Septoria_leaf_spot', 'Tomato___Spider_mites Two-spotted_spider_mite', 
    'Tomato___Target_Spot', 'Tomato___Tomato_Yellow_Leaf_Curl_Virus', 'Tomato___Tomato_mosaic_virus', 
    'Tomato___healthy'
]

@api_view(['GET'])
def get_all_crops(request):
    crops = Crop.objects.all()
    serializer = CropSerializers(crops, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def create_prediction(request):
    location = request.data.get('location')
    crop_id = request.data.get('crop_id')

    if not location or not crop_id:
        return Response({"error": "Please provide both location and crop_id."}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        crop = Crop.objects.get(id=crop_id)
    except Crop.DoesNotExist:
        return Response({"error": "Crop not found in the database."}, status=status.HTTP_404_NOT_FOUND)
    
    weather_data = get_live_weather(location)
    if not weather_data:
        return Response({"error": f"Could not fetch weather for {location}. Check spelling or API key."}, status=status.HTTP_400_BAD_REQUEST)
    
    temp = weather_data['temperature']
    humidity = weather_data['humidity']

    if ml_model:
        input_data = pd.DataFrame([[temp, humidity]], columns=['temperature', 'humidity'])
        ai_optimal_crop = ml_model.predict(input_data)[0]
        if ai_optimal_crop.lower() == crop.name.lower():
            calculated_yield_risk = 'Low'
            calculated_disease_prob = 12.5 # Low risk
        else:
            calculated_yield_risk = 'High'
            calculated_disease_prob = 85.0 # High risk because the weather is meant for a different crop!
    else:
        calculated_yield_risk = 'Medium'
        calculated_disease_prob = 50.0

    prediction = Prediction.objects.create(
        crop=crop,
        location=location,
        weather_temp=temp,
        weather_humidity=humidity,
        disease_probability=calculated_disease_prob,
        yield_risk=calculated_yield_risk
    )

    serializer = PredictionSerializer(prediction)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def diagnose_disease(request):
    """Handles Image uploads to diagnose crop diseases using the CNN model."""
    if not cnn_model:
        return Response({'error': 'CNN Vision model is offline.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    try:
        uploaded_file = request.FILES.get('image')
        location = request.data.get('location', 'Coimbatore') 
        
        if not uploaded_file:
            return Response({'error': 'No image file provided in the request payload.'}, status=status.HTTP_400_BAD_REQUEST)
            
        img = Image.open(uploaded_file)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img = img.resize((128, 128))
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        predictions = cnn_model.predict(img_array)
        predicted_class_idx = np.argmax(predictions[0])
        confidence = float(predictions[0][predicted_class_idx])
        # --- UX UPGRADE: CONFIDENCE BOUNCER ---
        if confidence < 0.60:
            return Response({
                "status": "warning",
                "message": "Image is unclear or lighting is poor. Please retake the photo closer to the affected leaf.",
                "confidence_score": round(confidence * 100, 2)
            }, status=status.HTTP_200_OK)
        result_label = CLASS_NAMES[predicted_class_idx]
        
        # Fetch External Environmental Metrics using your custom utility!
        # Fetch External Environmental Metrics
        weather_data = get_live_weather(location)
        forecast_data = get_disease_forecast(location)
        
        # Save to PostgreSQL securely inside the try block
        scan_record = DiseaseScan.objects.create(
            image=uploaded_file,
            location=location,
            crop_stage="N/A",  # Passed defaults to avoid database errors
            disease_detected=result_label,
            confidence_score=round(confidence * 100, 2),
            triage_urgency="N/A"
        )
        
        return Response({
            "status": "success",
            "scan_id": scan_record.id,
            "prediction": result_label,
            "confidence_score": round(confidence * 100, 2),
            "environmental_context": {
                "location": location,
                "live_weather": weather_data if weather_data else "Weather data unavailable",
                "5_day_forecast": forecast_data if forecast_data else "Forecast unavailable"
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({'error': f'Internal engine error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)