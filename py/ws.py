# encoding: UTF-8
import json
import time
import shelve
import os
import socket
from bottle import route,get, run, static_file,error,request
from bottle.ext.websocket import GeventWebSocketServer
from bottle.ext.websocket import websocket
from ctpEngine import MainEngine
from string import lowercase as _chars
from string import uppercase as _CHARS
from time import sleep
from eventType import *
from threading import Lock

def platdict(_key,_value,_out,_pos,_tab,_keys):
    if type(_value)==type({}):
        _out.append(_tab*_pos+_key+" => ")
        for k,v in _value.items():
            _out = platdict(k,v,_out,_pos+1,_tab,_keys+[k])
    else:
        if type(_value)==type(''):
            _out.append(u'''%s %s => %s'''%(_tab*_pos,'.'.join(_keys),_value))
        elif  type(_value)==type(u''):
            _out.append(u'''%s %s => %s'''%(_tab*_pos,'.'.join(_keys),_value))
        elif  type(_value)==type(1.0):
            _out.append(u'''%s %s => %.5f'''%(_tab*_pos,'.'.join(_keys),_value))
        elif  type(_value)==type(1):
            _out.append(u'''%s %s => %d'''%(_tab*_pos,'.'.join(_keys),_value))
        elif  type(_value)==type(()):
            _out.append(u'''%s %s => %s %d'''%(_tab*_pos,'.'.join(_keys),_value[0],_value[1]))
        else:
            _out.append(u'''%s %s => %s'''%(_tab*_pos,'.'.join(_keys),str(type(_value))))
    return _out

cs = set()
me = {}
cache = {}
cache['len'] = 100
cache['msg'] = []
STORE = "local_store"

@route('/css/<file_name>')
def get_css(file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'css'))

@route('/ico/favicon.ico')
def get_ico():
    return static_file("ico.ico",root = os.path.join(os.getcwd(),'ico'))

@route('/src/<file_name>')
def get_src(file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'src'))

@route('/src/<a>/<file_name>')
def get_src(a,file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'src',a))

@route('/src/<a>/<b>/<file_name>')
def get_src(a,b,file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'src',a,b))

@route('/src/<a>/<b>/<c>/<file_name>')
def get_src(a,b,c,file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'src',a,b,c))

@route('/src/<a>/<b>/<c>/<d>/<file_name>')
def get_src(a,b,c,d,file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'src',a,b,c,d))

@route('/py/<file_name>')
def get_py(file_name):
    return static_file(file_name,root = os.path.join(os.getcwd(),'py'))

def make_plus(accountid):
    o = ''
    for one in accountid:
        o = o+_chars[int(one)]
    return o

def get_server_ip():
    return socket.gethostbyname_ex(socket.gethostname())[-1]

def get_accounts():
    f = shelve.open(STORE)
    _out = f.get("accounts",{})
    f.close()
    return _out

class Bridge:
    _INSTRUMENT = "Saved_Instrument"
    def __init__(self):
        self.__lock = Lock()
    def set_instrument(self,_dict):
        with self.__lock:
            f = shelve.open(self._INSTRUMENT)
            f['data'] = _dict
            f.close()
    def get_instrument(self):
        with self.__lock:
            f = shelve.open(self._INSTRUMENT)
            _out = f.get('data',{})
            f.close()
            return _out
    def send_ws(self,event):
        try:
            _data = json.dumps(event.dict_,ensure_ascii=False)
            _l = cache['msg']+[_data]
            cache['msg'] = _l[-1*cache['len']:]
            if event.type_ == EVENT_LOG:
                print(event.dict_['log'])
            for _ws in cs:
                _ws.send(_data)
        finally:
            pass

bg = Bridge()
@route('/bridge/set/<a>/<b>/<c>/')
def bridge_set(a,b,c):
    if c not in ['int','str','float']:return 'error type'
    _d = bg.get_instrument()
    _l = a.split('.')
    b = eval(c)(b)
    _tmp = _d
    _out = []
    for one in _l:
        _out.append((one,_tmp))
        if one in _tmp:
            _tmp = _tmp[one]
        else:
            return '%s not in correct place'%one
    _tmp = b
    _n = {}
    for k,d in _out[::-1]:
        d[k] = _tmp
        _tmp = d
    bg.set_instrument(_tmp)
    return str(_tmp)

@route('/bridge/get/<a>/')
def bridge_get(a):
    _d = bg.get_instrument()
    _l = a.split('.')
    return str(reduce(lambda x,y:x.get(y,{}),_l,_d))

def start_accounts(_acc):
    for k,v in _acc.items():
        _plus = make_plus(k)
        me[k] = MainEngine(v, _plus, bg)
        print(u"帐户 [ %s ] 已启动"%k)

def set_accounts(_acc):
    f = shelve.open(STORE)
    _out = {}
    for k,v in _acc.items():
        _out[k] = v
        if '#' in v['instrument']:
            _out[k]['instrument'] = '#'
        else:
            _instrument = v['instrument'].split('+')
            _instrument.sort(reverse=True)
            if '' in _instrument:
                _pos = _instrument.index('')
                _instrument = _instrument[:_pos]
            _list = []
            for one in _instrument:
                if '=' in one:
                    one = filter(lambda x:x in _chars+_CHARS,one)+'='
                    _list.append(one)
                else:
                    _list.append(one)
            _out[k]['instrument'] = '+'.join(_list)
    f['accounts'] = _out
    f.close()
    start_accounts(get_accounts())

