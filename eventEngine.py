# encoding: UTF-8
from Queue import Queue, Empty
from time import sleep,time
from threading import Thread
import datetime
from eventType import *
from settings_ctp import *
import traceback
from log import logger

class Event:
    #----------------------------------------------------------------------
    def __init__(self, type_=None):
        self.type_ = type_      # 事件类型
        self.dict_ = {'date':datetime.datetime.now(),'time':time(),'data':{}}         # 字典用于保存具体的事件数据
########################################################################

class EventEngine:
    def __init__(self,account):
        """初始化事件引擎"""
        self.__account = account
        # 事件队列
        self.__queue = Queue()

        # 事件引擎开关
        self.__active = False

        self.timer_timer = 0

        self.tick_cache = {}

        self.haveTodo = False
        self.isLocked = False

        # 事件处理线程
        self.__thread = Thread(target = self.__run)

        # 计时器，用于触发计时器事件
        self.__timer = Thread(target = self.__runTimer)
        self.__timerActive = False                      # 计时器工作状态
        self.__timerSleep = 1

        self.queue_timout = 1

        self.__handlers = {}

    #----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active:
            if time() - self.timer_timer > 1:
                self.timer_timer = time()
                event = Event(type_=EVENT_TIMER)
                event.dict_['data'] = {}
                event.dict_['data']['_name_'] = self.__account.get('name', '')
                event.dict_['data']['_account_'] = self.__account.get('account', '*')
                event.dict_['data']['_qsize_'] = self.__queue.qsize()
                event.dict_['_account_'] = self.__account.get('account', '*')
                event.dict_['_type_'] = self.__account.get('_type_', '*')
                self.__queue.put(event)
            try:
                event = self.__queue.get(block = True, timeout = self.queue_timout)  # 获取事件的阻塞时间设为10秒
                self.__process(event)
            except Empty:
                if self.haveTodo and not self.isLocked:
                    _ticks = [v for v in self.tick_cache.values()]
                    _ticks.sort()
                    _new = _ticks[-1]
                    _delta,_price,_nowprice,_inst,_event = _new
                    self.tick_cache[_inst] = (0,_nowprice,_nowprice,_inst,_event)
                    if _delta > 0:
                        self.__process(_event)
                    else:
                        self.tick_cache = {}
                        self.haveTodo = False
                        self.queue_timout = 1


    #----------------------------------------------------------------------
    def __runTimer(self):
        """运行在计时器线程中的循环函数"""
        while self.__timerActive:
            # 创建计时器事件
            event = Event(type_=EVENT_TIMER)

            if 'data' not in event.dict_:
                event.dict_['data'] = {}
            event.dict_['data']['_name_'] = self.__account.get('name','')
            event.dict_['data']['_account_'] = self.__account.get('account','*')
            event.dict_['data']['_qsize_'] = self.__queue.qsize()
            event.dict_['_account_'] = self.__account.get('account','*')
            event.dict_['_type_'] = self.__account.get('_type_','*')
            # 向队列中存入计时器事件
            if self.__active:
                self.__queue.put(event)

            # 等待
            sleep(self.__timerSleep)

    def __process(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if event.type_ in self.__handlers:
            #若存在，则按顺序将事件传递给处理函数执行
            for _h in self.__handlers[event.type_]:
                try:
                    _h(event)
                except:
                    logger.error(str(traceback.format_exc()))
    def start(self):
        """引擎启动"""
        # 将引擎设为启动
        self.__active = True

        # 启动事件处理线程
        self.__thread.start()

    #----------------------------------------------------------------------
    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False
        self.__timerActive = False
        # 等待事件处理线程退出
        self.__thread.join()

    #----------------------------------------------------------------------
    def register(self, type_, handler):
        """注册事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则创建
        try:
            handlerList = self.__handlers[type_]
        except KeyError:
            handlerList = []
            self.__handlers[type_] = handlerList

        # 若要注册的处理器不在该事件的处理器列表中，则注册该事件
        if handler not in handlerList:
            handlerList.append(handler)

    #----------------------------------------------------------------------
    def unregister(self, type_, handler):
        """注销事件处理函数监听"""
        # 尝试获取该事件类型对应的处理函数列表，若无则忽略该次注销请求
        try:
            handlerList = self.__handlers[type_]

            # 如果该函数存在于列表中，则移除
            if handler in handlerList:
                handlerList.remove(handler)

            # 如果函数列表为空，则从引擎中移除该事件类型
            if not handlerList:
                del self.__handlers[type_]
        except KeyError:
            pass

    #----------------------------------------------------------------------
    def put(self, event):
        """向事件队列中存入事件"""
        event.dict_['data']['_name_'] = self.__account.get('name','')
        event.dict_['data']['_account_'] = self.__account.get('account','*')
        event.dict_['data']['_qsize_'] = self.__queue.qsize()
        event.dict_['_account_'] = self.__account.get('account','*')
        event.dict_['_type_'] = self.__account.get('_type_','*')
        if self.__active and event.dict_['date'].hour in [8,9,10,11,12,13,14,15,20,21,22,23,0,1,2]:
            if event.type_ == EVENT_TICK:
                _inst = event.dict_['data'][InstrumentID]
                _price = event.dict_['data'][LastPrice]
                if _inst in self.tick_cache:
                    _old = self.tick_cache[_inst]
                    _delta = abs(_old[1]-_price)/_price
                    if _delta > 0:
                        _new = (_delta, _old[1], _price, _inst, event)
                        self.haveTodo = True
                        self.queue_timout = 0
                        self.isLocked = True
                        self.tick_cache[_inst] = _new
                        self.isLocked = False
                else:
                    _new = (0,_price,_price,_inst,event)
                    self.isLocked = True
                    self.tick_cache[_inst] = _new
                    self.isLocked = False
                    self.__queue.put(event)
            else:
                self.__queue.put(event)


########################################################################

def test():
    def show_timer(e):
        logger.error('show timer test')

    e = EventEngine({})
    e.register(EVENT_TIMER,show_timer)
    e.start()
