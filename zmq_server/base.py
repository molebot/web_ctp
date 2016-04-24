vsn = 'in.2015.12.28.0'
import time,datetime
from life import *
from log import *
from svgcandle import *
from cmath import log as mathclog
from qqmail import alertmail
import thread
import acc

def mathlog(a):return mathclog(a).real

def clear_old(db,days):
    _time = time.time()-days*24*3600
    db.remove({'_time':{'$lt':_time}})

#=====================================================================
#=====================================================================

class Base:
    def __init__(self,exchange,symbol,dbConnection,dbState,plus='run'):
        self.symbol = "k_%s_%s_%s"%(exchange,symbol,plus)
        self.raw = "raw_%s_%s_%s"%(exchange,symbol,plus)
        self.plus = plus
        self.db = {}
        self.todo = ['3600']
        self.raw = dbConnection[self.raw]['raw']
        for i in self.todo:self.db[i] = dbConnection[self.symbol][i]
        _a = allstate[self.symbol]
        if _a:
            self.state = _a[0]
        else:
            self.state = {}
        self.hour = None
        self.cache = {}
        self.money = 0.0
#=====================================================================
    def get_timeframe(self):
        return self.todo
    def raw_tick(self):
        _result = self.raw.find(sort=[('_time',desc)],limit=100)
        return list(_result)
    def get_result(self,passit=1):
        c = self.cache
        s = self.state
        i = self.todo[0]
        
        _Max = 20
        _result = list(self.db[i].find({},sort=[('_id',desc)],limit=_Max))

        ma10 = sum([one['c'] for one in _result[:10]])/10.0
        ma20 = sum([one['c'] for one in _result[:20]])/20.0

        for one in self.todo:
            c[one][0]['ma10'] = ma10
            c[one][0]['ma20'] = ma20
            c[one][0]['point'] = s.get('point',c[one][0]['c'])
            self.cache[one][0] = c[one][0]
            self.save(one,c[one][0])
        if passit<1:return

        LS = s.get('ls',1)
        Real = s.get('real',0.0)
        Dead = s.get('dead',0)

        if ma10>ma20:
            LS2 = 1
        else:
            LS2 = -1

        _day_ = datetime.datetime.now()
        if LS2!=LS:
            s['ls'] = LS2
            _profit = LS*(self.realprice-Real)
            s['real'] = self.realprice
            s['point'] = c[i][0]['c']

            c[i][0]['_doit'] = 1
            self.cache[i][0] = c[i][0]
            self.save(i,c[i][0])

            if _day_.hour==9 and _day_.minute<30:
                s['dead'] = Dead = 0
                s['base_p']=0   #   profit
                s['base_c']=0   #   count
            elif _day_.hour==15:
                s['dead'] = Dead = 0
                s['base_p']=0
                s['base_c']=0
            else:
                s['dead'] = Dead = 1
                _p = s.get('base_p',0)
                if _p==0:
                    s['base_p'] = 0.0001
                    s['base_c'] = 0
                else:
                    s['base_p'] = _p+_profit-1
                    s['base_c'] = s.get('base_c',0)+1

        if _day_.hour==15 and _day_.minute>10:
            s['dead'] = Dead = 0
            s['base_p'] = 0
            s['base_c'] = 0
            closeit = 0
        else:
            closeit = 1

        out = {}
        out['result'] = LS2*Dead*closeit
        out['point'] = '%.1f'%s.get('base_p',0.0)

        if s.get('ss',0)!=LS2:
            time_str = _day_.strftime('%m.%d.%H:%M:%S')
            s['ss']=LS2
            _his = s.get('his',['none'])
            _his.append('%s#%.1f=%d@%.1f=%d'%(time_str,self.realprice,LS2,s.get('base_p',0),s.get('base_c',0)))
            s['his'] = _his[-26:]

        allstate[self.symbol] = self.state = s
        logit(str(out))
        return out

    def data_out(self,pos):
        _result = self.db[pos].find({'_do':1},sort=[('_id',desc)],limit=2)
        return jsondump(list(_result))
    def data_in(self,pos,_str):
        self.save(pos,jsonload(_str))
        print "save ok",pos
        return 'ok'
    def account_money(self,money):self.money = money
    def period_job(self):
        for one in self.todo:
            thread.start_new_thread(clear_old,(self.db[one],5))
        thread.start_new_thread(clear_old,(self.raw,30))
