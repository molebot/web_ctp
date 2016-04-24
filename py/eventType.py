# encoding: UTF-8

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

