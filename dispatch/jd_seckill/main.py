from dispatch.jd_seckill import class_logger, class_MongoDB
from dispatch.jd_seckill import class_consign
from dispatch.jd_seckill import class_login
from dispatch.jd_seckill import class_presell
import base64
import random
import string
import time
from config.celery_config import MONGODB_SETTINGS as uri
from dispatch.jd_seckill.proxy_pool import ProxyStore


class jd_seckill_dispatch:

    def __init__(self):
        self.dbc = class_MongoDB.MongoClient(uri, class_logger.getLogger('MongoDB_Users'), 'JD')
        self.dbc.setUnique('Users', 'username')
        cl = class_logger
        cl.init()
        self.logger = cl.getLogger('Class_Login')

        # 连接池
        self.Ppool = ProxyStore.get_proxyPoolstores()

    def insertUsers(self, username, password):
        i = {
            "username": username,
            "password": password,
            "cookies": "",
            "last_refresh": 0,
            "last_pool": 0,
            "orders": {},
            "created_time": time.time(),
            "alive": 1,
            "eid":"",
            "fp":""
        }
        if self.dbc.isexisted('Users', {"username": i['username']}) == True:
            # self.logger.info('Unable to insert User, User existed')
            return i
        else:
            self.dbc.insert_one('Users', i)
            return i

    def jd_seckill_deal_user(self, username='13481316814', password='qweasd789'):
        # 保存用户
        user = self.insertUsers(username, password)

        self.Ppool.refreshpool()
        # 用户登录
        lg = class_login.Login()
        lret = lg.login(username, password, self.Ppool.getProxy())

        if lret['state'] == 200:
            user['eid'] = lret['eid']
            user['fp'] = lret['fp']
            user['last_refresh'] = time.time()
            user['cookies'] = lret['cookies']
            self.dbc.update('Users',{'username': user['username']}, user)
            self.logger.info('登录成功，username：'+username)
        else:
            user['alive'] = 0
            self.dbc.update('Users', {'username': user['username']}, user)
            self.logger.info('登录失败，username：' + username)
            return {"code": "Fail", "msg": '登录失败，username：' + username}

        Cookies = base64.b64decode(lret['cookies']).decode()

        # 检查用户是否登录 更新状态
        isLoginRet = lg.isLogin(Cookies, self.Ppool.getProxy())
        if lret['state'] == 200:
            self.dbc.update('Users', {'username': user['username']}, {'last_refresh': time.time()})
            self.logger.info('更新成功，username：' + username)
        else:
            self.dbc.update('Users', {'username': user['username']}, {'last_refresh': 0})
            self.logger.info('更新失败，username：' + username)
            return {"code": "Fail", "msg": '更新失败，username：' + username}

        # 提交收获地址
        cs = class_consign.Consign()
        addr_id = ''.join(random.sample(string.ascii_letters + string.digits, 8))
        cs.add(addr_id, Cookies, self.Ppool.getProxy())
        add = cs.getAddressList(Cookies, self.Ppool.getProxy())
        print(add)
        self.logger.info(add)
        cs.setOnekey(Cookies,add[1]['id'], self.Ppool.getProxy())

        # 预约抢购
        ps = class_presell.Presell()
        myPresell = ps.getMyPresell(Cookies, self.Ppool.getProxy())
        print(myPresell)
        self.logger.info(myPresell)

        psinfo = ps.goPresellInfo(Cookies,'5369028', self.Ppool.getProxy())
        print(psinfo)
        self.logger.info(psinfo)

        goPresell = ps.goPresell(Cookies,'5369028','https:' + psinfo['url'], self.Ppool.getProxy())
        print(goPresell)
        self.logger.info(goPresell)

        getMyPresell = ps.getMyPresell(Cookies, self.Ppool.getProxy())
        print(getMyPresell)
        self.logger.info(getMyPresell)

        return {"code": "Success", "msg": "抢购用户初始化成功"}