#        thread.start_new_thread(alertmail,("Account:%s_Eq:%.0f_Point:%.1f"%(acc.account,self.money,self.state.get("base_p",0.0)),))
    def get_image(self,pos,lens,group,offset=0):
        result = list(self.db[pos].find(sort=[('_id',desc)],limit=int(lens),skip=int(offset)*int(lens)))
        _l = self.state.get('his',['none'])[::-1]
        if len(result)<int(lens):
            result = result[:-1]
        out = SVG(group,result[::-1],_l).to_html()
        return out
    def only_image(self,pos,lens,group,offset=0):
        result = list(self.db[pos].find(sort=[('_id',desc)],limit=int(lens),skip=int(offset)*int(lens)))
        if len(result)<int(lens):
            result = result[:-1]
        out = SVG(group,result[::-1],[str(datetime.datetime.now())]).to_html()
        return out
    def save(self,Pos,Dict):
        self.db[Pos].save(Dict)
    def check_base(self,pos,_todo,_last):
        _todo['_do'] = 1
        self.save(pos,_todo)
        if _last:
            self.cache[pos] = [_todo,_last]
        else:
            self.cache[pos] = [_todo]
        self.get_result(passit=0)
        return _todo
    def check_k_period(self,now,last,timeframe):
        _hour = int(self.timer/int(timeframe))
        if now.get('_hour',0)!=_hour:
            p = now['c']
            new = {'o':p,'h':p,'l':p,'c':p,'_do':0,'_hour':_hour,'point':self.state.get('point',0)}
            new['_id'] = _hour*1000000
            new['_cnt'] = 0
            now = self.check_base(timeframe,now,last)

            if self.plus=='run':
#                logit("period_jod")
                self.period_job()
            return (new,now)
        return (now,last)
    def check_k_len(self,now,last,pos):
        length = self.state.get('length',8)
        if now['h']-now['o']>length:
            high = now['h']
            now['h'] = now['o']+length
            now['c'] = now['o']+length

            new = {'o':now['c'],'h':high,'l':now['c'],'c':now['c'],'_do':0,'_hour':now['_hour'],'point':self.state.get('point',now['c'])}
            new['_cnt'] = now.get('_cnt',0)+1
            new['_id'] = now['_id']+1

            now = self.check_base(pos,now,last)
            return self.check_k_len(new,now,pos)
        elif now['o']-now['l']>length:
            low = now['l']
            now['l'] = now['o']-length
            now['c'] = now['o']-length

            new = {'o':now['c'],'h':now['c'],'l':low,'c':now['c'],'_do':0,'_hour':now['_hour'],'point':self.state.get('point',now['c'])}
            new['_cnt'] = now.get('_cnt',0)+1
            new['_id'] = now['_id']+1

            now = self.check_base(pos,now,last)
            return self.check_k_len(new,now,pos)
        else:
            return (now,last)
    def do_price(self,timeframe,price):
        _result = list(self.db[timeframe].find({'_do':1},sort=[('_id',desc)],limit=2))
        if len(_result)>0:
            now = _result[0]
            if len(_result)>1:
                last = _result[1]
            else:
                last = None
            now['c'] = price
            now['h'] = max(now['c'],now['h'])
            now['l'] = min(now['c'],now['l'])
            now['_time'] = self.timer
            now['_do'] = 0
            now,last = self.check_k_len(now,last,timeframe)
            now,last = self.check_k_period(now,last,timeframe)
            self.check_base(timeframe,now,last)
        else:
            last = None
            now = {'_id':0,'_do':0,'o':price,'h':price,'l':price,'c':price,'_hour':0,'point':price}
            self.check_base(timeframe,now,last)
    def new_price(self,timer,price,realprice):
        self.timer = timer
        self.price = price
        self.realprice = realprice
        if self.plus == 'run':
            self.raw.save({"_time":timer,"point":price,"price":realprice})   #   save tick to raw
        for one in self.todo:
            self.do_price(one,price)
############################################################################################################
'''
#        end
'''
############################################################################################################
