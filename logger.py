import logging
import datetime
import threading


ERROR   = 1
WARNING = 2
INFO    = 3
DEBUG   = 4

MAX_LOG_ENTRIES = 1000

class FifoLogger():
    def __init__(self):
        self.logentries = []
        self.serial = 0
        self._lock = threading.Lock()

    def log(self, loglevel, *args):
        with self._lock:
            self.serial += 1
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            msg = ' '.join([str(x) for x in args])
            self.logentries.append([self.serial, timestamp, loglevel, msg])
            print(timestamp, msg)

            while len(self.logentries) > MAX_LOG_ENTRIES:
                self.logentries.pop(0)

        if loglevel == ERROR:
            logging.error(msg)
        if loglevel == WARNING:
            logging.warning(msg)
        if loglevel == INFO:
            logging.info(msg)
        if loglevel == DEBUG:
            logging.debug(msg)
        return

    def get_last_n_logs(self, n=10):
        with self._lock:
            return self.logentries[-n:]

    def get_logs_after_serial(self, serial=0):
        with self._lock:
            if serial>len(self.logentries):
                return []
            n = 1
            while True:
                if self.logentries[-n][0] <= serial:
                    break
                n += 1
                if n >= len(self.logentries):
                    break
            ret = self.logentries[-n:]
        return ret



if __name__ == '__main__':
    logger = FifoLogger()

    for i in range(100):
        logger.log(INFO, 'ize', 'bigyo', [1]*5)


