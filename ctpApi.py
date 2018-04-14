# encoding: UTF-8
from vnctpmd import MdApi
from vnctptd import TdApi
from eventEngine import *
from ctp_data_type import defineDict
from log import *
from string import lowercase as _chars
import os
from settings_ctp import *
from settings_mongo import *
from AccountPassword import AccountPasswordManager as APM

apm = APM()

def num2string(num_list):
    return ''.join([_chars[int(x)] for x in num_list])

def date_int(formater = '%H%M'):
    a = datetime.datetime.now().strftime(formater)
    return int(a)
def date_weekday():
    return datetime.datetime.now().isoweekday()

def get_path(type_,plus_):
    _base = os.getcwd()
    _path = os.path.join(_base,type_+plus_)
    if not os.path.exists(_path):
        os.makedirs(_path)
    return _path+'/'

def utf_dict(d):
    _d = {}
    for k,v in d.items():
        if type(v)==type(''):
            _d[k] = v.decode('gbk')
        else:
            _d[k] = v
    return _d

def print_dict(d):
    """打印API收到的字典，该函数主要用于开发时的debug"""
    print '-'*60
    l = d.keys()
    l.sort()
    for key in l:
        print key, ':', d[key]

'''如果有需要更多信息，自行修改下面的tick_key_list和info_key_list并把键对应到settings_ctp中
from tick..........

InstrumentID
TradingDay
UpperLimitPrice
LowerLimitPrice
Volume
OpenPrice
HighestPrice
LowestPrice
PreClosePrice
LastPrice

from info..........

InstrumentName      i
ProductID           i
ExchangeID          i
ExpireDate          i
VolumeMultiple      i
ShortMarginRatio    i
LongMarginRatio     i
PriceTick           i
'''

tick_key_list = [InstrumentID,TradingDay,UpperLimitPrice,LowerLimitPrice,Volume,OpenPrice,HighestPrice,LowestPrice,PreClosePrice,LastPrice]
info_key_list = [InstrumentName,ProductID,ExchangeID,ExpireDate,VolumeMultiple,ShortMarginRatio,LongMarginRatio,PriceTick]

