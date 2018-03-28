# encoding: UTF-8

class AccountPasswordManager:

    def __init__(self):
        self.Server_Dict = {}
        self.Server_Dict['future_shanghai'] = {'md':'tcp://123.123.123.123:1234','td':'tcp://234.234.234.234:2345','brokerid':'1234'}
        self.Account_Dict = {}
        self.Account_Dict['user1234'] = {'name':u'测试用户','account':'12345678','password':'future','server':'future_shanghai'}

    def get_account(self,account_id,other_info_dict = {}):
        if account_id in self.Account_Dict:
            _d = self.Account_Dict[account_id]
            _server = _d.get('server','none')
            if _server in self.Server_Dict:
                _d['td'] = self.Server_Dict[_server]['td']
                _d['md'] = self.Server_Dict[_server]['md']
                _d['brokerid'] = self.Server_Dict[_server]['brokerid']
            _d.update(other_info_dict)
            return _d
        else:
            print(u'账户管理器未发现账户 %s'%account_id)
            return {}

AccountPasswordManager_Version = '2018-03-31'

print(u'账户管理器加载完成 版本:%s'%AccountPasswordManager_Version)