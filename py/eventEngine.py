# encoding: UTF-8
from Queue import Queue, Empty
from threading import Thread
from time import sleep,time
from thread import start_new_thread as th_fork
from eventType import *
import json,shelve
import datetime as dt

class Event:
    #----------------------------------------------------------------------
    def __init__(self, type_=None):
        self.type_ = type_      # 事件类型
        self.dict_ = {}         # 字典用于保存具体的事件数据
########################################################################
class EventEngine:
    def __init__(self,account):
        """初始化事件引擎"""
        self.__account = account
        # 事件队列
        self.__queue = Queue()

        # 事件引擎开关
        self.__active = False
        self.__maxStep = 60

        # 事件处理线程
        self.__thread = Thread(target = self.__run)
        
        self.__handlers = {}
        self.__handlers_sync = {}

    #----------------------------------------------------------------------
    def __run(self):
        """引擎运行"""
        while self.__active == True:
            try:
                event = self.__queue.get(block = True, timeout = 10)  # 获取事件的阻塞时间设为10秒
                self.__process(event)
            except Empty:
                event = Event(type_=EVENT_LOG)
                log = 'Empty Queue'
                event.dict_['log'] = log
                self.put(event)
    #----------------------------------------------------------------------
    def __process(self, event):
        """处理事件"""
        # 检查是否存在对该事件进行监听的处理函数
        if time()-event.timer<self.__maxStep:
            if event.type_ in self.__handlers:
                #若存在，则按顺序将事件传递给处理函数执行
                for _h in self.__handlers[event.type_]:
            
                    if self.__handlers_sync[_h]:
                        _h(event)
                    else:
                        th_fork(_h,(event,))

    def start(self):
        """引擎启动"""
        # 将引擎设为启动
        self.__active = True
        
        # 启动事件处理线程
        self.__thread.start()
        
        # 启动计时器，计时器事件间隔默认设定为1秒
#        self.__timer.start(100)
    
    #----------------------------------------------------------------------
    def stop(self):
        """停止引擎"""
        # 将引擎设为停止
        self.__active = False
        
        # 等待事件处理线程退出
        self.__thread.join()
            
    #----------------------------------------------------------------------
    def register(self, type_, handler,_sync):
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
            self.__handlers_sync[handler] = _sync
            
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

        event.timer = time()
        event.dict_['_type_'] = event.type_
        event.dict_['_qsize_'] = self.__queue.qsize()
        event.dict_['_account_'] = self.__account.get('userid','NONE_USERID')

        self.__queue.put(event)


########################################################################
