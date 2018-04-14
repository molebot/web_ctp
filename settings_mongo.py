from pymongo import *
mongo_server='localhost'
mongo_port = 27017

asc = ASCENDING
desc = DESCENDING
conn = MongoClient(host=mongo_server,port=mongo_port)

