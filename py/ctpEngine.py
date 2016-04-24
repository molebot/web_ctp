# encoding: UTF-8
from datetime import date,datetime
from time import time
from rule import Product_Time_Rule
import zmq
from remote import *
from string import lowercase as _chars
from string import uppercase as _CHARS
from ctp_data_type import defineDict

_TODAYPOSITIONDATE_ = defineDict["THOST_FTDC_PSD_Today"]#'1'
_YDPOSITIONDATE_    = defineDict["THOST_FTDC_PSD_History"]#'2'

_LONGDIRECTION_     = defineDict["THOST_FTDC_PD_Long"]#'2'
_SHORTDIRECTION_    = defineDict["THOST_FTDC_PD_Short"]#'3'

from ctpApi import *
from eventEngine import EventEngine
from threading import Lock

class SymbolOrdersManager:
    def __init__(self,symbol,data,me):
        self.symbol = symbol
        self.data = data
        self.exchange = data['ExchangeID']
        self.productid = data['ProductID']
        self.pointValue = data['VolumeMultiple']
        self.marginRatio = '%.3f'%max(data['LongMarginRatio'],data['ShortMarginRatio'])
        self.me = me
        self.__lock = Lock()
        self.__maxRetry = 5
        self.__status = {}
        self.__orders = {}
        self.__hold = 0
        self.__signal = 0
        self.__last = 0
        self.__timecheck = 0
        self.__timepass = 0
        self.__timerule = Product_Time_Rule.get(self.productid,[lambda x:x>0])#默认交易
        self.__price = {}
        self.__onWay = {}
    def openPosition(self,tr,volume):
        print(tr,volume,'SymbolOrdersManager.openPosition')
        if volume<=0:return
        event = Event(type_=EVENT_LOG)
        log = u'开仓[%s] 方向[%d] 数量[%d]'%(self.symbol,tr,volume)
        event.dict_['log'] = log
        self.me.ee.put(event)
        self.me.countGet = -2
        offset = defineDict['THOST_FTDC_OF_Open']
        pricetype = defineDict['THOST_FTDC_OPT_LimitPrice']
        if tr>0:
            price = self.__price['ask']+self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Buy"]
        else:
            price = self.__price['bid']-self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Sell"]
        exchangeid = self.data["ExchangeID"]
        _ref = self.me.td.sendOrder(self.symbol,exchangeid,price,pricetype,volume,direction,offset)
        self.__orders[_ref] = (self.symbol,exchangeid,price,pricetype,volume,direction,offset,0,time())
        self.__onWay[_ref] = volume*tr
    def closePosition(self,tr,volume):
        print(tr,volume,'SymbolOrdersManager.closePosition')
        if volume<=0:return
        if tr>0:
            if self.exchange in ['SHFE', 'CFFEX']:
                _haved = self.__status.get(_LONGDIRECTION_,{}).get(_YDPOSITIONDATE_,0)
            else:
                _haved = self.__status.get(_LONGDIRECTION_, {}).get(_TODAYPOSITIONDATE_, 0)
                _haved += self.__status.get(_LONGDIRECTION_,{}).get(_YDPOSITIONDATE_,0)
        else:
            if self.exchange in ['SHFE', 'CFFEX']:
                _haved = self.__status.get(_SHORTDIRECTION_,{}).get(_YDPOSITIONDATE_,0)
            else:
                _haved = self.__status.get(_SHORTDIRECTION_, {}).get(_TODAYPOSITIONDATE_, 0)
                _haved += self.__status.get(_SHORTDIRECTION_,{}).get(_YDPOSITIONDATE_,0)
        volume = min(abs(_haved),volume)
        event = Event(type_=EVENT_LOG)
        log = u'平仓[%s] 方向[%d] 数量[%d]'%(self.symbol,tr,volume)
        event.dict_['log'] = log
        self.me.ee.put(event)
        self.me.countGet = -2
        offset = defineDict['THOST_FTDC_OF_Close']
        pricetype = defineDict['THOST_FTDC_OPT_LimitPrice']
        if tr<0:
            price = self.__price['ask']+self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Buy"]
        else:
            price = self.__price['bid']-self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Sell"]
        exchangeid = self.data["ExchangeID"]
        _ref = self.me.td.sendOrder(self.symbol,exchangeid,price,pricetype,volume,direction,offset)
        self.__orders[_ref] = (self.symbol,exchangeid,price,pricetype,volume,direction,offset,0,time())
        self.__onWay[_ref] = -1*volume*tr
    def closeTodayPosition(self,tr,volume):
        print(tr,volume,'SymbolOrdersManager.closeTodayPosition')
        if volume<=0:return
        if tr>0:
            _haved = self.__status.get(_LONGDIRECTION_,{}).get(_TODAYPOSITIONDATE_,0)
        else:
            _haved = self.__status.get(_SHORTDIRECTION_,{}).get(_TODAYPOSITIONDATE_,0)
        volume = min(abs(_haved),volume)
        event = Event(type_=EVENT_LOG)
        log = u'平今仓[%s] 方向[%d] 数量[%d]'%(self.symbol,tr,volume)
        event.dict_['log'] = log
        self.me.ee.put(event)
        self.me.countGet = -2
        offset = defineDict['THOST_FTDC_OF_CloseToday']
        pricetype = defineDict['THOST_FTDC_OPT_LimitPrice']
        if tr<0:
            price = self.__price['ask']+self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Buy"]
        else:
            price = self.__price['bid']-self.data['PriceTick']*2.0
            direction = defineDict["THOST_FTDC_D_Sell"]
        exchangeid = self.data["ExchangeID"]
        _ref = self.me.td.sendOrder(self.symbol,exchangeid,price,pricetype,volume,direction,offset)
        self.__orders[_ref] = (self.symbol,exchangeid,price,pricetype,volume,direction,offset,0,time())
        self.__onWay[_ref] = -1*volume*tr
    def ontrade(self,event):pass
    def onorder(self,event):#pass
        _data = event.dict_['data']
        if _data['OrderStatus'] == '5':
            _ref = int(_data['OrderRef'])
            if int(_data['OrderRef']) in self.__orders:
                _saved = self.__orders.pop(int(_data['OrderRef']))
                _volume = self.__onWay.pop(_ref)
            else:
                return 0
            if _saved[-1]>=self.__maxRetry:
                return 0
            event = Event(type_=EVENT_LOG)
            log = u'未成交已撤单，补单'
            event.dict_['log'] = log
            self.me.ee.put(event)
            if _saved[5] == defineDict["THOST_FTDC_D_Buy"]:
                price = float(_saved[2])+self.data['PriceTick']
            elif _saved[5] == defineDict["THOST_FTDC_D_Sell"]:
                price = float(_saved[2])-self.data['PriceTick']
            else:
                price = -1
                print("ctpEngine.py SymbolOrdersManager onorder not found THOST_FTDC_D")
            _ref = self.me.td.sendOrder(_saved[0],_saved[1],price,_saved[3],_saved[4],_saved[5],_saved[6])
            self.__orders[_ref] = (_saved[0],_saved[1],price,_saved[3],_saved[4],_saved[5],_saved[6],_saved[7]+1,_saved[8])
            self.__onWay[_ref] = _volume
        elif _data['OrderStatus'] == '2':
            _ref = int(_data['OrderRef'])
            if int(_data['OrderRef']) in self.__orders:
                _saved = self.__orders.pop(int(_data['OrderRef']))
                _volume = self.__onWay.pop(_ref)
            else:
                return 0
            if _saved[-1]>=self.__maxRetry:
                return 0
            event = Event(type_=EVENT_LOG)
            log = u'部分成交，其余已撤单，补单'
            event.dict_['log'] = log
            self.me.ee.put(event)
            if _saved[5] == defineDict["THOST_FTDC_D_Buy"]:
                price = float(_saved[2])+self.data['PriceTick']
            elif _saved[5] == defineDict["THOST_FTDC_D_Sell"]:
                price = float(_saved[2])-self.data['PriceTick']
            else:
                price = -1
                print("ctpEngine.py SymbolOrdersManager onorder not found THOST_FTDC_D")
            _todo = _saved[4]-_data['VolumeTraded']
            _ref = self.me.td.sendOrder(_saved[0],_saved[1],price,_saved[3],_todo,_saved[5],_saved[6])
            self.__orders[_ref] = (_saved[0],_saved[1],price,_saved[3],_todo,_saved[5],_saved[6],_saved[7]+1,_saved[8])
            self.__onWay[_ref] = _todo*_volume/abs(_volume)
        elif _data['OrderStatus'] == '0':
            event = Event(type_=EVENT_LOG)
            log = u'全部成交'
            event.dict_['log'] = log
            self.me.ee.put(event)
            _ref = int(_data['OrderRef'])
            if int(_data['OrderRef']) in self.__orders:
                self.__orders.pop(int(_data['OrderRef']))
                self.__onWay.pop(_ref)
    def ontick(self,event):#pass
        _data = event.dict_['data']
        _ask = _data['AskPrice1']
        _bid = _data['BidPrice1']
        if _ask+_bid==0:return
        _symbol = _data['InstrumentID']
        if _symbol not in self.me.tickpass:return
        _exchange =  self.data.get("ExchangeID",'')
        self.__price = {"ask":_ask,"bid":_bid,"price":(_ask*_ask+_bid*_bid)/(_ask+_bid)}
        if time()>self.__timecheck:
            self.__timecheck = int(time()/60)*60+60
            _now = datetime.now()
            self.me.now = _now
            _time = _now.hour*100+_now.minute
            self.__timepass = [one(_time) for one in self.__timerule].count(True)
        with self.__lock:
            if self.me.socket:
                if (self.symbol,self.exchange) not in self.me.subInstrument:
                    self.__hold = 0
                elif self.__timepass>0:
                    _dict = {"ratio":self.marginRatio,"point":self.pointValue,"account":self.me.userid,"eq":self.me.eq,"price":self.__price['price'],"exchange":'ctp',"symbol":self.productid,"act":"result"}
                    self.__hold = self.me.corefunc(_dict,self)
                else:
                    self.__hold = 0
            else:
                return
            
            for k,v in self.__orders.items():
                if time()-v[8]>1:
                    self.__orders.pop(k)
            if len(self.__orders)>0:
                print(self.symbol,self.__orders)
            else:
                _long       =   defineDict["THOST_FTDC_PD_Long"]
                _short      =   defineDict["THOST_FTDC_PD_Short"]
                long_st     =   self.__status.get(_long,{})
                short_st    =   self.__status.get(_short,{})

                def do_it(_todo,_pass,_reverse,d_pass,d_reverse):
                    if self.__status.get(_reverse,{}).get(_YDPOSITIONDATE_,0)>0:
                        self.closePosition(d_reverse,self.__status[_reverse][_YDPOSITIONDATE_])
                    if self.__status.get(_reverse,{}).get(_TODAYPOSITIONDATE_,0)>0:
                        if self.exchange in ['SHFE','CFFEX']:
                            self.closeTodayPosition(d_reverse,self.__status[_reverse][_TODAYPOSITIONDATE_])
                        else:
                            self.closePosition(d_reverse,self.__status[_reverse][_TODAYPOSITIONDATE_])

                    self.__status[_reverse] = {}

                    _old = self.__status.get(_pass,{})
                    _old_old = _old.get(_YDPOSITIONDATE_,0)
                    _old_today = _old.get(_TODAYPOSITIONDATE_,0)
                    _haved = sum(_old.values())

                    if _todo>_haved:
                        self.openPosition(d_pass,_todo-_haved)
                        _old[_TODAYPOSITIONDATE_] = _old_today+(_todo-_haved)
                    elif _todo<_haved:
                        if _todo-_haved > _old_old:
                            # 昨仓全平 今仓平一部分
                            self.closePosition(_pass,_old_old)
                            _old[_YDPOSITIONDATE_] = 0
                            if self.exchange in ['SHFE','CFFEX']:
                                self.closeTodayPosition(_pass,_todo-_haved-_old_old)
                            else:
                                self.closePosition(_pass,_todo-_haved-_old_old)
                            _old[_TODAYPOSITIONDATE_] = _old_today - (_todo-_haved-_old_old)
                        elif _todo-_haved == _old_old:
                            # 昨仓全平
                            self.closePosition(_pass,_old_old)
                            _old[_YDPOSITIONDATE_] = 0
                        else:
                            # 昨仓平一部分
                            self.closePosition(_pass,_todo-_haved)
                            _old[_YDPOSITIONDATE_] = _old_old - (_todo-_haved)

                    self.__status[_pass] = _old
            
                if self.__signal!=self.__hold:
                    self.__signal = self.__hold
                    if self.__hold==0:
                        if long_st.get(_YDPOSITIONDATE_,0)>0:
                            self.closePosition(1,long_st[_YDPOSITIONDATE_])
                        if long_st.get(_TODAYPOSITIONDATE_,0)>0:
                            if self.exchange in ['SHFE','CFFEX']:
                                self.closeTodayPosition(1,long_st[_TODAYPOSITIONDATE_])
                            else:
                                self.closePosition(1,long_st[_TODAYPOSITIONDATE_])
                        if short_st.get(_YDPOSITIONDATE_,0)>0:
                            self.closePosition(-1,short_st[_YDPOSITIONDATE_])
                        if short_st.get(_TODAYPOSITIONDATE_,0)>0:
                            if self.exchange in ['SHFE','CFFEX']:
                                self.closeTodayPosition(-1,short_st[_TODAYPOSITIONDATE_])
                            else:
                                self.closePosition(-1,short_st[_TODAYPOSITIONDATE_])
                        self.__status = {}
                        if self.__last != self.__hold:
                            self.__last = self.__hold
                            for _key in ['2','3']:
                                _dict = {}
                                _dict['InstrumentID'] = self.symbol
                                _dict['PosiDirection'] = _key
                                _dict['TodayPosition'] = 0
                                _dict['YdPosition'] = 0
                                _dict['Position'] = 0
                                event = Event(type_=EVENT_POSIALL)
                                event.dict_['data'] = _dict
                                self.me.ee.put(event)
                    elif self.__hold>0:
                        _todo = abs(self.__hold)
                        _pass = _long
                        _reverse = _short
                        d_pass = 1
                        d_reverse = -1
                        do_it(_todo,_pass,_reverse,d_pass,d_reverse)
                    elif self.__hold<0:
                        _todo = abs(self.__hold)
                        _pass = _short
                        _reverse = _long
                        d_pass = -1
                        d_reverse = 1
                        do_it(_todo,_pass,_reverse,d_pass,d_reverse)

    def onposi(self,event):#pass
        _dict = event.dict_['data']
        _dict.pop('InstrumentID')
        
        with self.__lock:
            self.__status = {}
            _hold = 0
            for k,_vol in _dict.items():
                _dir,_date = k
                _old = self.__status.get(_dir,{})
                _old[_date] = _vol
                if _dir==_LONGDIRECTION_:
                    _hold+= _vol
                elif _dir==_SHORTDIRECTION_:
                    _hold-=_vol
                else:
                    print('SymbolOrdersManager.onposition,UNKNOW_DIRECTION')
                self.__status[_dir] = _old
            
            self.__signal = _hold+sum(self.__onWay.values())
            print(self.symbol,' hold:',self.__signal,' signal:',self.__hold,' status:',self.__status,'SymbolOrdersManager.onposition')

            for k,v in self.__status.items():
                event2 = Event(type_=EVENT_POSIALL)
                data = {}
                data['InstrumentID']    = self.symbol
                data['PosiDirection']   = k
                data['TodayPosition']   = v.get(_TODAYPOSITIONDATE_,0)
                data['YdPosition']      = v.get(_YDPOSITIONDATE_,0)
                data['Position']        = data['TodayPosition']+data['YdPosition']
                event2.dict_['data'] = data
                event2.symbol = event.symbol
                self.me.ee.put(event2)

        if (self.symbol,self.exchange) not in self.me.subedInstrument:
            self.me.subscribe(self.symbol, self.exchange)

