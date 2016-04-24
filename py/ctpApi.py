# encoding: UTF-8
from vnctpmd import MdApi
from vnctptd import TdApi
from eventEngine import *
from ctp_data_type import defineDict
from thread import start_new_thread as th_fork
from copy import copy

# ----------------------------------------------------------------------

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


class ctpMdApi(MdApi):

    #----------------------------------------------------------------------
    def __init__(self, me, address, userid, password, brokerid, plus_path=""):
        """
        API对象的初始化函数
        """
        super(ctpMdApi, self).__init__()
        
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__me = me
        self.__eventEngine = me.ee
        
        # 请求编号，由api负责管理
        self.__reqid = 0
        self.cachePrice = False
        self.priceCache = {}

        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = userid
        self.__password = password
        self.__brokerid = brokerid
        self.__address = address
        # 以下集合用于重连后自动订阅之前已订阅的合约，使用集合为了防止重复
        self.__setSubscribed = set()

        self.plus_path = plus_path
        self.connect_server()

    # ----------------------------------------------------------------------

    def connect_server(self):
        # 初始化.con文件的保存目录为\mdconnection，注意这个目录必须已存在，否则会报错
        self.createFtdcMdApi('md%s'%self.plus_path)
        # 注册服务器地址
        self.registerFront(self.__address)
        # 初始化连接，成功会调用onFrontConnected
        self.init()

    # ----------------------------------------------------------------------

    def login(self):
        """连接服务器"""
        req = {}
        req['UserID'] = self.__userid
        req['Password'] = self.__password
        req['BrokerID'] = self.__brokerid
        self.__reqid = self.__reqid + 1
        self.reqUserLogin(req, self.__reqid)

    # ----------------------------------------------------------------------

    def onFrontConnected(self):
        """服务器连接"""

        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = u'行情服务器连接成功'
        self.__eventEngine.put(event)

        self.login()

    #----------------------------------------------------------------------
    def onFrontDisconnected(self, n):
        """服务器断开"""
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = u'行情服务器连接断开'
        self.__eventEngine.put(event)
        
    #----------------------------------------------------------------------
    def onHeartBeatWarning(self, n):
        """心跳报警"""
        # 因为API的心跳报警比较常被触发，且与API工作关系不大，因此选择忽略
        pass
    
    #----------------------------------------------------------------------   
    def onRspError(self, error, n, last):
        """错误回报"""
        event = Event(type_=EVENT_LOG)
        log = u'行情错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
        event1 = Event(type_=EVENT_ERROR)
        log = u'行情错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event1.dict_['log'] = log
        event1.dict_['ErrorID'] = unicode(error['ErrorID'])
        self.__eventEngine.put(event1)
    
    #----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        event = Event(type_=EVENT_LOG)
        
        if error['ErrorID'] == 0:
            log = u'行情服务器登陆成功'
        else:
            log = u'登陆回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        
        event1 = Event(type_=EVENT_MDLOGIN)
        self.__eventEngine.put(event1)
        ## 重连后自动订阅之前已经订阅过的合约
        for instrument in self.__setSubscribed:
            self.subscribe(instrument[0], instrument[1])
                
    #---------------------------------------------------------------------- 
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""
        event = Event(type_=EVENT_LOG)
        
        if error['ErrorID'] == 0:
            log = u'行情服务器登出成功'
        else:
            log = u'登出回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        
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
        
    #----------------------------------------------------------------------  
    def onRtnDepthMarketData(self, data):
        """行情推送"""
        # 行情推送收到后，同时触发常规行情事件，以及特定合约行情事件，用于满足不同类型的监听
        # 常规行情事件
        ask = data['AskPrice1']
        bid = data['BidPrice1']
        if not self.cachePrice or self.priceCache.get(data['InstrumentID'],())!=(ask,bid):
            self.priceCache[data['InstrumentID']] = (ask,bid)
            event1 = Event(type_=EVENT_TICK)
            event1.dict_['data'] = data
            event1.symbol = data['InstrumentID']
            self.__eventEngine.put(event1)
        
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
    def subscribe(self, instrumentid, exchangeid):
        """订阅合约"""
        event = Event(type_=EVENT_LOG)
        log = u'订阅合约: %s %s'%(instrumentid,exchangeid)
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        instrument = (instrumentid, exchangeid)
        self.__setSubscribed.add(instrument)
        self.subscribeMarketData(instrumentid)

    #----------------------------------------------------------------------
    def unsubscribe(self, instrumentid, exchangeid):
        """取消订阅合约"""
        event = Event(type_=EVENT_LOG)
        log = u'取消合约订阅: %s %s'%(instrumentid,exchangeid)
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        instrument = (instrumentid, exchangeid)
        if instrument in self.__setSubscribed:
            self.__setSubscribed.remove(instrument)
        self.unSubscribeMarketData(instrumentid)

        event = Event(type_=EVENT_TICK_CLEAR)
        event.dict_['InstrumentID'] = instrumentid
        self.__eventEngine.put(event)


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
    def __init__(self, me, address, userid, password, brokerid, plus_path=""):
        """API对象的初始化函数"""
        super(ctpTdApi, self).__init__()
        
        # 事件引擎，所有数据都推送到其中，再由事件引擎进行分发
        self.__me = me
        self.__eventEngine = me.ee
        
        # 请求编号，由api负责管理
        self.__reqid = 0
        
        # 报单编号，由api负责管理
        self.__orderref = 0
        
        # 以下变量用于实现连接和重连后的自动登陆
        self.__userid = userid
        self.__password = password
        self.__brokerid = brokerid
        self.__address = address
        
        # 合约字典（保存合约查询数据）
        self.__dictInstrument = {}

        self.plus_path = plus_path

        self.connect_server()
    
        self.dictPosition = {}  #   Position Status for all InstrumentID of This Account

    def connect_server(self):
        # 初始化.con文件的保存目录为\tdconnection
        self.createFtdcTraderApi('td%s'%self.plus_path)
        # 数据重传模式设为从开始
        #       QUICK
        self.subscribePrivateTopic(2)
        self.subscribePublicTopic(2)
        # 注册服务器地址
        self.registerFront(self.__address)
        # 初始化连接，成功会调用onFrontConnected
        self.init()

    # ----------------------------------------------------------------------

    def login(self):
        """连接服务器"""
        req = {}
        req['UserID'] = self.__userid
        req['Password'] = self.__password
        req['BrokerID'] = self.__brokerid
        self.__reqid = self.__reqid + 1
        self.reqUserLogin(req, self.__reqid)

    # ----------------------------------------------------------------------

    def onFrontConnected(self):
        """服务器连接"""
        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = u'交易服务器连接成功'
        self.__eventEngine.put(event)

        self.login()

    #----------------------------------------------------------------------
    def onFrontDisconnected(self, n):
        """服务器断开"""

        event = Event(type_=EVENT_LOG)
        event.dict_['log'] = u'交易服务器连接断开'
        self.__eventEngine.put(event)

    #----------------------------------------------------------------------
    def onHeartBeatWarning(self, n):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def onRspAuthenticate(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def onRspUserLogin(self, data, error, n, last):
        """登陆回报"""
        event = Event(type_=EVENT_LOG)
        if error['ErrorID'] == 0:
            log = u'交易服务器登陆成功'
            self.__orderref = int(data['MaxOrderRef'])
            self.__frontid = data['FrontID']
            self.__sessionid = data['SessionID']
            print(data)
        else:
            log = u'登陆回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        
        self.getSettlement()    # 登录完成后立即查询结算信息
    
    #----------------------------------------------------------------------
    def onRspUserLogout(self, data, error, n, last):
        """登出回报"""
        event = Event(type_=EVENT_LOG)
        
        if error['ErrorID'] == 0:
            log = u'交易服务器登出成功'
        else:
            log = u'登出回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
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
        event = Event(type_=EVENT_LOG)
        log = u' 发单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)   
    
        event1 = Event(type_=EVENT_ERROR)
        log = u' 发单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event1.dict_['log'] = log
        event1.dict_['ErrorID'] = int(error['ErrorID'])
        self.__eventEngine.put(event1)

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
        event = Event(type_=EVENT_LOG)
        log = u'撤单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
        event1 = Event(type_=EVENT_ERROR)
        log = u'撤单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event1.dict_['log'] = log
        event1.dict_['ErrorID'] = int(error['ErrorID'])
        self.__eventEngine.put(event1)

    #----------------------------------------------------------------------
    def onRspQueryMaxOrderVolume(self, data, error, n, last):
        """"""
        pass
    
    #----------------------------------------------------------------------
    def onRspSettlementInfoConfirm(self, data, error, n, last):
        """确认结算信息回报"""
        event = Event(type_=EVENT_LOG)
        log = u'结算信息确认完成'
        event.dict_['log'] = log
        self.__eventEngine.put(event)
        
        event = Event(type_=EVENT_TDLOGIN)
        self.__eventEngine.put(event)    
    
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
    def onRspQryInstrumentCommissionRate(self, data, error, n, last):
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
    def onRspQryInstrument(self, data, error, n, last):
        """
        合约查询回报
        由于该回报的推送速度极快，因此不适合全部存入队列中处理，
        选择先储存在一个本地字典中，全部收集完毕后再推送到队列中
        （由于耗时过长目前使用其他进程读取）
        """
        if error['ErrorID'] == 0:
            if data['InstrumentID'][-1].isdigit():
                event = Event(type_=EVENT_INSTRUMENT)
                event.dict_['data'] = utf_dict(data)
                event.dict_['last'] = last
                self.__eventEngine.put(event)
            else:
                print(u'ctpApi.mdapi.onRspQryInstrument:非常规合约 %s'%data['InstrumentID'])
                if last:
                    event = Event(type_=EVENT_INSTRUMENT)
                    event.dict_['data'] = {'InstrumentID':"None",'ProductID':"None",'ExchangeID':"None",'IsTrading':0}
                    event.dict_['last'] = last
                    self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = u'合约投资者回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)   
    
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
        event = Event(type_=EVENT_LOG)
        log = u'交易错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
        event1 = Event(type_=EVENT_ERROR)
        log = u'交易错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event1.dict_['log'] = log
        event1.dict_['ErrorID'] = unicode(error['ErrorID'])
        self.__eventEngine.put(event1)
    #----------------------------------------------------------------------
    def onRtnOrder(self, data):
        """报单回报"""
        # 更新最大报单编号
        newref = data['OrderRef']
        self.__orderref = max(self.__orderref, int(newref))
        
        # 常规报单事件
        event1 = Event(type_=EVENT_ORDER)
        _data = utf_dict(data)
        event1.dict_['data'] = _data
        event1.symbol = _data['InstrumentID']
        self.__eventEngine.put(event1)

    #----------------------------------------------------------------------
    def onRtnTrade(self, data):
        """成交回报"""
        # 常规成交事件
        event1 = Event(type_=EVENT_TRADE)
        _data = utf_dict(data)
        event1.dict_['data'] = _data
        event1.symbol = _data['InstrumentID']
        self.__eventEngine.put(event1)
        
    #----------------------------------------------------------------------
    def onErrRtnOrderInsert(self, data, error):
        """发单错误回报（交易所）"""
        event = Event(type_=EVENT_LOG)
        log = u'发单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def onErrRtnOrderAction(self, data, error):
        """撤单错误回报（交易所）"""
        event = Event(type_=EVENT_LOG)
        log = u'撤单错误回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
        event.dict_['log'] = log
        self.__eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def getInstrument(self):
        """查询合约"""
        self.__reqid = self.__reqid + 1
        self.reqQryInstrument({}, self.__reqid)
        
    #----------------------------------------------------------------------
    def getAccount(self):
        """查询账户"""
        self.__reqid = self.__reqid + 1
        self.reqQryTradingAccount({}, self.__reqid)
        
    #----------------------------------------------------------------------
    def getInvestor(self):
        """查询投资者"""
        self.__reqid = self.__reqid + 1
        self.reqQryInvestor({}, self.__reqid)
        
    #----------------------------------------------------------------------
    def getPosition(self):
        """查询持仓"""
        self.__reqid = self.__reqid + 1
        req = {}
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid
        self.reqQryInvestorPosition(req, self.__reqid)
        
    #----------------------------------------------------------------------
    def sendOrder(self, instrumentid, exchangeid, price, pricetype, volume, direction, offset):
        """发单"""
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
        
        # 返回订单号，便于某些算法进行动态管理
        return self.__orderref
    
    #----------------------------------------------------------------------
    def cancelOrder(self, instrumentid, exchangeid, orderref, frontid, sessionid):
        """撤单"""
        self.__reqid = self.__reqid + 1
        req = {}
        
        req['InstrumentID'] = instrumentid
        req['ExchangeID'] = exchangeid
        req['OrderRef'] = orderref
        req['FrontID'] = frontid
        req['SessionID'] = sessionid   
        
        req['ActionFlag'] = defineDict['THOST_FTDC_AF_Delete']
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid
        
        self.reqOrderAction(req, self.__reqid)
    
    #----------------------------------------------------------------------
    def onRspQrySettlementInfo(self, data, error, n, last):
        """查询结算信息回报"""
        if last:
            #print(str(datetime.now()),'td.onRspQrySettlementInfo')
            event = Event(type_=EVENT_LOG)
            log = u'结算信息查询完成'
            event.dict_['log'] = log
            self.__eventEngine.put(event)
            
            self.confirmSettlement()    # 查询完成后立即确认结算信息
    
    #----------------------------------------------------------------------
    def onRspQryInvestorPosition(self, data, error, n, last):
        """持仓查询回报"""
        if error['ErrorID'] == 0:
            _data   = utf_dict(data)
            _dir    = _data['PosiDirection']
            _date   = _data['PositionDate']
            _vol    = _data['Position']
            _symbol = _data['InstrumentID']
            
            if _symbol not in self.dictPosition:
                self.dictPosition[_symbol] = {}
            self.dictPosition[_symbol][(_dir,_date)] = _vol

            if last:
                def sent_position(ee,dict_):
                    for symbol,_dict in dict_.items():
                        event = Event(type_=EVENT_POSITION)
                        event.symbol = symbol
                        _dict['InstrumentID'] = symbol
                        event.dict_['data'] = _dict
                        ee.put(event)
                
                _dict = copy(self.dictPosition)
                th_fork(sent_position,(self.__eventEngine,_dict))
                self.dictPosition = {}
        else:
            event = Event(type_=EVENT_LOG)
            log = u'持仓查询回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def onRspQryTradingAccount(self, data, error, n, last):
        """资金账户查询回报"""
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_ACCOUNT)
            event.dict_['data'] = utf_dict(data)
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = u'账户查询回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)
    
    #----------------------------------------------------------------------
    def onRspQryInvestor(self, data, error, n, last):
        """投资者查询回报"""
        if error['ErrorID'] == 0:
            event = Event(type_=EVENT_INVESTOR)
            event.dict_['data'] = utf_dict(data)
            self.__eventEngine.put(event)
        else:
            event = Event(type_=EVENT_LOG)
            log = u'合约投资者回报，错误代码：' + unicode(error['ErrorID']) + u',' + u'错误信息：' + error['ErrorMsg'].decode('gbk')
            event.dict_['log'] = log
            self.__eventEngine.put(event)
            
    #----------------------------------------------------------------------
    def getSettlement(self):
        """查询结算信息"""
        self.__reqid = self.__reqid + 1
        req = {}
        
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid
        
        self.reqQrySettlementInfo(req, self.__reqid)
        
    #----------------------------------------------------------------------
    def confirmSettlement(self):
        """确认结算信息"""
        self.__reqid = self.__reqid + 1
        req = {}
        
        req['BrokerID'] = self.__brokerid
        req['InvestorID'] = self.__userid
        
        self.reqSettlementInfoConfirm(req, self.__reqid)    