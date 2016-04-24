#coding:utf-8
from base import *
from log import *
import time
import zmq
import json
import requests
from cmath import log as mathclog
from life import price2point
def mathlog(a):return mathclog(a).real

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:9999")

time.sleep(1)
logit("begin loop")

def get_result(_msg):
    try:
        _symbol = _msg.get("symbol","test")
        _exchange = _msg.get("exchange","test")
        _money = _msg.get("eq","1.0")
        _price = _msg.get("price",1.0)
        _point = price2point(_price,_msg['point'],mathlog)
        b = Base(_exchange,_symbol,conn,allstate)
        b.account_money(float(_money))
        b.new_price(time.time(),_point,_price)
        return '0'#str(b.get_result()['result'])
    except Exception,e:
        logit("zmq_error")
        logit(str(e.message))
        return "0"*20

def nothing(_msg):pass

Funcs = {
"result":get_result,
}

while True:
    try:
        _dict = json.loads(socket.recv())
        _func = Funcs.get(_dict.get("act","none"),nothing)
        bk = _func(_dict)
    except Exception,e:
        logit("zmq_error:"+str(e.message))
        bk = "0"*20
    finally:
        socket.send(bytes(bk))
