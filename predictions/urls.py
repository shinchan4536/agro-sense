from django.urls import path
from . import views

app_name = "predict"
urlpatterns = [
    path('crops/',views.get_all_crops,name='get_crops'),
    path('predict/',views.create_prediction,name='create_prediction'),
    path('diagnose/',views.diagnose_disease, name='diagnose_disease'),
]