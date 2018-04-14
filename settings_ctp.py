# encoding: UTF-8

#   账户设置
Account_Tick = {}
Account_Tick['user1234'] = {'name':u'user1234行情账户'}
Account_Tick['user2345'] = {'name':u'user2345行情账户'}

Account_Trade = {}
Account_Trade['user1234'] = {'name':u'user1234交易账户','trade':0,'margin_shift':{'a':0.0,'b':1.0,'c':0.0}}
'''
margin_shift用法
资金偏移，仓位计算要用

实际保证金为X
仓位计算保证金为Y

Y = ( X + a ) * b + c
'''


#   行情订阅黑名单
PRODUCT_NO_SUB = ['LR','bb','WH','b','RS','fb','CY','PM','RI','fu','wr','JR','SRP','SRC','m_o','cu_o','au_o','ag_o']

#   品种交易黑名单
PRODUCT_NO_TRADE = ['IF','IH','IC','TF','T','sc']

#   ctp终端命名
CTP_PRODUCT_INFO = 'molebot_web_ctp'
CTP_AUTH_CODE = ''

#   主力合约标识
Master_Level = 2

#   数据库设置
BASE_DB = 'ctpBase'
INSTRUMENT_DB = 'InstrumentDB'
ACCOUNT_DB = 'AccountDB'
POSITION_DB = 'PositionDB'

log_database = 'Log'
log_collection = 'logs'

#   字段命名
InstrumentID = 'InstrumentID'
InstrumentName = 'InstrumentName'
ProductID = 'ProductID'
ExchangeID = 'ExchangeID'
TradingDay = 'TradingDay'
UpperLimitPrice = 'UpperLimitPrice'
LowerLimitPrice = 'LowerLimitPrice'
Volume = 'Volume'
VolumeMultiple = 'VolumeMultiple'
ShortMarginRatio = 'ShortMarginRatio'
LongMarginRatio = 'LongMarginRatio'
PriceTick = 'PriceTick'
ExpireDate = 'ExpireDate'
AskPrice = 'AskPrice1'
BidPrice = 'BidPrice1'
OpenPrice = 'OpenPrice'
HighestPrice = 'HighestPrice'
LowestPrice = 'LowestPrice'
LastPrice = 'LastPrice'
PreClosePrice = 'PreClosePrice'
UpdateTime = 'UpdateTIme'
#带_为自定义值
OverDate = 'Over_Date'
AvgVolume = 'Avg_Volume'
IsMaster = 'Is_Master'

tick_key_list = [InstrumentID,TradingDay,UpperLimitPrice,LowerLimitPrice,Volume,OpenPrice,HighestPrice,LowestPrice,PreClosePrice,LastPrice,AskPrice,BidPrice,UpdateTime]
info_key_list = [InstrumentName,ProductID,ExchangeID,ExpireDate,VolumeMultiple,ShortMarginRatio,LongMarginRatio,PriceTick]
