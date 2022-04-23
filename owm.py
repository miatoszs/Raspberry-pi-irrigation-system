#!/usr/bin/python3
import time, datetime
import json
import requests
import os.path
import config
import traceback

class OWM(object):

    def unixtime2iso(self, t):
        return (datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S"))

    def is_unixtime_today(self, t):
        t_to_date = datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d")
        now_to_date = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d")
        if t_to_date == now_to_date:
            return(True)
        else:
            return(False)

    def is_unixtime_yesterday(self, t):
        t_to_date = datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d")
        yesterday_to_date = datetime.datetime.fromtimestamp(time.time() - 86400).strftime("%Y-%m-%d")
        if t_to_date == yesterday_to_date:
            return(True)
        else:
            return(False)


    def retrieve_url(self, url, cachefile):
        if cachefile and os.path.isfile(cachefile) and time.time() - os.path.getmtime(cachefile) < config.CACHE_EXPIRATION:
            #print('Loading cached file:', cachefile)
            f = open(cachefile, 'r')
            js = json.load(fp=f)
            f.close()
            return(js)

        # print('Retrieving url :', url)
        try:
            r = requests.get(url)
            js = json.loads(r.content.decode("UTF-8"))
        except requests.exceptions.ConnectionError as e:
            print(traceback.format_exc())
            js = {}
            js['hourly'] = []
        if cachefile:
            f = open(cachefile, 'w')
            json.dump(js, fp=f, indent=4)
            f.close()
        #print('cache:', cachefile)
        #self.print_data(js)
        return(js)


    def get_history_js(self):
        js = {}
        js['hourly'] = []
        js_temp = self.retrieve_url(config.history_yesterday_url, '.history_yesterday.js')
        if 'hourly' in js_temp:
            for hour in js_temp['hourly']:
                    js['hourly'].append(hour)
        js_temp = self.retrieve_url(config.history_today_url, '.history_today.js')
        if 'hourly' in js_temp:
            for hour in js_temp['hourly']:
                    js['hourly'].append(hour)
        return(js)

    def get_last_n_hours_js(self, n=24):
        js_temp = self.get_history_js()
        js = {}
        js['hourly'] = []
        js['hourly'] = js_temp['hourly'][-n:]
        return(js)

    def get_today_so_far_js(self):
        jstemp = self.get_history_js()
        js = {}
        js['hourly'] = []
        for hour in js_temp['hourly']:
            if self.is_unixtime_today(hour['dt']):
                js['hourly'].append(hour)
        return(js)

    def get_yesterday_js(self):
        jstemp = self.get_history_js()
        js = {}
        js['hourly'] = []
        for hour in js_temp['hourly']:
            if self.is_unixtime_yesterday(hour['dt']):
                js['hourly'].append(hour)
        return(js)

    def get_next_n_hours_js(self, n=48):
        js_ret = self.retrieve_url(config.onecall_url, '.onecall_next_48h.js')
        if n >= 48:
            return(js_ret)
        js = {}
        js['hourly'] = []
        if 'hourly' in js_ret:
            for idx, hour in enumerate(js_ret['hourly'],1 ):
                if idx <= n:
                    js['hourly'].append(hour)
                else:
                    break
        return(js)

    def get_next_24h_js(self):
        return(self.get_next_n_hours_js(24))

    def get_today_forecast_js(self):
        js_temp  = self.get_next_n_hours_js(24)
        js = {}
        js['hourly'] = []
        for hour in js_temp['hourly']:
            if self.is_unixtime_today(hour['dt']):
                js['hourly'].append(hour)
            else:
                break
        return(js)


    def K2C(self, kelvin):
        celsius = kelvin - 272.15
        return(celsius)

    def is_watering_needed_based_on_yesterday_rainfall(self):
        '''
        {'dt': 1641301200, 'temp': 284.27, 'feels_like': 283.4, 'pressure': 1004, 'humidity': 75, 'dew_point': 280.01, 'uvi': 0.19, 'clouds': 90, 'visibility': 10000, 'wind_speed': 1.34
        , 'wind_deg': 220, 'wind_gust': 3.13, 'weather': [{'id': 500, 'main': 'Rain', 'description': 'light rain', 'icon': '10d'}]}
        '''
        js = self.get_last_n_hours_js(24)
        rainfall = False
        # if owm is unavailable return True
        if len(js['hourly']) == 0:
            return(True)
        for hour in js['hourly']:
            for i in hour['weather']:
                if i['main']=='Rain':
                    #print(hour['dt'], h)
                    rainfall = True
        return(not rainfall)

    def get_rainfall_volume(self, n):
        '''
        {'dt': 1641301200, 'temp': 284.27, 'feels_like': 283.4, 'pressure': 1004, 'humidity': 75, 'dew_point': 280.01, 'uvi': 0.19, 'clouds': 90, 'visibility': 10000, 'wind_speed': 1.34
        , 'wind_deg': 220, 'wind_gust': 3.13, 'weather': [{'id': 500, 'main': 'Rain', 'description': 'light rain', 'icon': '10d'}]},
        {"dt": 1645448400, "temp": 280.17, "feels_like": 276.36, "pressure": 1005, "humidity": 88, "dew_point": 278.32, "uvi": 0.32, "clouds": 100, "visibility": 5000, "wind_speed": 6.71, "wind_deg": 283, "wind_gust": 12.96, "weather": [ { "id": 501, "main": "Rain", "description": "moderate rain", "icon": "10d" } ], "rain": { "1h": 1 } }
        '''
        if n < 0:
            js = self.get_last_n_hours_js(abs(n))
        else:
            js = self.get_next_n_hours_js(n)
        rain_volume = 0
        for hour in js['hourly']:
            if 'rain' in hour:
                rain_volume += float(hour['rain']['1h'])
        return(rain_volume)


    def is_watering_needed_based_on_temperatue_forecast(self):
        '''Don't water when today's forecast max temperature is less than minimum threshold value
        inputs: oncall.js
        outputs: True, or False
        '''
        js = self.get_next_n_hours_js(24)
        irrigate = False
        if len(js['hourly']) == 0:
            return(True)
        for hour in js['hourly']:
            # print(counter, f"{self.K2C(hour['temp']):02.1f}")
            if self.K2C(hour['temp']) > config.IRRIGATION_MINIMUM_TEMPERATURE_THRESHOLD_VALUE:
                irrigate = True
                break
        return(irrigate)

    def print_data(self, js):
        for h in js['hourly']:
            if 'rain' in h:
                print(h['dt'], self.unixtime2iso(h['dt']), f"{self.K2C(h['temp']):02.1f}", h['weather'][0]['main'], h['rain'])
            else:
                print(h['dt'], self.unixtime2iso(h['dt']), f"{self.K2C(h['temp']):02.1f}", h['weather'][0]['main'] )

    def is_watering_needed(self, debug=False):
        if debug:
            print('last 48 hours:')
            js = self.get_last_n_hours_js(48)
            self.print_data(js)
            print('next 48 hours:')
            js = self.get_next_n_hours_js(48)
            self.print_data(js)

            print('get_rainfall_volume for last 24 hours:', self.get_rainfall_volume(-24), 'mm')
            print('get_rainfall_volume forecast for next 12 hours:', self.get_rainfall_volume(12), 'mm')
            print('is_watering_needed_based_on_yesterday_rainfall:', self.is_watering_needed_based_on_yesterday_rainfall())
            print('is_watering_needed_based_on_temperatue_forecast:', self.is_watering_needed_based_on_temperatue_forecast())

        needed_based_on_yesterday_rainfall = self.is_watering_needed_based_on_yesterday_rainfall()
        rainfall_volume_yesterday = self.get_rainfall_volume(-24)
        rainfall_volume_forecast_24h = self.get_rainfall_volume(12)
        needed_based_on_temperature_forecast = self.is_watering_needed_based_on_temperatue_forecast()
        if not needed_based_on_yesterday_rainfall:
            return False
        if rainfall_volume_yesterday >= 3:
            return False
        if rainfall_volume_forecast_24h >= 3:
            return False
        if not needed_based_on_temperature_forecast:
            return False
        return(True)

if __name__ == '__main__':
    owm = OWM()
    print('is_watering_needed:', owm.is_watering_needed(debug=True))
