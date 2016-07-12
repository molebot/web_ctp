# encoding: UTF-8
from datetime import datetime
from ws import *
run(host='0.0.0.0', port=9789, server=GeventWebSocketServer)