print(u'可用地址: '+' '.join(get_server_ip()))
start_accounts(get_accounts())

@get('/top/<n>/')
def get_top(n):
    _all = bg.get_instrument()
    _out = [(v.get('_vol_',0),k) for k,v in _all['instrument'].items()]
    _out.sort(reverse=True)
    _str = '<br/>'.join(map(str,_out[:int(n)]))
    return u'''<!DOCTYPE html><html>
<head></head>
<body>%s</body></html>'''%_str

@get('/all/')
def get_all():
    _all = bg.get_instrument()
    _out = platdict('root',_all,[],0,'...',[])
    _str = '<br/>'.join(_out)
    return u'''<!DOCTYPE html><html>
<head></head>
<body>%s</body></html>'''%_str

@get('/account/getinstrument/')
def account_getinstrument():
    out = []
    for k,one in me.items():
        one.getInstrument(fetch_new=True)
        out.append('account %s getInstrument'%k)
    return '#'.join(out)

@get('/monitor/')
def monitor():
    ips = '|'.join(get_server_ip())
    _t = int(time.time())
    return '''<!DOCTYPE html><html><head><link rel="stylesheet" href="/css/css.css?_=%d" /><link rel="shortcut icon" href="/ico/favicon.ico" type="image/x-icon" /><meta charset="utf-8"><script type="text/javascript" src="/src/brython.js?_=%d"></script><title>CTP监控终端</title></head><body onload="brython()"><script type="text/python" src="/py/monitor.py?_=%d"></script><main role="main" class="grid-container"><div class="grid-100 mobile-grid-100"><section class="example-block"><p><b>行情显示</b></p><div style="margin:10px;" id="marketdata"/><span class="dynamic-px-width"></span></section></div><div class="grid-100 mobile-grid-100"><section class="example-block"><p><b>帐户信息</b></p><div style="margin:10px;" id="account"/><span class="dynamic-px-width"></span></section></div><div class="grid-100 mobile-grid-100"><section class="example-block"><p><b>帐户持仓</b></p><div style="margin:10px;" id="position"/><span class="dynamic-px-width"></span></section></div><hr/><div class="grid-33 mobile-grid-33"><section class="example-block"><p><b>成交</b></p><div style="margin:10px;" id="trade"/><span class="dynamic-px-width"></span></section></div><div class="grid-33 mobile-grid-33"><section class="example-block"><p><b>报单</b></p><div style="margin:10px;" id="order"/><span class="dynamic-px-width"></span></section></div><div class="grid-33 mobile-grid-33"><section class="example-block"><p><b>日志</b></p><div style="margin:10px;" id="log"/><span class="dynamic-px-width"></span></section></div><input type="hidden" id="websocket_ip" value="%s"></main></body></html>'''%(_t,_t,_t,ips)

@get('/settings/')
def settings():
    ips = '|'.join(get_server_ip())
    _t = int(time.time())
    return '''<!DOCTYPE html><html><head><link rel="stylesheet" href="/css/css.css?_=%d" /><link rel="shortcut icon" href="/ico/favicon.ico" type="image/x-icon" /><meta charset="utf-8"><script type="text/javascript" src="/src/brython.js?_=%d"></script><title>CTP帐户管理</title></head><body onload="brython()"><script type="text/python" src="/py/settings.py?_=%d"></script><input type="hidden" id="websocket_ip" value="%s">
    <div id="console">获取帐户信息...请稍候...</div>
    <div id="ctp"></div>
    </body></html>'''%(_t,_t,_t,ips)

@get('/')
def index():
    return '''<!DOCTYPE html><html><head><link rel="stylesheet" href="/css/css.css" /><link rel="shortcut icon" href="/ico/favicon.ico" type="image/x-icon" /><meta charset="utf-8"></script><title>CTP终端</title></head><body><main role="main" class="grid-container"><div class="grid-100 mobile-grid-100"><section class="example-block"><div style="margin:10px;"/>
    <a href="/monitor/" target="_blank">CTP监控界面</a><br/><br/>
    <a href="/settings/" target="_blank">CTP帐户管理</a><br/><br/>
    <a href="/account/getinstrument/" target="_blank">获取合约信息</a><br/><br/>
    <a href="/all/" target="_blank">储存的合约信息</a><br/><br/>
    </section></div></main></body></html>'''

def get_ctp_accounts(act):
    _dict = get_accounts()
    _out = {}
    _out['action'] = EVENT_CTPALL
    _out['data'] = _dict
    _rs = json.dumps(_out)
    for one in cs:
        one.send(_rs)

def update_ctp_accounts(act):
    _accs = act[-1]['data']
    set_accounts(_accs)

def empty_func(act):pass
#    print(act)

funcs = {
    EVENT_EMPTY:empty_func,
    EVENT_CTPUPDATE:update_ctp_accounts,
    EVENT_CTPALL:get_ctp_accounts,
}

@get('/websocket', apply=[websocket])
def echo(ws):
    cs.add(ws)
    print(u'客户端'+str(ws)+u'连接至websocket')
    for _msg in cache['msg']:
        ws.send(_msg)
    while True:
        msg = ws.receive()
        if msg is not None:
            _dict = json.loads(msg)
            _type = _dict.get("action",EVENT_EMPTY)
            if _type in funcs:
                funcs[_type]((msg,_dict))
            else:
                empty_func(msg)
        else: break
    cs.remove(ws)
    print(u'客户端'+str(ws)+u'断开连接')
