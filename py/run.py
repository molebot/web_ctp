# encoding: UTF-8
from datetime import datetime
_now_ = datetime.now()
_time = _now_.hour*100+_now_.minute

_rules = [(900,1530),(2000,2400)]
if filter(lambda x:x[0]<=_time<=x[1],_rules):
    from ws import *
    run(host='0.0.0.0', port=9789, server=GeventWebSocketServer)