########################################################################
class MainEngine:

    #----------------------------------------------------------------------
    def __init__(self, account, _plus_path, bg):

        self.ee = EventEngine(account)         # 创建事件驱动引擎
        self.bridge = bg
        self.__lock = Lock()
        self.userid = str(account['userid'])
        self.password = str(account['password'])
        self.brokerid = str(account['brokerid'])
        self.mdaddress = str(account['mdfront'])
        self.tdaddress = str(account['tdfront'])
        self.instrument = account['instrument'] #   sub list str
        self.pluspath = _plus_path

        self.dictInstrument = {}        # 字典（保存合约查询数据）
        self.dictProduct = {}        # 字典（保存合约查询数据）
        self.dictExchange= {}
        self.tmpInstrument = {}        # 字典（保存合约查询数据）
        self.tmpProduct = {}        # 字典（保存合约查询数据）
        self.tmpExchange= {}
        self.dictUpdate = None
        self.subInstrument = set()
        self.subedInstrument = set()
        self.master = {}    #   记录主力合约对应关系
        self.masterSubed = False
        self.subedMaster = {}
        self.tickpass = set()
        self.now = datetime.now()
        self.socket = None
        self.coreServer = str(account['zmqserver'])
        self.corefunc = passit
        if int(account['usezmq'])>0:
            if self.coreServer[:4] == 'tcp:':
                context = zmq.Context()
                socket = context.socket(zmq.REQ)
                socket.connect(self.coreServer)
                self.socket = socket
                self.corefunc = tcpfunc
            elif self.coreServer[:5] == 'http:':
                self.socket = True
                self.corefunc = httpfunc
        self.ee.start()                 # 启动事件驱动引擎
        self.som = {}

        self.lastError = 0
        self.lastTodo = 0

        self.eq = 0

        # 循环查询持仓和账户相关
        self.countGet = 0               # 查询延时计数
        self.lastGet = 'Account'        # 上次查询的性质
        self.ee.register(EVENT_TDLOGIN, self.initGet,True)  # 登录成功后开始初始化查询

        self.__timer = time()+3
        self.__readySubscribe = {}
        
        # 合约储存相关

        self.get_instrument()
        self.get_subscribe(self.instrument)
        self.ee.register(EVENT_MDLOGIN,     self.ready_subscribe,True)
        self.ee.register(EVENT_TDLOGIN,     self.ready_subscribe,True)
        self.ee.register(EVENT_ERROR,       self.get_error,False)
        self.ee.register(EVENT_INSTRUMENT,  self.insertInstrument,True)
        self.ee.register(EVENT_TIMER,       self.getAccountPosition,False)
        self.ee.register(EVENT_TRADE,       self.get_trade,False)
        self.ee.register(EVENT_ORDER,       self.get_order,False)
        self.ee.register(EVENT_TICK,        self.get_tick,True)
        self.ee.register(EVENT_POSITION,    self.get_position,False)
        self.ee.register(EVENT_ACCOUNT,     self.get_account,False)

        self.ee.register(EVENT_TICK,        self.check_timer,False)

        import eventType
        for k,v in eventType.__dict__.items():
            if 'EVENT_' in k and v[0]!='_':
                self.ee.register(v,self.websocket_send,False)

        self.md = ctpMdApi(self, self.mdaddress, self.userid, self.password, self.brokerid, plus_path=_plus_path)    # 创建API接口
        self.td = ctpTdApi(self, self.tdaddress, self.userid, self.password, self.brokerid, plus_path=_plus_path)

    def get_subscribe(self,_inst):
        if '#' in _inst:
            _instlist = [ (v.get('_vol_',0),k) for k,v in self.dictInstrument.items()]
            _instlist.sort(reverse=True)
            _only = set()
            for v,_instrumentid in _instlist[:10]:
                _product = self.dictInstrument[_instrumentid]['ProductID']
                if _product not in _only:
                    _exchangeid = self.dictInstrument.get(_instrumentid,{}).get("ExchangeID",'')
                    self.subInstrument.add((_instrumentid,_exchangeid))
                    self.subedMaster[_instrumentid] = 1
                    self.tickpass.add(_instrumentid)
                    _only.add(_product)
            for _productid in ['IF','IH','IC']:
                if _productid in self.dictProduct and _productid not in _only:
                    _product = self.dictProduct[_productid]
                    _productlist = [ (v,k) for k,v in _product.items()]
                    _productlist.sort(reverse=True)
                    _instrumentid = _productlist[0][-1]
                    _exchangeid = self.dictInstrument.get(_instrumentid,{}).get("ExchangeID",'')
                    self.subInstrument.add((_instrumentid,_exchangeid))
                    self.master[_productid] = _product
                    self.subedMaster[_instrumentid] = 1
                    self.tickpass.add(_instrumentid)
            for _productid,_product in self.dictProduct.items():
                self.master[_productid] = _product

        else:
            _all = _inst.split('+')
            for one in _all:
                if '=' in one:
                    _productid = one[:-1]
                    if _productid in self.dictProduct:
                        _product = self.dictProduct[_productid]
                        _productlist = [ (v,k) for k,v in _product.items()]
                        _productlist.sort(reverse=True)
                        _instrumentid = _productlist[0][-1]
                        _exchangeid = self.dictInstrument.get(_instrumentid,{}).get("ExchangeID",'')
                        self.subInstrument.add((_instrumentid,_exchangeid))
                        self.master[_productid] = _product
                        self.subedMaster[_instrumentid] = 1
                        self.tickpass.add(_instrumentid)
                else:
                    _instrumentid = one
                    _exchangeid = self.dictInstrument.get(_instrumentid,{}).get("ExchangeID",'')
                    self.subInstrument.add((_instrumentid,_exchangeid))
                    self.tickpass.add(_instrumentid)
            print(self.subInstrument)
    def ready_subscribe(self,event):
        self.__readySubscribe[event.type_] = 1
        if len(self.__readySubscribe) == 2:
            for one in self.subInstrument:
                if one[0] in self.subedMaster:
                    event = Event(type_=EVENT_LOG)
                    log = u'订阅主力合约:%s[%s]'%(one[0],self.dictInstrument[one[0]]['InstrumentName'])
                    event.dict_['log'] = log
                    self.ee.put(event)
                else:
                    event = Event(type_=EVENT_LOG)
                    log = u'订阅合约:%s[%s]'%(one[0],self.dictInstrument[one[0]]['InstrumentName'])
                    event.dict_['log'] = log
                    self.ee.put(event)
                self.subscribe(one[0],one[1])
    def get_instrument(self):
        _dict = self.bridge.get_instrument()
        self.dictInstrument = _dict.get('instrument',{})
        self.dictExchange = _dict.get('exchange',{})
        self.dictProduct = _dict.get('product',{})
        self.dictUpdate = _dict.get('day',None)
    def set_instrument(self):
        _dict = {}
        _dict['instrument'] = self.dictInstrument
        _dict['exchange'] = self.dictExchange
        _dict['product'] = self.dictProduct
        _dict['day'] = date.today()
        _dict['_day_'] = str(date.today())
        self.bridge.set_instrument(_dict)
    def get_som(self,event):
        try:
            symbol = event.dict_['data']['InstrumentID']
            if symbol:
                if symbol not in self.tickpass:return
                if symbol in self.som:
                    return self.som[symbol]
                else:
                    _data = None
                    if symbol in self.dictInstrument:
                        _data = self.dictInstrument[symbol]
                        event = Event(type_=EVENT_LOG)
                        log = u'初始化合约[%s]并填充其基本信息'%symbol
                        event.dict_['log'] = log
                        self.ee.put(event)
                    else:
                        _productid = filter(lambda x:x in _chars+_CHARS,symbol)
                        if _productid in self.dictProduct:
                            for _instrument in self.dictProduct[_productid].keys():
                                if _instrument in self.dictInstrument:
                                    _data = self.dictInstrument[_instrument]
                                    event = Event(type_=EVENT_LOG)
                                    log = u'注意:初始化合约[%s]但填充了<%s>的基本信息'%(symbol,_instrument)
                                    event.dict_['log'] = log
                                    self.ee.put(event)
                                    break
                    if _data:
                        one = SymbolOrdersManager(symbol,_data,self)
                        self.som[symbol] = one
                        return one
                    else:
                        event = Event(type_=EVENT_LOG)
                        log = u'警告:初始化合约[%s]失败，未发现其基本信息'%symbol
                        event.dict_['log'] = log
                        self.ee.put(event)
                        print("ctpEngine.py MainEngine get_som not found Instrument Info")
                        return None
            else:
                return None
        except Exception,e:
            print("ctpEngine.py MainEngine get_som ERROR",e)
            print(event.type_,event.dict_['data'])
    def get_mastervol(self,event):
        _data = event.dict_['data']
        _instrument = _data['InstrumentID']
        _symbol = self.dictInstrument.get(_instrument,{})
        if _symbol:
            if self.subedMaster:
                _product = _symbol['ProductID']
                _exchange = _symbol['ExchangeID']
                with self.__lock:
                    if _instrument in self.subedMaster:
                        self.dictProduct[_product][_instrument] = _data['Volume']
                        _p = self.dictInstrument.get(_instrument,{}).get('VolumeMultiple',0)
                        self.dictInstrument[_instrument]['_vol_'] = _data['Volume']*_p
                        self.set_instrument()
                        if _instrument not in self.tickpass:
                            self.unsubscribe(_instrument,_exchange)
                        self.subedMaster.pop(_instrument)
            else:
                event = Event(type_=EVENT_LOG)
                log = u'主力合约数据获取完毕'
                event.dict_['log'] = log
                self.ee.put(event)
                self.ee.unregister(EVENT_TICK,self.get_mastervol,False)
                event = Event(type_=EVENT_LOG)
                log = u'取消合约成交量事件注册'
                event.dict_['log'] = log
                self.ee.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = u'未发现合约信息:%s'%_instrument
            event.dict_['log'] = log
            self.ee.put(event)

    def check_timer(self,event):
        if time()>=self.__timer:
            self.__timer = time()+1
            event = Event(type_=EVENT_TIMER)
            self.ee.put(event)

            if not self.masterSubed and self.master and self.now.hour==14 and self.now.minute>=58:
                self.masterSubed = True
                self.ee.register(EVENT_TICK,self.get_mastervol,False)
                event = Event(type_=EVENT_LOG)
                log = u'注册合约成交量事件'
                event.dict_['log'] = log
                self.ee.put(event)

            if self.masterSubed and self.master:
                with self.__lock:
                    _key = self.master.keys()[0]
                    _instruments = self.master.pop(_key)
                    for _instrument in _instruments:
                        _exchange = self.dictInstrument.get(_instrument,{}).get("ExchangeID",'')
                        self.subscribe(_instrument,_exchange)
                        if _instrument not in self.subedMaster:
                            self.subedMaster[_instrument] = 0
    def set_ws(self,ws):
        self.websocket = ws
    def websocket_send(self,event):
        try:
            self.bridge.send_ws(event)
        except:
            pass
    def get_error(self,event):
        print(event.dict_['log'])
        print(event.dict_['ErrorID'])
        self.lastError = event.dict_['ErrorID']
    def get_order(self,event):
        som = self.get_som(event)
        if som:som.onorder(event)
    def get_trade(self,event):
        som = self.get_som(event)
        if som:som.ontrade(event)
    def get_position(self,event):
        som = self.get_som(event)
        if som:som.onposi(event)
    def get_tick(self,event):
        som = self.get_som(event)
        if som:som.ontick(event)
    def get_account(self,event):
        _data = event.dict_['data']
        self.eq = _data['Balance']
    def zmq_heart(self):
        if self.socket:
            self.socket.send(bytes(json.dumps({"act":"ping"})))
            try:
                _msg = self.socket.recv()
                if _msg != "pong":print("zmq timeout")
            except Exception,e:
                print("zmq_heart error",e)
        else:
            print("no zmq")
    #----------------------------------------------------------------------
    def login(self):
        """登陆"""
        print("me.login")
        self.td.login()
        self.md.login()
    
    #----------------------------------------------------------------------
    def subscribe(self, instrumentid, exchangeid):
        """订阅合约"""
        self.md.subscribe(str(instrumentid), str(exchangeid))
        self.subedInstrument.add((instrumentid, exchangeid))
    #----------------------------------------------------------------------
    def unsubscribe(self, instrumentid, exchangeid):
        """取消订阅合约"""
        self.md.unsubscribe(str(instrumentid), str(exchangeid))
        if (instrumentid, exchangeid) in self.subedInstrument:
            self.subedInstrument.remove((instrumentid, exchangeid))
    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        self.td.getAccount()
        
    #----------------------------------------------------------------------
    def getInvestor(self):
        """查询投资者"""
        self.td.getInvestor()
        
    #----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        self.td.getPosition()
    
    #----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction, offset):
        """发单"""
        self.td.sendOrder(instrumentid, exchangeid, price, pricetype, volume, direction, offset)
        
    #----------------------------------------------------------------------
    def cancelOrder(self, instrumentid, exchangeid, orderref, frontid, sessionid):
        """撤单"""
        self.td.cancelOrder(instrumentid, exchangeid, orderref, frontid, sessionid)
        
    #----------------------------------------------------------------------
    def getAccountPosition(self, event):
        """循环查询账户和持仓"""
        self.countGet = self.countGet + 1
        
        # 每1秒发一次查询
        if self.countGet > 0:
            if self.countGet>2:
                self.countGet = 0
                if self.lastGet == 'Account':
                    self.lastGet = 'Position'
                    self.getPosition()
                else:
                    self.lastGet = 'Account'
                    self.getAccount()
        else:
            self.getPosition()
    #----------------------------------------------------------------------
    def initGet(self, event):
        """在交易服务器登录成功后，开始初始化查询"""
        self.getInstrument()
    #----------------------------------------------------------------------
    def getInstrument(self,fetch_new=True):
        """获取合约"""

        event = Event(type_=EVENT_LOG)
        log = u'获取合约...'
        event.dict_['log'] = log
        self.ee.put(event)

        if self.dictUpdate==date.today() and not fetch_new:

            event = Event(type_=EVENT_PRODUCT)
            event.dict_['data'] = self.dictProduct
            self.ee.put(event)

            event = Event(type_=EVENT_LOG)
            log = u'得到本地合约!'
            event.dict_['log'] = log
            self.ee.put(event)

            self.getPosition()
        else:
            event = Event(type_=EVENT_LOG)
            log = u'查询合约信息...'
            event.dict_['log'] = log
            self.ee.put(event)
            self.td.getInstrument()
    def product_print(self):
        return(0)
        print("self.dictExchange ",self.dictExchange.keys())
        for k,v in self.dictProduct.items():
            print(k)
            for _inst,_data in v.items():
                print("  "+_inst+" : "+self.dictInstrument[_inst]['InstrumentName'])
                data = self.dictInstrument[_inst]
        print data
    def insertInstrument(self, event):
        """插入合约对象"""
        data = event.dict_['data']
        _update_ = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last = event.dict_['last']
        if data['InstrumentID'] in self.dictInstrument:
            if '_vol_' in self.dictInstrument[data['InstrumentID']]:
                data['_vol_'] = self.dictInstrument[data['InstrumentID']]['_vol_']
            else:
                data['_vol_'] = -1
        data['_update_'] = _update_
        if data['ProductID'] not in self.tmpProduct:
            self.tmpProduct[data['ProductID']] = {}
        if data['ExchangeID'] not in self.tmpExchange:
            self.tmpExchange[data['ExchangeID']] = {}
        if data['ProductID'] not in self.tmpExchange[data['ExchangeID']]:
            self.tmpExchange[data['ExchangeID']][data['ProductID']] = {}
        if data['ProductID'] in data['InstrumentID'] and data['IsTrading']==1:
            self.tmpExchange[data['ExchangeID']][data['ProductID']][data['InstrumentID']] = 1
            self.tmpProduct[data['ProductID']][data['InstrumentID']] = self.dictProduct.get(data['ProductID'],{}).get(data['InstrumentID'],0)
            self.tmpInstrument[data['InstrumentID']] = data
            print(data['InstrumentID'])

        # 合约对象查询完成后，查询投资者信息并开始循环查询
        if last:
            print('getInstrument OK')
            # 将查询完成的合约信息保存到本地文件，今日登录可直接使用不再查询
            self.dictProduct = self.tmpProduct
            self.dictInstrument = self.tmpInstrument
            self.dictExchange = self.tmpExchange
            self.set_instrument()

            event = Event(type_=EVENT_LOG)
            log = u'合约查询完成!'
            event.dict_['log'] = log
            self.ee.put(event)            

            event1 = Event(type_=EVENT_PRODUCT)
            event1.dict_['data'] = self.dictProduct
            self.ee.put(event1)

            self.getPosition()

    #----------------------------------------------------------------------
    def selectInstrument(self, instrumentid):
        """获取合约信息对象"""
        try:
            instrument = self.dictInstrument[instrumentid]
        except KeyError:
            instrument = None
        return instrument
    
    #----------------------------------------------------------------------
    def exitEvent(self,e):
        self = None
    def exit(self):
        """退出"""
        # 销毁API对象
        self.td = None
        self.md = None
        
        # 停止事件驱动引擎
        self.ee.stop()

    def __del__(self):
        self.exit()
