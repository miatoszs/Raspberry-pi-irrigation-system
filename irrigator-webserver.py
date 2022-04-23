#!/usr/bin/python3
import time, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse
from urllib.parse import unquote
try:
    has_RPi = True
    import RPi.GPIO as GPIO
except ImportError as e:
    print(ImportError('Cannot import RPi: %s' % str(e)))
    has_RPi = False
import threading
import signal
import os
from owm import OWM
import config
import logger

CONFIG_FILE = 'config.json'

class RequestHandlerClass(BaseHTTPRequestHandler):

    def getConf(self):
        config = {}
        global CONFIG_FILE
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        return(config)

    def write_config(self, config):
        global CONFIG_FILE
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4, sort_keys=True)
        return()

    def parseQueryString(self, querysting):
        keyvalues = {}
        for keyvalue in querysting.split('&'):
            k,v = keyvalue.split('=')

            if not k in keyvalues:
                keyvalues[k] = unquote(v)
            elif type(keyvalues[k]) == "list":
                keyvalues[k].append(unquote(v))
            else:
                tmp = keyvalues[k]
                keyvalues[k] = []
                keyvalues[k].append(tmp)
                keyvalues[k].append(unquote(v))
        return keyvalues

    def read_text_file(self, path):
        if path.startswith('/'):
            path = path[1:]
        with open(path, "r", encoding='utf-8') as f:
            file_content = f.read()
        return(file_content)

    def generate_index_html(self, config):
        htmlcontent = ''
        zonelist = config["zonelist"]
        manual_control_content = ''
        htmlcontent += '<div class="zonelist">'
        for idx, zone in enumerate(zonelist,1):
            htmlcontent += f'<a id="zone_{idx}"><div class="zone">'
            htmlcontent += f'<form action="#zone_{idx}">\n'
            htmlcontent += '<h1>Zone '+ str(idx) +':'+ '</h1>'
            htmlcontent += f'<input name="zonename" value="{zone["name"]}">'
            htmlcontent += '<div id="parentElement">'
            programs = zone["program"]
            for prog_idx, program in enumerate(programs,1):
                starttime = program['start']
                htmlcontent += '<div id="formblockElement" class = "formblockElement">'
                htmlcontent += f'<label for="appt-time">program {prog_idx}:</label>\n'
                htmlcontent += '<input id="appt-time" type="time" name="appt-time" value= '+ starttime +'>'+'\n'
                htmlcontent += f'<br><label for="slider">interval: </label><span id="value">{program["interval"]} min(s)</span>'
                htmlcontent += f'<input name="interval" value="{program["interval"]}" type="range" min="" max="60" id="slider" class="slider"></label><br>'
                htmlcontent += '</div>'
            htmlcontent += '<input type="button" class="button" name="submit" value = "+" onclick=add(this)><input type = "button" class="button" name = "submit" value = "-" onclick=remove(this)>\n'
            htmlcontent += '<input type = "submit" class="okbutton" name = "submit" value = "OK" />\n'
            htmlcontent += '</div>'
            htmlcontent += f'<input name="pin" type="hidden" value="{zone["pin"]}">\n'
            htmlcontent += '</form>\n\n'
            htmlcontent += '</div>'
            checked = ''
            if type(self.server.controller.manual_control_pin) == int and self.server.controller.manual_control_pin == zone['pin']:
                checked = ' checked'
            manual_control_content += f'<input type="radio" id="man_pin_{zone["pin"]}" name="manual_control_pin" value="{zone["pin"]}"{checked}><label for="man_pin_{zone["pin"]}">{zone["name"]}</label> \n'
        htmlcontent += '</div>'
        manual_control_content = '<div id="manualControl" class="manualControl"><a id="manualControl"><h1>Manual program:</h1></a>\n<form action="#manualControl">\n' + manual_control_content

        manual_control_content += '<div>\n'
        if type(self.server.controller.manual_control_pin) == int:
            manual_control_content += f'<input type="submit" class="okbutton" name="manual_control" value="Stop">\n'
        manual_control_content += '<input type="submit" class="okbutton" name="submit" value="Start" />\n</div>\n</form>\n</div>'

        htmlcontent = manual_control_content + htmlcontent
        htmlcontent += f'<div id="logs"></div>'
        ret = f'<html><link rel="stylesheet" href="./style.css"><meta charset="utf-8"><body>\n{htmlcontent}</body><script src="./rangevalue.js"></script><script src="./addelement.js"></script></html>'
        return(ret)

    def extract_multidim_list_elements(self, l):
        ret = []
        for val in l:
            if type(val) == list:
                #newval = self.extract_multidim_list_elements(val)
                #if newval is not None:
                ret.extend(self.extract_multidim_list_elements(val))
            else:
                ret.append(val)
        return(ret)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        config = self.getConf()
        config_write_needed = False
        if parsed_path.query:
            kv_pairs = self.parseQueryString(parsed_path.query)
            if 'interval' in kv_pairs and 'appt-time' in kv_pairs:
                # {"name": "kortefa",   "pin": 5, "program":[{"start": "07:00:00", "interval": 1}]},
                updated_zone = {}
                updated_zone['program'] = []
                updated_zone_id = None
                if type(kv_pairs['interval']) == list:
                    starttimes = self.extract_multidim_list_elements(kv_pairs['appt-time'])
                    intervals = self.extract_multidim_list_elements(kv_pairs['interval'])
                    #print(kv_pairs['appt-time'])
                    #print(kv_pairs['interval'])
                    #print(starttimes)
                    #print(intervals)

                    for i, starttime in enumerate(starttimes):
                        updated_zone['program'].append({'start': starttime, 'interval': int(intervals[i])})
                else:
                    updated_zone['program'].append({'start': kv_pairs['appt-time'], 'interval': int(kv_pairs['interval'])})
                updated_zone['pin'] = int(kv_pairs['pin'])
                for zone_id, zone in enumerate(config['zonelist']):
                    if zone['pin'] == int(kv_pairs['pin']):
                            updated_zone_id = zone_id
                            updated_zone['name'] = kv_pairs['zonename']
                if updated_zone_id is not None:
                    config['zonelist'][updated_zone_id] = updated_zone
                    self.write_config(config)
            elif 'manual_control' in kv_pairs:
                if kv_pairs['manual_control'] == 'Stop':
                    self.server.controller.manual_control_pin = kv_pairs['manual_control']
            elif 'manual_control_pin' in kv_pairs:
                self.server.controller.manual_control_pin = int(kv_pairs['manual_control_pin'])
            elif 'serial' in kv_pairs:
                serial = int(kv_pairs['serial'])

        if (parsed_path.path == '/' or parsed_path.path == '/index.html'):
            message = self.generate_index_html(config)
            self.send_response(200)
            self.send_header('Content-type','text/html')
        elif (parsed_path.path == '/status.json'):
            message = json.dumps(self.server.controller.zone_states, indent=4)
            self.send_response(200)
            self.send_header('Content-type','application/json')
        elif (parsed_path.path == '/program.json'):
            message = json.dumps(self.server.controller.program, indent=4)
            self.send_response(200)
            self.send_header('Content-type','application/json')
        elif (parsed_path.path == '/logs.json'):
            if 'serial' not in locals(): serial = 0
            message = json.dumps(log.get_logs_after_serial(serial), indent=4)
            self.send_response(200)
            self.send_header('Content-type','application/json')
        elif (parsed_path.path.endswith('.css') or parsed_path.path.endswith('.js') or parsed_path.path.endswith('.html')):
            self.send_response(200)
            if parsed_path.path.endswith('.js'):
                self.send_header('Content-type','application/javascript')
            elif parsed_path.path.endswith('.css'):
                self.send_header('Content-type','text/css')
            else:
                self.send_header('Content-type','text/html')
            message = self.read_text_file(parsed_path.path)
        else:
            self.send_response(200)
            message = '\n'.join([
                'CLIENT VALUES:',
                'client_address=%s (%s)' % (self.client_address,
                    self.address_string()),
                'command=%s' % self.command,
                'path=%s' % unquote(self.path),
                'real path=%s' % parsed_path.path,
                'query=%s' % unquote(parsed_path.query),
                'request_version=%s' % self.request_version,
                '',
                'SERVER VALUES:',
                'server_version=%s' % self.server_version,
                'sys_version=%s' % self.sys_version,
                'protocol_version=%s' % self.protocol_version,
                '',
                ])

        self.end_headers()
        self.wfile.write(bytes(message, "utf8"))
        #if parsed_path.query:
        #    self.wfile.write(bytes(json.dumps(self.parseQueryString(parsed_path.query)), "utf8"))
        #self.wfile.write(bytes(str(self.server.controller.zone_states), "utf8"))
        return

    def do_POST(self):
        content_len = int(self.headers.getheader('content-length'))
        post_body = self.rfile.read(content_len)
        self.send_response(200)
        self.end_headers()

        data = json.loads(post_body)

        self.wfile.write(data['foo'])
        return


