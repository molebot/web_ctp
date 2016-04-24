from page import *
from log import *
import time
time.sleep(1)

logit('begin page')
bottle.run( host='0.0.0.0', port=80)
