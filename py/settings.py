import sys
import time
import json
import datetime
from browser import document, alert, html, websocket, timer, window
from browser.local_storage import storage
sys.path.append("../py")
from eventType import *

cache = {}

if 'ws_server' in storage and storage['ws_server'] in document['websocket_ip'].value:
    ip = storage['ws_server']
else:
    ips = document['websocket_ip'].value.split('|')
    cache['ips'] = ips
    cache['ips_pos'] = 0
    ip = ips[0]


address = 'ws://'+ip+":9789/websocket"
ws = websocket.WebSocket(address)

def reload():
    window.location.reload()

def update_account(accs):
    _dict = {}
    _dict['action'] = EVENT_CTPUPDATE
    _dict['data'] = accs
    _rs = json.dumps(_dict)
    ws.send(_rs)
    timer.set_timeout(reload,1000)

def addnew(ev):
    def check_front(a):
        return a[:4]=="tcp:"
    if check_front(document['mdfront'].value) and check_front(document['tdfront'].value):
        document['console'].clear()
        one = {}
        for _k in ["userid","password","mdfront","tdfront","brokerid",'usezmq','zmqserver','instrument']:
            one[_k] = document[_k].value
        _acc = cache['ctp']
        cache['zmq'] = one['zmqserver']
        _acc[one['userid']] = one
        update_account(_acc)
        document['console'] <= "账号["+one['userid']+"]设置成功"
    else:
        document['console'].clear()
        document['console'] <= "地址错误,请添加tcp://"

def updatectp(ev):
    _acc = cache['ctp']
    _one = _acc[ev.target.id]
    for _k in ['mdfront','tdfront','userid','brokerid','usezmq','zmqserver','instrument']:
        document[_k].value = _one[_k]
    document['new'].set_text("更新账户"+ev.target.id)

def delctp(ev):
    _all = document['ctp'].children
    for one in _all:
        if one.id ==  ev.target.id:
            document['ctp'].remove(one)
    _acc = cache['ctp']
    _acc.pop(ev.target.id)
    update_account(_acc)
    document['console'].clear()
    document['console']<= "账号"+ev.target.id+"已删除"

def get_ctp_all(ev):
    document['console'].clear()
    document['console'] <= "帐户信息获取成功..."
    cache['ctp'] = ev['data']
    if 'zmq' not in cache:
        for one in cache['ctp'].values():
            if 'zmqserver' in one and len(one['zmqserver'])>0:
                cache['zmq'] = one['zmqserver']
                break
    for acc,one in ev['data'].items():
        if one['usezmq']=='0':
            _text = "账号:%(userid)s 行情服务器:%(mdfront)s 交易服务器:%(tdfront)s 柜台ID:%(brokerid)s 订阅合约:%(instrument)s 自动交易服务器:%(zmqserver)s ○不使用"%one
        else:
            _text = "账号:%(userid)s 行情服务器:%(mdfront)s 交易服务器:%(tdfront)s 柜台ID:%(brokerid)s 订阅合约:%(instrument)s 自动交易服务器:%(zmqserver)s ●使用"%one
        _btn1 = html.BUTTON("更新",id=one['userid'])
        _btn1.bind('click',updatectp)
        _btn2 = html.BUTTON("删除",id=one['userid'])
        _btn2.bind('click',delctp)
        _div = html.DIV(id=one['userid'])
        _div <= _btn1+_btn2+_text+html.HR()
        document['ctp'] <= _div

    newer = html.DIV()
    nmd = html.INPUT(id="mdfront")
    nmd.value=""
    newer<= nmd+"行情前置服务器(mdfront)"+html.BR()
    nmd = html.INPUT(id="tdfront")
    nmd.value=""
    newer<= nmd+"交易前置服务器(tdfront)"+html.BR()
    nmd = html.INPUT(id="brokerid")
    nmd.value=""
    newer<= nmd+"柜台ID"+html.BR()
    nmd = html.INPUT(id="userid")
    nmd.value=""
    newer<= nmd+"账号"+html.BR()
    nmd = html.INPUT(id="password")
    nmd.value=""
    newer<= nmd+"密码"+html.BR()
    nmd = html.INPUT(id="instrument")
    nmd.value=""
    newer<= nmd+"订阅合约(多个合约中间用+分隔,使用主力合约加=,如IF=,#代表所有主力合约)"+html.BR()
    nmd = html.INPUT(id="usezmq")
    nmd.value="0"
    newer<= nmd+"使用自动交易信号(0:不使用 1:使用)"+html.BR()
    nmd = html.INPUT(id="zmqserver")
    nmd.value=cache.get('zmqserver','')
    newer<= nmd+"自动交易服务器地址"+html.BR()
    nbtn = html.BUTTON("添加",id="new")
    nbtn.bind('click',addnew)
    newer<= nbtn
    document['ctp'] <= newer

def empty_func(ev):
    pass

funcs = {
    EVENT_EMPTY:empty_func,
    EVENT_CTPALL:get_ctp_all,
}

def ws_open():
    if 'ws_server' not in storage or storage['ws_server'] not in document['websocket_ip'].value:
        storage['ws_server'] = cache['ips'][cache['ips_pos']]
    _dict = {}
    _dict['action'] = EVENT_CTPALL
    ws.send(json.dumps(_dict))

def ws_error():
    if 'ws_server' not in storage or storage['ws_server'] not in document['websocket_ip'].value:
        if cache['ips_pos']+1 <= len(cache['ips']):
            global ws
            cache['ips_pos'] = cache['ips_pos']+1
            ip = cache['ips'][cache['ips_pos']]
            address = 'ws://'+ip+":9789/websocket"
            ws = websocket.WebSocket(address)

def ws_disconnected():
    pass

def ws_msg(event):
    _dict = json.loads(event.data)
    _type = _dict.get("action",EVENT_EMPTY)
    if _type in funcs:
        funcs[_type](_dict)
    else:
        empty_func(_dict)

ws.bind('message',ws_msg)
ws.bind('close',ws_disconnected)
ws.bind('open',ws_open)
ws.bind('error',ws_error)
