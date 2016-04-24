import sys
import time
import json
import datetime
from browser import document, alert, html, websocket, timer, window
from browser.local_storage import storage

EVENT_TIMER = '_eTimer'                  # 计时器事件，每隔1秒发送一次
EVENT_LOG = 'eLog'                      # 日志事件，通常使用某个监听函数直接显示

EVENT_TDLOGIN = '_eTdLogin'                  # 交易服务器登录成功事件
EVENT_MDLOGIN = '_eMdLogin'                  # 交易服务器登录成功事件

EVENT_TICK_CLEAR = 'eTickClear'
EVENT_TICK = 'eTick'                        # 行情推送事件
EVENT_TICK_JUST = 'eTick.'                        # 行情推送事件

EVENT_TRADE = 'eTrade'                      # 成交推送事件
EVENT_TRADE_JUST = 'eTrade.'                      # 成交推送事件

EVENT_ERROR = '_eError'                      # Error推送事件

EVENT_ORDER = 'eOrder'                      # 报单推送事件
EVENT_ORDER_JUST = 'eOrder.'                      # 报单推送事件

EVENT_POSITION = '_ePosition'                # 持仓查询回报事件
EVENT_POSIALL = 'ePosiAll'                # 持仓汇总

EVENT_INSTRUMENT = '_eInstrument'            # 合约查询回报事件
EVENT_PRODUCT = 'eProduct'                      # 合约品类更新
EVENT_INSTRUMENT_DETAIL = 'eInstrumentDetail'  # 合约查询
EVENT_INVESTOR = 'eInvestor'                # 投资者查询回报事件
EVENT_ACCOUNT = 'eAccount'                  # 账户查询回报事件

EVENT_CTPALL = 'eCtpAll'
EVENT_EMPTY = 'eNone'
EVENT_CTPUPDATE = 'eCtpUpdate'


count = 100
cache = {}

def width_label(c,width):
    if type(c)==type(.1):
        c = '%.2f'%c
    s= html.LABEL(c)
    s.style={"display":"inline-block","width":"%dpx"%width}
    return s

def add_log(content):
    _doc = document['log']
    _id = "log{}".format(time.time())
    _content = html.LABEL(str(datetime.datetime.now())[11:22]+" "+content)
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    _l = _doc.children
    _doc.clear()
    _l=[some]+_l
    for one in _l[:count]:
        _doc<=one

add_log("界面启动")

if 'ws_server' in storage and storage['ws_server'] in document['websocket_ip'].value:
    ip = storage['ws_server']
    add_log('连接至预存的'+storage['ws_server'])
else:
    ips = document['websocket_ip'].value.split('|')
    cache['ips'] = ips
    cache['ips_pos'] = 0
    ip = ips[0]

address = 'ws://'+ip+":9789/websocket"
ws = websocket.WebSocket(address)

def event_log(_msg):
    add_log('['+_msg['_account_']+'] '+_msg['log'])

def event_product(_msg):
    _doc = document['marketdata']
    _dict = _msg['data']
    storage['product_list'] = json.dumps(_dict.keys())
    add_log(str(_dict))

DirectionDict = {"0":"买","1":"卖"}
DirectionStyle = {"0":{"color":"red"},"1":{"color":"green"},"2":{"color":"red"},"3":{"color":"green"}}
OffsetFlagDict = {"0":"开仓","1":"平仓","2":"强平","3":"平今仓","4":"平昨仓","5":"强减","6":"本地强平"}
Orders = []

def event_order(_msg):
    global Orders
    _doc = document['order']
    _dict = _msg['data']
    _id = "order_{}_{}".format(_msg['_account_'],_dict['OrderRef'])
    _str = str(datetime.datetime.now())[11:19]+" [ {} ] {} 报{}价:{} {} 手数:{} {}".format(_msg['_account_'],_dict['InstrumentID'],DirectionDict.get(_dict['Direction'],"未知方向"),'%.2f'%float(_dict['LimitPrice']),OffsetFlagDict.get(_dict['CombOffsetFlag'],"未知开平"),_dict['VolumeTotalOriginal'],_dict['StatusMsg'])
    _content = html.LABEL(_str)
    _content.style = DirectionStyle.get(_dict['Direction'],{})
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    if Orders and Orders[0].id == _id:
        Orders = [some]+Orders[1:count]
    else:
        Orders = [some]+Orders[:count]
    _doc.clear()
    for one in Orders:
        _doc <= one

Trades = []
def event_trade(_msg):
    global Trades
    _doc = document['trade']
    _dict = _msg['data']
    _id = "trade_{}_{}".format(_msg['_account_'],_dict['OrderRef'])
    _str = str(datetime.datetime.now())[11:19]+" [ {} ] {} {} {} 成交手数:{} 成交价:{}".format(_msg['_account_'],_dict['InstrumentID'],DirectionDict.get(_dict['Direction'],"未知方向"),OffsetFlagDict.get(_dict['OffsetFlag'],"未知开平"),_dict['Volume'],'%.2f'%float(_dict['Price']))
    _content = html.LABEL(_str)
    _content.style = DirectionStyle.get(_dict['Direction'],{})
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    if Trades and Trades[0].id == _id:
        Trades = [some]+Trades[1:count]
    else:
        Trades = [some]+Trades[:count]
    _doc.clear()
    for one in Trades:
        _doc <= one

