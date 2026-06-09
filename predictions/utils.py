import requests
import os

def get_live_weather(location):
    api_key = os.environ.get('WEATHER_API_KEY') # <-- UPDATED LINE
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        return {
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity']
        }
    else:
        return None

def get_disease_forecast(location):
    """Fetches a clean 5-day weather forecast (Temperature & Humidity) for the frontend."""
    if not location:
        return None
        
    api_key = os.environ.get('WEATHER_API_KEY')
    url = f"http://api.openweathermap.org/data/2.5/forecast?q={location}&appid={api_key}&units=metric"
    
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            daily_forecast = []
            
            # The API returns 40 blocks of 3-hour intervals. 
            # We will just grab the midday forecast (12:00:00) for each day to keep the JSON clean.
            for item in data['list']:
                if '12:00:00' in item['dt_txt']:
                    daily_forecast.append({
                        "date": item['dt_txt'].split(' ')[0], # Extracts just the YYYY-MM-DD
                        "temperature": item['main']['temp'],
                        "humidity": item['main']['humidity'],
                        "condition": item['weather'][0]['description'].title()
                    })
            
            return daily_forecast
            
        return None
    except Exception as e:
        print(f"Forecast Error: {e}")
        return None