class HTTPServerClass(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        HTTPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self._running = True
        self._lock = threading.Lock()
        self.control_request = {}

    def htmlimport(self, htmlnev):
        """
        subiduuuu
        :param htmlnev:
        :return:
        """
        filehandler = open(htmlnev, 'r', encoding='UTF-8')  # r=read
        tartalom = filehandler.read()
        return (tartalom)

    def bin_file_import(self, htmlnev):
        """
        subiduuuu
        :param htmlnev:
        :return:
        """
        filehandler = open(htmlnev, 'rb')  # r=read b=binary/byte
        tartalom = filehandler.read()
        return (tartalom)

    def process_request(self, request, client_address):
        thread = threading.Thread(target=self.__new_request, args=(self.RequestHandlerClass, request, client_address, self))
        thread.start()

    def __new_request(self, handlerClass, request, address, server):
        handlerClass(request, address, server)
        self.shutdown_request(request)

    def set_control_request(self, data):
        with self._lock:
            self.control_request = data

    def get_control_request(self):
        with self._lock:
            data = self.control_request.copy()
            self.control_request = {}
        return(data)




class WebServerClass(threading.Thread):
    def __init__(self, name='web-server'):
        self._running = True
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        super(WebServerClass, self).__init__(name=name)

        self._name = name
        log.log(logger.INFO, self._name, ': Starting http server')
        self.httpd = HTTPServerClass(('', 8080), RequestHandlerClass)
        self.httpd.timeout = 3
        self.start()

    def signal_handler(self, sig, frame):
        log.log(logger.INFO, self._name, ': Received CTRL-BREAK, stopping...' )
        self.stop()

    def stop(self):
        self.httpd._running = False
        self._running = False

        log.log(logger.INFO, self._name, ': http stop signaled')

    def run(self):
        while self._running:
            self.httpd.handle_request() # is blocking, unless timeout set
        log.log(logger.INFO, self._name, 'joining http')




class ControllerClass():

    def __init__(self):
        # A raspberry PI fizikai pin sorszam hivatkozast allitjuk be
        if has_RPi:
            # log.log(logger.INFO, type(RPi.RPi), str(RPi.RPi))
            GPIO.setmode(GPIO.BOARD)
        self.last_read_timestamp = 0
        self.zone_states = []
        self.pin_to_zone_map = {}
        self.config = {}
        self.program = None
        self.read_config()
        self.set_zone_pins_to_default_state()
        self.manual_control_pin = None
        self.manual_pin_states = {}
        self.owm = OWM()

    def configtime_to_unix_timestamp(self, starttime):
        '''
        Unix timestampre atalakitja a bemeno parameterben megadott oo:pp:mm idot
        oly modon, hogy kiegesziti az aktualis datum napjaval
        '''
        t = 0
        multiplier = 3600
        starttime_splitted = starttime.split(':')
        for i in starttime_splitted:
            t += int(i) * multiplier
            multiplier /= 60
        return(int(t))

    def iso_timestamp(self):
        # ISO formatumu timestamp string letrehozasa
        return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def timestamp_to_hms(self, t):
        timeofday = ''
        hour = int(t / 3600)
        minutes = int(t % 3600 / 60)
        sec = t % 60
        timeofday = f'{hour:02d}:{minutes:02d}'
        if sec > 0:
            timeofday += f':{sec:02d}'
        return(timeofday)

    def get_seconds_of_day(self):
        # aktualis ido kiszamitasa masodpercben
        now = datetime.datetime.now()
        t = now.hour*3600 + now.minute * 60 + now.second
        return(t)

    def on_off_state(self, t, start, stop):
        # Eldonti, hogy benne vagyunk-e az ontozesi program intervallumban
        if t >= start and t < stop:
            return(True)
        else:
            return(False)

    def read_config(self):
        '''
        Beolvassa a CONFIG_FILE fileban talalhato json formatumu config filet,
        extra funkcioja, hogy csak akkor olvassa be ha konfig file os mtime attributuma ujabb,
        mint a legutolso alkalommal volt

        config:
        {'interval_multiplier': 1, 'suspend': False,
            'zonelist': [{'name': 'csopi', 'pin': 3, 'program': [{'interval': 5, 'start': '08:01'}]},
                        {'name': 'kortefa', 'pin': 5, 'program': [{'interval': 4, 'start': '08:00'}]},
                        {'name': 'trambulin', 'pin': 7, 'program': [{'interval': 3, 'start': '08:05'}, {'interval': 2, 'start': '19:15'}]}]}
        '''
        # itt ellenorizzuk a legutolso alkalommal elmentett mtime erteket a mostanival
        if self.last_read_timestamp == int(os.path.getmtime(CONFIG_FILE)):
            return(self.config, self.program)
        if self.last_read_timestamp == 0:
            log.log(logger.INFO, "Reading config")
        else:
            log.log(logger.INFO, "Rereading config")
        self.last_read_timestamp = int(os.path.getmtime(CONFIG_FILE))

        with open(CONFIG_FILE) as f:
            # config valtozo tartalmazza a json file tartalmat
            self.config = json.load(f)
        #log.log(logger.INFO, config)
        for idx, zona in enumerate(self.config['zonelist']):
            if has_RPi:
                GPIO.setup(zona['pin'], GPIO.OUT)
            self.pin_to_zone_map[zona['pin']] = idx
        # ha valtozik a zona-k szama, a zone_states-t ujra kell inicializalni
        if len(self.zone_states) != len(self.config['zonelist']):
            self.zone_states = [False] * len(self.config['zonelist'])

        self.program = self.create_program_from_config(self.config)
        return()

    def create_program_from_config(self, config):
        '''
        program dict valtozoba kigyujtjuk a config program alapjan az elemeket,
        mikozben a start kulcs ertekeket atalakitjuk unix timestampre, az atfedo startokat eltoljuk a korabbi program vegere
        input: read_config json formatum
        output:
        program:
        {   0: {'start': 1646463600, 'start_orig': '08:00', 'stop': 1646463840, 'interval': 240, 'name': 'kortefa', 'pin': 5, 'running': False},
            1: {'start': 1646463840, 'start_orig': '08:04:00', 'stop': 1646464140, 'interval': 300, 'name': 'csopi', 'pin': 3, 'running': False, 'tampered': True},
            2: {'start': 1646464140, 'start_orig': '08:09:00', 'stop': 1646464320, 'interval': 180, 'name': 'trambulin', 'pin': 7, 'running': False, 'tampered': True},
            3: {'start': 1646504100, 'start_orig': '19:15', 'stop': 1646504220, 'interval': 120, 'name': 'trambulin', 'pin': 7, 'running': False}}

        '''

        # ideiglenes dict letesitese, sorszam kulcssal
        tmp = {}
        index = 0
        for zona in config['zonelist']:
            for zona_program in zona['program']:
                #  a programban tarolt oo:pp:mm atalakitasa unix timestampre sajat fugvennyel
                start_unixtime = self.configtime_to_unix_timestamp(zona_program['start'])
                tmp[index] = {}
                tmp[index]['start']  = start_unixtime
                tmp[index]['start_orig'] = zona_program['start']
                tmp[index]['stop'] = int(start_unixtime + zona_program['interval'] * config['interval_multiplier']* 60)
                tmp[index]['interval'] = zona_program['interval']
                tmp[index]['name'] = zona['name']
                tmp[index]['pin'] = zona['pin']
                index += 1
        last_stop = 0
        program = {}
        # a tmp program elemek start idopont szerinti rendezese
        # start ertekeinek ellenorzese, atfedes eseten csusztatas az elozo program vegere
        index = 0
        for _,v in sorted(tmp.items(), key=lambda x: x[1]['start']):
            program[index] = v.copy()
            program[index]['running'] = False
            program[index]['interval'] = v['interval'] * config['interval_multiplier']* 60
            if v['start'] <= last_stop:
                program[index]['start'] = last_stop
                program[index]['start_orig'] = self.timestamp_to_hms(last_stop)
                #del (program[index]['start_orig'])
                program[index]['tampered'] = True
                program[index]['stop'] = int(last_stop + v['interval'] * config['interval_multiplier']* 60)
            last_stop = program[index]['stop']
            index += 1

        for k,v in program.items():
            #log.log(logger.INFO, 'prog:', k, v)
            log.log(logger.INFO, k, v)
            pass
        return(program)


    def set_zone_pins_to_default_state(self):
        for zone in self.config['zonelist']:
            log.log(logger.INFO, zone['pin'], 'pin kikapcsolasa')
            if has_RPi:
                GPIO.output(zone['pin'], GPIO.HIGH)

    def manual_run(self):
        if self.manual_control_pin is not None:
            for pin in self.manual_pin_states:
                if pin != self.manual_control_pin:
                    if has_RPi:
                        GPIO.output(pin , GPIO.HIGH)
                    self.zone_states[self.pin_to_zone_map[pin]] = False
                    log.log(logger.INFO, 'pin:', pin,  'kikapcsol')
            if self.manual_control_pin == 'Stop':
                self.manual_control_pin = None
            elif self.manual_control_pin not in self.manual_pin_states:
                self.manual_pin_states = {}
                self.manual_pin_states[self.manual_control_pin] = True
                if has_RPi:
                    GPIO.output(self.manual_control_pin , GPIO.LOW)
                self.zone_states[self.pin_to_zone_map[self.manual_control_pin]] = True
                log.log(logger.INFO, 'pin:', self.manual_control_pin,  'bekapcsol')
            time.sleep(1)
            return(True)
        return(False)


    def run(self):
        self.read_config()
        program = self.program
        if self.config['suspend'] == True or program == None:
            log.log(logger.INFO, self.config, '\n', program)
            time.sleep(1)
            return

        if self.manual_run():
            return()

        #aktualis futasi timestamp eltarolasa
        t = self.get_seconds_of_day()
        # a program idopontok szerinti rendezese es az elemek iteracioja
        for k in sorted(program):
            #Open Weather Monitoring lekerdezese, kell-e is ha igen mennyit locsolkodni
            # debug
            #print(k, program[k])
            # itt szuletik meg a zona pin statusa az aktualis illetve a programban tarolt start es interval alapjan
            status = self.on_off_state(t, program[k]['start'], program[k]['stop'])
            # ha aktiv a program megnezzuk owm alapjan kell-e locsolni
            if status and not self.owm.is_watering_needed(debug=False):
                log.log(logger.INFO, 'OWM alapjan az ontozes elmarad, prog:', k, program[k])
                time.sleep(program[k]['stop'] - t)
                break;
            # comment kozos reszenek elokeszitese
            comment = str(k) +  '. program, "' + program[k]['name'] + '" zona, pin:#'+str(program[k]['pin'])
            # a GPIO pineket csak akkor csesztetjuk, ha szukseges es az adott program fut, vagy epp er veget
            if status and not program[k]['running']:
                program[k]['running'] = True
                if has_RPi:
                    GPIO.output(program[k]['pin'], GPIO.LOW)
                self.zone_states[self.pin_to_zone_map[program[k]['pin']]] = True
                log.log(logger.INFO, comment, 'bekapcsol')
            elif not status and program[k]['running']:
                if has_RPi:
                    GPIO.output(program[k]['pin'], GPIO.HIGH)
                self.zone_states[self.pin_to_zone_map[program[k]['pin']]] = False
                program[k]['running'] = False
                log.log(logger.INFO, comment, 'kikapcsol')

            if status and (program[k]['stop'] - t) % 60 == 0:
                log.log(logger.INFO, comment, 'aktiv, lekapcsolas: ', program[k]['stop'] - t % 86400, 's mulva')
        time.sleep(1)

    def stop(self):
        # Takaritas, alapallapotba allitas
        self.set_zone_pins_to_default_state()
        if has_RPi:
            GPIO.cleanup()


def main():
    server = WebServerClass()
    controller = ControllerClass()
    server.httpd.controller = controller

    while server._running:
        control_req = server.httpd.get_control_request()
        controller.run()
    controller.stop()
    server.stop()
    log.log(logger.INFO, __name__, 'server stop signaled')
    server.join()
    log.log(logger.INFO, __name__, 'server joined')


if __name__ == '__main__':
    log = logger.FifoLogger()
    main()
