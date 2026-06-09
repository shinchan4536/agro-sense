from django.db import models

# Create your models here.

class Crop(models.Model):
    name = models.CharField(max_length=100)
    optimal_temperature = models.FloatField(help_text="In Celsius")
    optimal_humidity = models.FloatField(help_text="Percentage")
    region = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class Prediction(models.Model):
    RISK_CHOICES = [
        ('Low','Low Risk'),
        ('Medium','Medium Risk'),
        ('High','High Risk'),
    ]

    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    location = models.CharField(max_length=200)
    weather_temp = models.FloatField()
    weather_humidity = models.FloatField()

    disease_probability = models.FloatField(help_text="Percentage 0-100")
    yield_risk = models.CharField(max_length=10, choices=RISK_CHOICES)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop.name} at {self.location} - {self.created_at.strftime('%Y-%M-%D')}"
    

class DiseaseScan(models.Model):
    # Django will automatically save the image to /media/disease_scans/
    image = models.ImageField(upload_to='disease_scans/') 
    location = models.CharField(max_length=255)
    crop_stage = models.CharField(max_length=100)
    
    # AI Intelligence
    disease_detected = models.CharField(max_length=255)
    confidence_score = models.FloatField()
    triage_urgency = models.CharField(max_length=255)
    
    # Automatic Timestamp
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.disease_detected} detected in {self.location}"