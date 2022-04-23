#!/usr/bin/python3
import time
CACHE_EXPIRATION = 3600
KEY="OpenWeatherMapAPI_KEY"
onecall_url = 'https://api.openweathermap.org/data/2.5/onecall?lat=47.498&lon=19.0399&appid=' + KEY
history_today_url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat=47.498&lon=19.0399&dt='+ str(int(time.time()))+ '&appid=' + KEY
history_yesterday_url = 'https://api.openweathermap.org/data/2.5/onecall/timemachine?lat=47.498&lon=19.0399&dt='+ str(int(time.time() - 1*24*60*60))+ '&appid=' + KEY
IRRIGATION_MINIMUM_TEMPERATURE_THRESHOLD_VALUE = 10