class ctpMdApi(MdApi):

    #----------------------------------------------------------------------
    def __init__(self, ee, userid):
        """
        API对象的初始化函数
        """

        super(ctpMdApi, self).__init__()

        self.__eventEngine = ee

        self.next_login = 0

        self.__userid = userid
        user_info = apm.get_account(userid,other_info_dict={'name':'md_%s'%userid})
        self.__password = user_info['password']
        self.__brokerid = user_info['brokerid']
        self.__address = user_info['md']


        self.reSub = []
        self.reSub_timer = 0
        self.reSub_count = 0

        self.on_line = False
        self.plus_path = num2string(self.__userid+self.__brokerid)
        self.connect_server()

    # ----------------------------------------------------------------------
    def set_tradingday(self,_day):
        self.tradingDay = _day
    def close(self):
        self.on_line = False
        self.exit()
    def connect_server(self,fake=False):
        self.symbolInfo = {}
        for one in list(conn[BASE_DB][INSTRUMENT_DB].find()):
            self.symbolInfo[one[InstrumentID]] = {}
            for _key in info_key_list:
                if _key in one:
                    self.symbolInfo[one[InstrumentID]][_key] = one[_key]
                else:
                    logger.error(u'<font color="red">合约%s未发现%s信息</font>'%(one[InstrumentID],_key))
            self.symbolInfo[one[InstrumentID]][IsMaster] = one.get(IsMaster,0)
        logger.error(u'<font color="blue">账户%s的行情接口填充合约信息 共%d个</font>'%(self.__userid,len(self.symbolInfo)))
        self.__reqid = 0
        self.volCache = {}
        self.priceCache = {}
        self.timeoutCache = {}

        self.__setSubscribed = set()
        # 初始化.con文件的保存目录为\mdconnection，注意这个目录必须已存在，否则会报错
        self.createFtdcMdApi(get_path('md',self.plus_path))
        # 注册服务器地址
        self.registerFront(self.__address)
        # 初始化连接，成功会调用onFrontConnected
        self.init()
        logger.error(u'<font color="grey">账户%s连接柜台[md]</font>' % self.__userid)

    #----------------------------------------------------------------------

    def login(self):
        """连接服务器"""
        req = {}
        req['UserID'] = self.__userid
        req['Password'] = self.__password
        req['BrokerID'] = self.__brokerid
        req['UserProductInfo'] = CTP_PRODUCT_INFO
        req['AuthCode'] = CTP_AUTH_CODE
        self.__reqid = self.__reqid + 1
        _date_int = date_int()
        if time() > self.next_login:
            self.next_login = time()+60
            if 1530 > _date_int > 800 or 230 > _date_int or _date_int > 2000 and date_weekday() < 6:
                self.reqUserLogin(req, self.__reqid)
                logger.error(u'<font color="grey">账户%s发起登陆[md]</font>'%self.__userid)
    def onFrontConnected(self):
        """服务器连接"""
        self.on_line = True
        self.login()

    #----------------------------------------------------------------------
    def onFrontDisconnected(self, n):
        """服务器断开"""
        self.on_line = False
        logger.error(u'<font color="red">账户%s断开柜台[md]</font>' % self.__userid)
        _date_int = date_int()
        if 1530 > _date_int > 800 or 230 > _date_int or _date_int > 2000 and date_weekday()<6:
            pass
        else:
            sleep(60)
    #----------------------------------------------------------------------
    def onHeartBeatWarning(self, n):
        """心跳报警"""
        # 因为API的心跳报警比较常被触发，且与API工作关系不大，因此选择忽略
        pass

    #----------------------------------------------------------------------
    def onRspError(self, error, n, last):
        """错误回报"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[md.onRspError]</font>' % error)

    #----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""

        if error['ErrorID'] == 0:
            self.tradingDay = data[TradingDay]
            for instrument in self.__setSubscribed:
                self.subscribeMarketData(instrument[0])
            logger.error(u'<font color="blue">账户%s登陆成功[md]</font>' % self.__userid)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[md.onRspUserLogin]</font>' % error)

    #----------------------------------------------------------------------
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""

        if error['ErrorID'] == 0:
            logger.error(u'<font color="red">账户%s登出[md]</font>' % self.__userid)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[md.onRspUserLogout]</font>' % error)

    #----------------------------------------------------------------------
    def onRspSubMarketData(self, data, error, n, last):
        """订阅合约回报"""
        # 通常不在乎订阅错误，选择忽略
        pass

    #----------------------------------------------------------------------
    def onRspUnSubMarketData(self, data, error, n, last):
        """退订合约回报"""
        # 同上
        pass

    def check_reSub(self):
        if not self.reSub and self.reSub_count<10:
            self.reSub_count += 1
            self.reSub = list(self.__setSubscribed)
            logger.error(u'<font color="grey">账户%s第%d次订阅确认</font>'%(self.__userid,self.reSub_count))
        if self.reSub:
            this = self.reSub.pop(0)
            self.subscribeMarketData(str(this[0]))
    #----------------------------------------------------------------------
    def onRtnDepthMarketData(self, data):
        """行情推送"""
        # 行情推送收到后，同时触发常规行情事件，以及特定合约行情事件，用于满足不同类型的监听
        # 常规行情事件
        if ' ' in data['InstrumentID']:return
        _date_int = date_int()
        if 230 < _date_int < 900 or 1300 > _date_int > 1130 or 2100 > _date_int > 1515:
                return
        if _date_int in [1015,1300,1500,1515,2300,2330,100,230]:
            self.timeoutCache = {}

        if time()-self.reSub_timer>1:
            self.reSub_timer = time()
            self.check_reSub()

        _instrumentid = data[InstrumentID]
        _dict = {}
        for _key in tick_key_list:
            _dict[_key] = data[_key]
        _dict.update(self.symbolInfo.get(_instrumentid, {}))
        _dict['TradingDay'] = self.tradingDay
        _dict['Timer'] = time()
        _dict['Account'] = self.__userid

        if _dict.get(IsMaster,0) == Master_Level and time()>self.timeoutCache.get(_instrumentid,0):
            self.timeoutCache[_instrumentid] = time()+1
            if time()-min(self.timeoutCache.values()) > 100:
                _list = [(x[1],x[0]) for x in self.timeoutCache.items()]
                _list.sort()
                _resub = _list[0][1]
                self.subscribeMarketData(str(_resub))
                logger.error(u'<font color="grey">%s重新订阅%s</font>'%(self.__userid,_resub))
                self.timeoutCache[_resub] = time()
        if self.priceCache.get(_instrumentid,.0) != _dict[LastPrice]:
            if self.volCache.get(_instrumentid,0) < _dict[Volume]:
                if _dict[LastPrice]>0 and _dict[AskPrice]>0 and _dict[BidPrice]>0 and _dict[HighestPrice]>0 and _dict[LowestPrice]>0:
                    self.volCache[_instrumentid] = _dict[Volume]
                    self.priceCache[_instrumentid] = _dict[LastPrice]
                    event = Event(type_=EVENT_TICK)
                    event.dict_['data'] = _dict
                    self.__eventEngine.put(event)

    #----------------------------------------------------------------------
    def onRspSubForQuoteRsp(self, data, error, n, last):
        """订阅期权询价"""
        pass

    #----------------------------------------------------------------------
    def onRspUnSubForQuoteRsp(self, data, error, n, last):
        """退订期权询价"""
        pass

    #----------------------------------------------------------------------
    def onRtnForQuoteRsp(self, data):
        """期权询价推送"""
        pass
    #----------------------------------------------------------------------
    def subscribe(self, instrumentid, master_level):
        """订阅合约"""
        _productid = self.symbolInfo[instrumentid][ProductID]
        _exchangeid = self.symbolInfo[instrumentid][ExchangeID]
        if _productid not in PRODUCT_NO_SUB:
            self.symbolInfo[instrumentid][IsMaster] = master_level
            self.__setSubscribed.add((instrumentid,_exchangeid))
            self.subscribeMarketData(str(instrumentid))
    #----------------------------------------------------------------------
    def unsubscribe(self, instrumentid, exchangeid):
        """取消订阅合约"""
        pass


########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
class ctpTdApi(TdApi):

    #----------------------------------------------------------------------
    def __init__(self, ee, userid):
        """API对象的初始化函数"""
        super(ctpTdApi, self).__init__()

        self.__eventEngine = ee

        self.next_login = 0

        self.__userid = userid
        user_info = apm.get_account(userid,other_info_dict={'name':'td_%s'%userid})
        self.__password = user_info['password']
        self.__brokerid = user_info['brokerid']
        self.__address = user_info['td']

        self.on_line = False
        self.plus_path = num2string(self.__userid+self.__brokerid)

        self.Position_version = int(time())
        self.Client_version = str(int(time()))

        self.connect_server()

    def close(self):
        self.on_line = False
        self.exit()

    def connect_server(self,fake=False):
        # 请求编号，由api负责管理
        self.__reqid = 0

        # 报单编号，由api负责管理
        self.__orderref = 0

        # 合约字典（保存合约查询数据）
        self.__dictInstrument = {}

        # 初始化.con文件的保存目录为\tdconnection
        self.createFtdcTraderApi(get_path('td',self.plus_path))
        # 数据重传模式设为2
        #      2 : QUICK
        self.subscribePrivateTopic(2)
        self.subscribePublicTopic(2)
        # 注册服务器地址
        self.registerFront(self.__address)

        # 初始化连接，成功会调用onFrontConnected
        self.init()

        logger.error(u'<font color="grey">账户%s连接柜台[td]</font>' % self.__userid)

    # ----------------------------------------------------------------------
    def onFrontConnected(self):
        """服务器连接"""

        self.login()

    #----------------------------------------------------------------------

    def login(self):
        """连接服务器"""
        req = {}
        req['UserID'] = self.__userid
        req['Password'] = self.__password
        req['BrokerID'] = self.__brokerid
        req['UserProductInfo'] = CTP_PRODUCT_INFO
        req['AuthCode'] = CTP_AUTH_CODE
        self.__reqid = self.__reqid + 1
        _date_int = date_int()
        if time() > self.next_login:
            self.next_login = time()+60
            if 1530 > _date_int > 800 or 230 > _date_int or _date_int > 2000 and date_weekday() < 6:
                self.reqUserLogin(req, self.__reqid)
                logger.error(u'<font color="grey">账户%s发起登陆[td]</font>'%self.__userid)

    # ----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        if error['ErrorID'] == 0:
            self.tradingDay = data[TradingDay]
            if data['MaxOrderRef']:
                self.__orderref = int(data['MaxOrderRef'])
            else:
                self.__orderref = 1
            self.__frontid = data['FrontID']
            self.__sessionid = data['SessionID']
            self.__clientid = ''
            self.getSettlement()  # 登录完成后立即查询结算信息
            logger.error(u'<font color="blue">账户%s登陆成功[td]</font>' % self.__userid)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspUserLogin]</font>' % error)

    #----------------------------------------------------------------------
    def getSettlement(self):
        """查询结算信息"""
        self.__reqid = self.__reqid + 1

        req = {}
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid

        self.reqQrySettlementInfo(req, self.__reqid)

    def onRspQrySettlementInfo(self, data, error, n, last):
        """查询结算信息回报"""
        if last:
            self.confirmSettlement()    # 查询完成后立即确认结算信息

    #----------------------------------------------------------------------
    def confirmSettlement(self):
        """确认结算信息"""

        self.__reqid = self.__reqid + 1

        req = {}
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid

        self.reqSettlementInfoConfirm(req, self.__reqid)

        logger.error(u'<font color="blue">账户%s确认结算单[td]</font>' % self.__userid)

    #----------------------------------------------------------------------
    def onRspSettlementInfoConfirm(self, data, error, n, last):
        """确认结算信息回报"""
        if last:
            self.getInstrument()

    #----------------------------------------------------------------------
    def getInstrument(self):
        """查询合约"""
        self.__reqid = self.__reqid + 1
        self.reqQryInstrument({}, self.__reqid)
        logger.error(u'<font color="blue">账户%s获取合约信息[td]</font>' % self.__userid)

    # ----------------------------------------------------------------------
    def onRspQryInstrument(self, data, error, n, last):
        """
        合约查询回报
        由于该回报的推送速度极快，因此不适合全部存入队列中处理，
        选择先储存在一个本地字典中，全部收集完毕后再推送到队列中
        （由于耗时过长目前使用其他进程读取）
        """
        if error['ErrorID'] == 0:
            if '&' not in data['InstrumentID'] and data['InstrumentID'][-1].isdigit():
                event = Event(type_=EVENT_INSTRUMENT)
                event.dict_['data'] = utf_dict(data)
                self.__eventEngine.put(event)
            if last:
                self.on_line = True
                event = Event(type_=EVENT_TDLOGIN)
                self.__eventEngine.put(event)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspQryInstrument]</font>' % error)

    #----------------------------------------------------------------------
    def onFrontDisconnected(self, n):
        """服务器断开"""

        self.on_line = False
        logger.error(u'<font color="red">账户%s断开柜台[td]</font>' % self.__userid)
        _date_int = date_int()
        if 1530 > _date_int > 800 or 230 > _date_int or _date_int > 2000 and date_weekday()<6:
            pass
        else:
            sleep(60)
    #----------------------------------------------------------------------
    def onHeartBeatWarning(self, n):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspAuthenticate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""

        if error['ErrorID'] == 0:
            logger.error(u'<font color="red">账户%s登出[td]</font>' % self.__userid)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspUserLogout]</font>' % error)


    #----------------------------------------------------------------------
    def onRspUserPasswordUpdate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspTradingAccountPasswordUpdate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspOrderInsert(self, data, error, n, last):
        """发单错误（柜台）"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspOrderInsert]</font>' % error)

    #----------------------------------------------------------------------
    def onRspParkedOrderInsert(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspParkedOrderAction(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspOrderAction(self, data, error, n, last):
        """撤单错误（柜台）"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspOrderAction]</font>' % error)

    #----------------------------------------------------------------------
    def onRspQueryMaxOrderVolume(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspRemoveParkedOrder(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspRemoveParkedOrderAction(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspExecOrderInsert(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspExecOrderAction(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspForQuoteInsert(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQuoteInsert(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQuoteAction(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryOrder(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryTrade(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryTradingCode(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryInstrumentMarginRate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryExchange(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryProduct(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryDepthMarketData(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryTransferBank(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryInvestorPositionDetail(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryNotice(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQrySettlementInfoConfirm(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryInvestorPositionCombineDetail(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryCFMMCTradingAccountKey(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryEWarrantOffset(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryInvestorProductGroupMargin(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryExchangeMarginRate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryExchangeMarginRateAdjust(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryExchangeRate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQrySecAgentACIDMap(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryOptionInstrTradeCost(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryOptionInstrCommRate(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryExecOrder(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryForQuote(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryQuote(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryTransferSerial(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryAccountregister(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnInstrumentStatus(self, data):
        """"""
#        print('onRtnInstrumentStatus',data)
        pass

    #----------------------------------------------------------------------
    def onRtnTradingNotice(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnErrorConditionalOrder(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnExecOrder(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnExecOrderInsert(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnExecOrderAction(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnForQuoteInsert(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnQuote(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnQuoteInsert(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnQuoteAction(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnForQuoteRsp(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryContractBank(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryParkedOrder(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryParkedOrderAction(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryTradingNotice(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryBrokerTradingParams(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQryBrokerTradingAlgos(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnFromBankToFutureByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnFromFutureToBankByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromBankToFutureByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromFutureToBankByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnFromBankToFutureByFuture(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnFromFutureToBankByFuture(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromBankToFutureByFutureManual(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromFutureToBankByFutureManual(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnQueryBankBalanceByFuture(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnBankToFutureByFuture(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnFutureToBankByFuture(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnRepealBankToFutureByFutureManual(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnRepealFutureToBankByFutureManual(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onErrRtnQueryBankBalanceByFuture(self, data, error):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromBankToFutureByFuture(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnRepealFromFutureToBankByFuture(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspFromBankToFutureByFuture(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspFromFutureToBankByFuture(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspQueryBankAccountMoneyByFuture(self, data, error, n, last):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnOpenAccountByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnCancelAccountByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRtnChangeAccountByBank(self, data):
        """"""
        pass

    #----------------------------------------------------------------------
    def onRspError(self, error, n, last):
        """错误回报"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspError]</font>' % error)
    #----------------------------------------------------------------------
    def onRtnOrder(self, data):
        """报单回报"""
        # 更新最大报单编号
        newref = data['OrderRef']
        self.__orderref = max(self.__orderref, int(newref))

        # 常规报单事件
        event1 = Event(type_=EVENT_ORDER)
        _data = utf_dict(data)
        _data['client_version'] = self.Client_version
        if self.__frontid == data['FrontID'] and self.__sessionid == data['SessionID']:
            _clientid = data['ClientID']
            _data['_this_'] = 1
            if self.__clientid != _clientid:
                print('change ClientID from',self.__clientid,'to',_clientid,'onRtnOrder@ctpApi')
                self.__clientid = _clientid
        else:
            _data['_this_'] = 0
        event1.dict_['data'] = _data
        event1.symbol = _data['InstrumentID']
        self.__eventEngine.put(event1)

    #----------------------------------------------------------------------
    def onRtnTrade(self, data):
        """成交回报"""
        # 常规成交事件
        _clientid = data['ClientID']
        event1 = Event(type_=EVENT_TRADE)
        _data = utf_dict(data)
        _data['client_version'] = self.Client_version
        if _clientid == self.__clientid:
            _data['_this_'] = 1
        else:
            _data['_this_'] = 0
        event1.dict_['data'] = _data
        event1.symbol = _data['InstrumentID']
        self.__eventEngine.put(event1)

    #----------------------------------------------------------------------
    def onErrRtnOrderInsert(self, data, error):
        """发单错误回报（交易所）"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td]</font>' % error)

    #----------------------------------------------------------------------
    def onErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        error['account'] = self.__userid
        logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td]</font>' % error)

    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        if self.on_line:
            self.__reqid = self.__reqid + 1
            self.reqQryTradingAccount({}, self.__reqid)

    #----------------------------------------------------------------------
    def getInvestor(self):
        """查询投资者"""
        if self.on_line:
            self.__reqid = self.__reqid + 1
            self.reqQryInvestor({}, self.__reqid)

    #----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        if self.on_line:
            self.__reqid = self.__reqid + 1
            req = {}
            req['BrokerID'] = self.__brokerid
            req['InvestorID'] = self.__userid
            self.reqQryInvestorPosition(req, self.__reqid)

    #----------------------------------------------------------------------
    def getCommissionRate(self,req):
        if self.on_line:
            self.__reqid = self.__reqid + 1
            self.reqQryInstrumentCommissionRate(req, self.__reqid)

    #----------------------------------------------------------------------
    def onRspQryInstrumentCommissionRate(self, data, error, n, last):
        """CommissionRate for InstrumentID"""
        if data[InstrumentID]:
            event = Event(type_=EVENT_COMMISSION)
            data['account'] = self.__userid
            event.dict_['data'] = data
            self.__eventEngine.put(event)
        if last:
            event1 = Event(type_=EVENT_COMMISSION_END)
            data['account'] = self.__userid
            event1.dict_['data'] = data
            self.__eventEngine.put(event1)

    #----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction, offset):
        """发单"""
        if not self.on_line:return
        print(self.__userid,instrumentid,exchangeid,price,pricetype,volume,direction,offset,'ctpApi.sendOrder')
        self.__reqid = self.__reqid + 1
        req = {}
        req['InstrumentID'] = str(instrumentid)
        req['OrderPriceType'] = pricetype
        req['LimitPrice'] = price
        req['VolumeTotalOriginal'] = volume
        req['Direction'] = direction
        req['CombOffsetFlag'] = offset

        self.__orderref = self.__orderref + 1
        req['OrderRef'] = str(self.__orderref)

        req['InvestorID'] = self.__userid
        req['UserID'] = self.__userid
        req['BrokerID'] = self.__brokerid
        req['CombHedgeFlag'] = defineDict['THOST_FTDC_HF_Speculation']       # 投机单
        req['ContingentCondition'] = defineDict['THOST_FTDC_CC_Immediately'] # 立即发单
        req['ForceCloseReason'] = defineDict['THOST_FTDC_FCC_NotForceClose'] # 非强平
        req['IsAutoSuspend'] = 0                                             # 非自动挂起
        req['TimeCondition'] = defineDict['THOST_FTDC_TC_IOC']               #
        req['VolumeCondition'] = defineDict['THOST_FTDC_VC_AV']              # 任意成交量
        req['MinVolume'] = 1                                                 # 最小成交量为1

        self.reqOrderInsert(req, self.__reqid)

        return self.__orderref,self.Client_version

    #----------------------------------------------------------------------
    def cancelOrder(self, instrumentid, exchangeid, orderref):
        """撤单"""
        if not self.on_line:return
        self.__reqid = self.__reqid + 1
        req = {}

        req['InstrumentID'] = instrumentid
        req['ExchangeID'] = exchangeid
        req['OrderRef'] = orderref
        req['FrontID'] = self.__frontid
        req['SessionID'] = self.__sessionid

        req['ActionFlag'] = defineDict['THOST_FTDC_AF_Delete']
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid

        self.reqOrderAction(req, self.__reqid)

    #----------------------------------------------------------------------
    def onRspQryInvestorPosition(self, data, error, n, last):
        """持仓查询回报"""
        if error['ErrorID'] == 0:
            _data   = utf_dict(data)
            _dir    = _data['PosiDirection']
            _date   = _data['PositionDate']
            _vol    = _data['Position']
            _symbol = _data['InstrumentID']

            _d = {}
            _d['InstrumentID'] = _symbol
            _d['PosiDirection'] = _dir
            _d['PositionDate'] = _date
            _d['Position'] = _vol
            _d['vsn'] = self.Position_version
            if last:
                _d['last'] = 1
                self.Position_version = date_int(formater='%H%M%S')
            else:
                _d['last'] = 0

            event = Event(type_=EVENT_POSITION)
            event.dict_['data'] = _d
            self.__eventEngine.put(event)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspQryInvestorPosition]</font>' % error)

    #----------------------------------------------------------------------
    def onRspQryTradingAccount(self, data, error, n, last):
        """资金账户查询回报"""
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_ACCOUNT)
            event.dict_['data'] = utf_dict(data)
            self.__eventEngine.put(event)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspQryTradingAccount]</font>' % error)

    #----------------------------------------------------------------------
    def onRspQryInvestor(self, data, error, n, last):
        """投资者查询回报"""
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_INVESTOR)
            event.dict_['data'] = utf_dict(data)
            self.__eventEngine.put(event)
        else:
            error['account'] = self.__userid
            logger.error(u'<font color="red">账户%(account)s报错%(ErrorID)s%(ErrorMsg)s[td.onRspQryInvestor]</font>' % error)

