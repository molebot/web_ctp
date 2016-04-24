#coding:utf-8
from bottle import route,run,debug,request,redirect,response,error,static_file
import bottle,os
from cmath import log as mathclog
import time,sys,datetime,random,acc
from base import *
from life import *
from svgcandle import *
from mongo_log_handlers import MongoHandler
from settings import mongo_server
from qqmail import *
from log import *
import thread

def now():return datetime.datetime.now()
def mathlog(a):return mathclog(a).real

cache = {}
cache['pass'] = time.time()+3600*24*7

def logten():
    ip = request['REMOTE_ADDR']
    day= datetime.datetime.now().strftime("_%Y_%m_%d_%H")
    url = request.environ['PATH_INFO']+day
    if 'url' not in cache:
        cache['url'] = {}
    if ip+url not in cache['url']:
        cache['url'][ip+url]=0
        if len(cache['url'])>200:
            cache['url']={}
            logit('clear cache url')
        if 'Mozilla/4.0' in request.environ.get('HTTP_USER_AGENT','no agent'):
            pass
        else:
            logit('''url @ %s [ <a href="http://www.baidu.com/s?wd=%s&_=%.0f" target="_blank">%s</a> ] %.1f
                <span style="color:gray">%s</span>'''%(url,ip,time.time()/10,ip,cache['pass']-time.time(),request.environ.get('HTTP_USER_AGENT','no agent')))
    return True

@error(500)
def error500(error):
    try:
        logger.error(error.traceback)
    finally:
        return ''

@error(404)
def error404(error):
    logten()
    return ''

@route('/logs/')
def show_logs():
    logten()
    _list = MongoHandler().show()
    _dt = datetime.timedelta(hours=8)
    if _list:
        out = ''.join([ '<pre>%s >>> %s</pre>'%((_dt+one['timestamp'].as_datetime()).strftime("%Y-%m-%d %H:%M:%S"),one['message']) for one in _list])
        return '''<html><head><title>%s</title><META HTTP-EQUIV="REFRESH" CONTENT="10"></head><body>
                %s</body></html>'''%((_dt+_list[0]['timestamp'].as_datetime()).strftime("%H:%M:%S"),out)
    else:
        return '''<html><head><META HTTP-EQUIV="REFRESH" CONTENT="100"></head><body>
                <br/></body></html>'''

@route('/')
def index():
    logten()
    global cache
    _all = conn.database_names()
    _list = filter(lambda x:'_' in x and x[0]=='k',_all)
    _raw = filter(lambda x:'_' in x and x[:3]=='raw',_all)
    out = []
    len = request.query.l or cache.get('len','100')
    cache['len'] = len
    for one in [10,50,100,200]:
        out.append('<a href="/?l=%d">%d</a>'%(one,one))
    out.append("<br/>")
    out.append("<br/>")
    for one in _list:
        out.append('<a href="/list/%s/" target="_blank">%s</a>'%(one,one))
        out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    for one in _raw:
        out.append(u'<a href="/delete/%s/" target="_blank">删除 %s 原始tick数据!!!</a>'%(one,one))
        out.append("<br/>")
    all = '&nbsp;'.join(out)
    return '''<html><head></head><body><br/>%s</body></html>'''%all

@route('/delete/:symbol/')
def del_symbol(symbol):
    conn.drop_database(symbol)
    return 'ok'

@route('/list/:symbol/')
def get_symbol(symbol):
    logten()
    len = request.query.l or cache.get('len','100')
    cache['len'] = len
    _k,_exchange,_symbol,_plus = symbol.split('_')
    b=Base(_exchange,_symbol,conn,allstate,plus=_plus)
    s=SVG('',[],'')
    _all = s.get_lines()
    _tf = b.get_timeframe()
    out = []
    out.append(_exchange)
    out.append(_symbol)
    out.append(_plus)
    out.append("<br/>")
    for one in _all:
        for tf in _tf:
            out.append('<a href="/image/%s/%s/%s/" target="_blank">%s[%s]</a>'%(symbol,one,tf,tf,one))
        out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append("<br/>")
    out.append(u'<a href="/delete/%s/" target="_blank">删除 %s !!!</a>'%(symbol,symbol))
    out.append("<br/>")
    out.append("<br/>")
    _ticks = b.raw_tick()
    for one in _ticks:
        out.append(str(one))
        out.append("<br/>")
    out.append("<br/>")
    all = '&nbsp;'.join(out)
    return '''<html><head></head><body><br/>%s</body></html>'''%all

@route('/time/')
def get_time():
    _day = datetime.datetime.now()
    _time = _day.hour*100+_day.minute
    return str(_time)

@route('/tick/:account/:eq/:price/:symbol/:exchange/:point/:ratio/result/')
def get_result(account,eq,price,symbol,exchange,point,ratio):
    if not price.replace('.','').isdigit():
        logit("Error_Price,%s"%price)
        return '0'
    _account = account
    _money = float(eq)
    _price = float(price)
    _point = price2point(_price,int(point),mathlog)
    _symbol = symbol
    _exchange = "ctp"
    _begin = time.time()
    if _begin - cache.get(('time',_exchange,_symbol),0)>0.5:
        b = Base(_exchange,_symbol,conn,allstate)
        b.account_money(_money)
        b.new_price(time.time(),_point,_price)
        _result = b.get_result()
        logit(str(_result))
        logit(str(time.time()-_begin))
        cache[('time',_exchange,_symbol)] = time.time()
        cache[('rslt',_exchange,_symbol)] = _result
        return '0'
        return str(b.get_result().get('result',0))
    else:
        return '0'
        return cache.get(('rslt',_exchange,_symbol),{}).get('result',0)


@route('/image/:symbol/:group/:tf/')
def get_image(symbol,group,tf):
    logten()
    len = request.query.l or cache.get('len','100')
    o = request.query.p or '0'
    cache['len'] = len
    _k,_exchange,_symbol,_plus = symbol.split('_')
    if _plus:
        b=Base(_exchange,_symbol,conn,allstate,plus=_plus)
    else:
        b=Base(_exchange,_symbol,conn,allstate)
    out = []
    out.append(_exchange)
    out.append(_symbol)
    out.append(_plus)
    out.append(group)
    out.append("<br/>")
    _svg = b.get_image(tf,len,group,offset=int(o))
    _page = ''.join(['''<a href="/image/%s/%s/%s/?p=%d">-%d-</a>'''%(symbol,group,tf,i,i) for i in range(11)])
    out.append(_svg)
    out.append("<br/>")
    out.append(_page)
    all = '&nbsp;'.join(out)
    return '''<!DOCTYPE html><head><META HTTP-EQUIV="REFRESH" CONTENT="10"></head><body><br/>%s</body></html>'''%all

