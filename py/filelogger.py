# encoding: UTF-8

import logging
import datetime

class tickLogger:
    def __init__(self,InstrumentId):
        _now = datetime.datetime.now()
        str_now = _now.strftime('%Y%m%d')
        _name = 'tick_'+InstrumentId+'_'+str_now
        self.logger = logging.getLogger(_name)
        fh = logging.FileHandler('%s.txt'%_name)
        formatter = logging.Formatter('%(asctime)s # %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
    def get_logger(self):
        return self.logger

class otherLogger:
    def __init__(self):
        _now = datetime.datetime.now()
        str_now = _now.strftime('%Y%m%d')
        _name = 'other_'+str_now
        self.logger = logging.getLogger(_name)
        fh = logging.FileHandler('%s.txt'%_name)
        formatter = logging.Formatter('%(asctime)s # %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
    def get_logger(self):
        return self.logger