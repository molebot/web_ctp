import sys
from log import logit
from settings import *
from dom import dictomongo as dom
from pymongo import MongoClient
from pymongo import ASCENDING as asc
from pymongo import DESCENDING as desc
from bson.json_util import loads as jsonload
from bson.json_util import dumps as jsondump
allstate = dom('states')
conn = MongoClient(host=mongo_server,port=27017)

def price2point(price,point,func):
    return func(price*(1+func(point)))*1000
