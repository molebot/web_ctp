from bson.timestamp import Timestamp
from pymongo import MongoClient as Connection
from pymongo.errors import AutoReconnect
import logging
from pymongo import ASCENDING as asc
from pymongo import DESCENDING as desc
from settings import mongo_server
"""
Example format of generated bson document:
{
    'thread': -1216977216,
    'level': 'ERROR',
    'timestamp': Timestamp(1290895671, 63),
    'message': 'test message',
    'fileName': '/var/projects/python/log4mongo-python/tests/test_mongo_handler.py',
    'lineNumber': 38,
    'method': 'test_emit_exception',
    'loggerName':  'testLogger',
    'exception': {
        'stackTrace': 'Traceback (most recent call last):
                       File "/var/projects/python/log4mongo-python/tests/test_mongo_handler.py", line 36, in test_emit_exception
                       raise Exception(\'exc1\')
                       Exception: exc1',
        'message': 'exc1',
        'code': 0
    }
}
"""

logging.LogRecord

class MongoFormatter(logging.Formatter):

    DEFAULT_PROPERTIES = logging.LogRecord('', '', '', '','', '', '', '').__dict__.keys()

    def format(self, record):
        """Formats LogRecord into python dictionary."""
        # Standard document
        document = {
            'timestamp': Timestamp(int(record.created), int(record.msecs)),
            'level': record.levelname,
            'thread': record.thread,
            'message': record.getMessage(),
            'loggerName': record.name,
            'fileName': record.pathname,
            'method': record.funcName,
            'lineNumber': record.lineno
        }
        # Standard document decorated with exception info
        if record.exc_info is not None:
            document.update({
                'exception': {
                    'message': str(record.exc_info[1]),
                    'code': 0,
                    'stackTrace': self.formatException(record.exc_info)
                }
            })
        # Standard document decorated with extra contextual information
        if len(self.DEFAULT_PROPERTIES) != len(record.__dict__):
            contextual_extra = set(record.__dict__).difference(set(self.DEFAULT_PROPERTIES))
            if contextual_extra:
                for key in contextual_extra:
                    document[key] = record.__dict__[key]
        return document


class MongoHandler(logging.Handler):

    def __init__(self, level=logging.NOTSET, host=mongo_server, port=27017, database_name='logs', collection='logs',
                 username=None, password=None, fail_silently=False, formatter=None):
        """Setting up mongo handler, initializing mongo database connection via pymongo."""
        logging.Handler.__init__(self, level)
        self.host = host
        self.port = port
        self.database_name = database_name
        self.collection_name = collection
        self.username = username
        self.password = password
        self.fail_silently = fail_silently
        self.connection = None
        self.db = None
        self.collection = None
        self.authenticated = False
        self.formatter = formatter or MongoFormatter()
        self._connect()

    def show(self,len=100,offset=0):
        return list(self.collection.find(sort=[('timestamp',desc)],limit=len,skip=offset*len))
        
    def _connect(self):
        """Connecting to mongo database."""

        try:
            self.connection = Connection(host=self.host, port=self.port)
        except AutoReconnect, e:
            if self.fail_silently:
                return
            else:
                raise AutoReconnect(e)

        self.db = self.connection[self.database_name]
        if self.username is not None and self.password is not None:
            self.authenticated = self.db.authenticate(self.username, self.password)
        if self.collection_name not in self.db.collection_names():
            self.db.create_collection(self.collection_name,size=512000000,capped=True,max=200)
        self.collection = self.db[self.collection_name]

    def close(self):
        """If authenticated, logging out and closing mongo database connection."""
        if self.authenticated:
            self.db.logout()
        if self.connection is not None:
            self.connection.close()

    def emit(self, record):
        """Inserting new logging record to mongo database."""
        if self.collection is not None:
            try:
                self.collection.save(self.format(record))
            except Exception:
                if not self.fail_silently:
                    self.handleError(record)