Ticks = set()
TickDict = {}
def event_tick(_msg):
    global Ticks
    global TickDict
    _doc = document['marketdata']
    _l = _doc.children
    _data = _msg['data']
    _id = "tick_{}".format(_data['InstrumentID'])
    _content = width_label(_data['InstrumentID'],100)
    _content += width_label("叫卖1",30)+width_label(_data["AskPrice1"],50)+width_label(_data["AskVolume1"],50)
    _content += width_label("叫买1",50)+width_label(_data["BidPrice1"],50)+width_label(_data["BidVolume1"],50)
    _content += width_label("最新价",40)
    _content += width_label(_data["LastPrice"],50)
    _content += width_label("成交量",40)
    _content += width_label(_data["Volume"],50)
    _content += width_label(_data["UpdateTime"],50)
    _content += width_label(_msg["_qsize_"],10)
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    Ticks.add(_id)
    TickDict[_id] = some
    _doc.clear()
    for one in Ticks:
        _doc <= TickDict[one]

def event_tickclear(_msg):
    global Ticks
    global TickDict
    _data = _msg['data']
    _id = "tick_{}".format(_data['InstrumentID'])
    if _id in Ticks:
        Ticks.remove(_id)
    if _id in TickDict:
        TickDict.pop(_id)
    _doc.clear()
    for one in Ticks:
        _doc <= TickDict[one]

PosAccount = set()
PosInst = set()
PosDir = ["2","3"]
PosDict = {}

def event_position(_msg):
    global PosAccount
    global PosInst
    global PosDir
    global PosDict
    _doc = document['position']
    _dict = _msg['data']
    _id = "position_{}_{}_{}".format(_msg['_account_'],_dict['InstrumentID'],_dict['PosiDirection'])
    PosAccount.add(_msg['_account_'])
    PosInst.add(_dict['InstrumentID'])
    _str = ''
    _str += width_label("帐号",30)
    _str += width_label(_msg['_account_'],80)
    _str += width_label("合约",30)
    _str += width_label(_dict['InstrumentID'],80)
    _str += width_label("今仓",30)
    _str += width_label(_dict['TodayPosition'],80)
    _str += width_label("昨仓",50)
    _str += width_label(_dict['YdPosition'],80)
    _str += width_label("总仓",50)
    _str += width_label(_dict['Position'],80)
    _content = html.LABEL(_str)
    _content.style = DirectionStyle.get(_dict['PosiDirection'],{})
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    PosDict[_id] = some
    _doc.clear()
    for pac in PosAccount:
        for pinst in PosInst:
            for pdir in PosDir:
                _pid = "position_{}_{}_{}".format(pac,pinst,pdir)
                if _pid in PosDict:
                    _doc <= PosDict[_pid]

Accounts = set()
AccDict = {}
def event_account(_msg):
    global Accounts
    global AccDict
    _doc = document['account']
    _dict = _msg['data']
    _id = "account_{}".format(_msg['_account_'])
    Accounts.add(_id)
    _str = ''
    _str+= width_label("帐号",30)
    _str+= width_label(_msg['_account_'],80)
    _str+= width_label("持仓盈亏",50)
    _str+= width_label('%.2f'%float(_dict['PositionProfit']),80)
    _str+= width_label("可用",30)
    _str+= width_label('%.2f'%float(_dict['Available']),80)
    _str+= width_label("净值",30)
    _str+= width_label('%.2f'%float(_dict['Balance']),80)
    _content = html.LABEL(_str)
    some = html.DIV(_content,id=_id)
    some.style={"text-align":"left"}
    AccDict[_id] = some
    _doc.clear()
    for one in Accounts:
        _doc <= AccDict[one]

def event_skip(_msg):pass

def empty_func(_msg):
    add_log(str(_msg))

funcs = {
            EVENT_EMPTY:empty_func,
            EVENT_LOG:event_log,
            EVENT_TICK:event_tick,
            EVENT_ORDER:event_order,
            EVENT_TRADE:event_trade,
            EVENT_ACCOUNT:event_account,
            EVENT_POSIALL:event_position,
            EVENT_PRODUCT:event_product,
            EVENT_TICK_CLEAR:event_tickclear,
    }

def ws_msg(ev):
    _msg = json.loads(ev.data)
    _type = _msg.get('_type_',EVENT_EMPTY)
    if _type in funcs:
        funcs[_type](_msg)
    else:
        event_skip(_msg)

def reconnect():
    add_log("重连ing")
    window.location.reload()

def ws_open():
    if 'ws_server' not in storage or storage['ws_server'] not in document['websocket_ip'].value:
        storage['ws_server'] = cache['ips'][cache['ips_pos']]
        add_log('连接至'+storage['ws_server']+'并存储该地址')
#    timer.set_timeout(step_one, 1000)

def ws_error():
    add_log("!!!websocket连接报错!!!")
    if 'ws_server' not in storage or storage['ws_server'] not in document['websocket_ip'].value:
        if cache['ips_pos']+1 <= len(cache['ips']):
            global ws
            cache['ips_pos'] = cache['ips_pos']+1
            ip = cache['ips'][cache['ips_pos']]
            address = 'ws://'+ip+":9789/websocket"
            ws = websocket.WebSocket(address)


def ws_disconnected():
    add_log("服务器端断开连接,3秒后尝试重连")
    idTimer = timer.set_timeout(reconnect, 3000)

ws.bind('message',ws_msg)
ws.bind('close',ws_disconnected)
ws.bind('open',ws_open)
ws.bind('error',ws_error)
