from base import *
from life import *
import time
from urllib2 import urlopen



# You Can Change Below

exchange = 'SHFE'

symbol = 'IF'

# You Can't Change Below!!!



names = 'raw_%s_%s_run'%(exchange,symbol)

_plus = 'rebuild'
_old = 'k_%s_%s_%s'%(exchange,symbol,_plus)

TimeStamp = 0*24*3600*21
db = conn[names]['raw']
n = 100
cnt = 0
conn.drop_database(_old)
while(n>=100):
	rs = list(db.find({},sort=[('time',asc)],limit=n,skip=cnt*n))
	n = len(rs)
	print(n*cnt)
	for one in rs:
		pp = Base(exchange,symbol,conn,allstate,plus=_plus)
		pp.account_money(float(0.0))
		pp.new_price(one['_time']+TimeStamp,one['point'],one['price'])
		pp.get_result()
	cnt+=1
	time.sleep(1)