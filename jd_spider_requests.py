import random
import sys
import time
from jd_logger import logger
from timer import Timer
import requests
from util import parse_json, get_session, get_sku_title,send_wechat
from config import global_config
from concurrent.futures import ProcessPoolExecutor
from util import get_random_useragent


class JdSeckill(object):
    def __init__(self):
        # 初始化信息
        self.session = get_session()
        self.sku_id = global_config.getRaw('config', 'sku_id')
        self.seckill_num = 1
        self.seckill_init_info = dict()
        self.seckill_url = dict()
        self.seckill_order_data = dict()
        self.timers = Timer()
        self.default_user_agent = global_config.getRaw('config', 'DEFAULT_USER_AGENT')

    def reserve(self):
        """
        预约
        """
        self.__reserve()

    def seckill(self):
        """
        抢购
        """
        self.__seckill()

    def wati_some_time(self):
        time.sleep(random.randint(100, 300) / 1000)

    def seckill_by_proc_pool(self, work_count=5):
        """
        多进程进行抢购
        work_count：进程数量
        """
        with ProcessPoolExecutor(work_count) as pool:
            for i in range(work_count):
                pool.submit(self.seckill)

    def __reserve(self):
        """
        预约
        """
        self.login()
        while True:
            try:
                self.make_reserve()
            except Exception as e:
                logger.info('预约发生异常!', e)
            self.wati_some_time()

    def __seckill(self):
        """
        抢购
        """
        self.login()
        while True:
            try:
                self.request_seckill_url()
                self.request_seckill_checkout_page()
                self.submit_seckill_order()
            except Exception as e:
                logger.info('抢购发生异常，稍后继续执行！', e)
            self.wati_some_time()

    def login(self):
        for flag in range(1, 3):
            try:
                targetURL = 'https://order.jd.com/center/list.action'
                payload = {
                    'rid': str(int(time.time() * 1000)),
                }
                resp = self.session.get(
                    url=targetURL, params=payload, allow_redirects=False)
                if resp.status_code == requests.codes.OK:
                    logger.info('校验是否登录[成功]')
                    logger.info('用户:{}'.format(self.get_username()))
                    return True
                else:
                    logger.info('校验是否登录[失败]')
                    logger.info('请重新输入cookie')
                    time.sleep(1)
                    continue
            except Exception as e:
                logger.info('第【%s】次失败请重新获取cookie', flag)
                time.sleep(1)
                continue
        sys.exit(1)

    def make_reserve(self):
        """商品预约"""
        logger.info('商品名称:{}'.format(get_sku_title()))
        url = 'https://yushou.jd.com/youshouinfo.action?'
        payload = {
            'callback': 'fetchJSON',
            'sku': self.sku_id,
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://item.jd.com/{}.html'.format(self.sku_id),
        }
        resp = self.session.get(url=url, params=payload, headers=headers)
        resp_json = parse_json(resp.text)
        reserve_url = resp_json.get('url')
        print(reserve_url)
        self.timers.start()
        while True:
            try:
                get = self.session.get(url='https:' + reserve_url)
                logger.info('预约成功，已获得抢购资格 / 您已成功预约过了，无需重复预约')
                if global_config.getRaw('messenger', 'enable') == 'true':
                    success_message = "预约成功，已获得抢购资格 / 您已成功预约过了，无需重复预约"
                    send_wechat(success_message)
                break
            except Exception as e:
                logger.error('预约失败正在重试...')

    def get_username(self):
        """获取用户信息"""
        url = 'https://passport.jd.com/user/petName/getUserInfoForMiniJd.action'
        payload = {
            'callback': 'jQuery'.format(random.randint(1000000, 9999999)),
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Referer': 'https://order.jd.com/center/list.action',
        }

        resp = self.session.get(url=url, params=payload, headers=headers)

        try_count = 5
        while not resp.text.startswith("jQuery"):
            try_count = try_count - 1
            if try_count > 0:
                resp = self.session.get(url=url, params=payload, headers=headers)
            else:
                break
            self.wati_some_time()
        # 响应中包含了许多用户信息，现在在其中返回昵称
        # jQuery2381773({"imgUrl":"//storage.360buyimg.com/i.imageUpload/xxx.jpg","lastLoginTime":"","nickName":"xxx","plusStatus":"0","realName":"xxx","userLevel":x,"userScoreVO":{"accountScore":xx,"activityScore":xx,"consumptionScore":xxxxx,"default":false,"financeScore":xxx,"pin":"xxx","riskScore":x,"totalScore":xxxxx}})
        return parse_json(resp.text).get('nickName')

    def get_seckill_url(self):
        """获取商品的抢购链接
        点击"抢购"按钮后，会有两次302跳转，最后到达订单结算页面
        这里返回第一次跳转后的页面url，作为商品的抢购链接
        :return: 商品的抢购链接
        """
        url = 'https://itemko.jd.com/itemShowBtn'
        payload = {
            'callback': 'jQuery{}'.format(random.randint(1000000, 9999999)),
            'skuId': self.sku_id,
            'from': 'pc',
            '_': str(int(time.time() * 1000)),
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Host': 'itemko.jd.com',
            'Referer': 'https://item.jd.com/{}.html'.format(self.sku_id),
        }
        while True:
            resp = self.session.get(url=url, headers=headers, params=payload)
            resp_json = parse_json(resp.text)
            if resp_json.get('url'):
                # https://divide.jd.com/user_routing?skuId=8654289&sn=c3f4ececd8461f0e4d7267e96a91e0e0&from=pc
                router_url = 'https:' + resp_json.get('url')
                # https://marathon.jd.com/captcha.html?skuId=8654289&sn=c3f4ececd8461f0e4d7267e96a91e0e0&from=pc
                seckill_url = router_url.replace(
                    'divide', 'marathon').replace(
                    'user_routing', 'captcha.html')
                logger.info("抢购链接获取成功: %s", seckill_url)
                return seckill_url
            else:
                logger.info("抢购链接获取失败，稍后自动重试")
                self.wati_some_time()

    def request_seckill_url(self):
        """访问商品的抢购链接（用于设置cookie等"""
        logger.info('用户:{}'.format(self.get_username()))
        logger.info('商品名称:{}'.format(get_sku_title()))
        self.timers.start()
        self.seckill_url[self.sku_id] = self.get_seckill_url()
        logger.info('访问商品的抢购连接...')
        headers = {
            'User-Agent': self.default_user_agent,
            'Host': 'marathon.jd.com',
            'Referer': 'https://item.jd.com/{}.html'.format(self.sku_id),
        }
        self.session.get(
            url=self.seckill_url.get(
                self.sku_id),
            headers=headers,
            allow_redirects=False)

    def request_seckill_checkout_page(self):
        """访问抢购订单结算页面"""
        logger.info('访问抢购订单结算页面...')
        url = 'https://marathon.jd.com/seckill/seckill.action'
        payload = {
            'skuId': self.sku_id,
            'num': self.seckill_num,
            'rid': int(time.time())
        }
        headers = {
            'User-Agent': self.default_user_agent,
            'Host': 'marathon.jd.com',
            'Referer': 'https://item.jd.com/{}.html'.format(self.sku_id),
        }
        self.session.get(url=url, params=payload, headers=headers, allow_redirects=False)

    def _get_seckill_init_info(self):
        """获取秒杀初始化信息（包括：地址，发票，token）
        :return: 初始化信息组成的dict
        """
        logger.info('获取秒杀初始化信息...1')
        url = 'https://marathon.jd.com/seckillnew/orderService/init.action'
        data = {
            'sku': self.sku_id,
            'num': self.seckill_num,
            'id': 4553344744,
            'provinceId': 1,
            'cityId': 2901,
            'countyId': 55565,
            'townId': 0,
            # 'isModifyAddress': 'false',
        }
        headers = {
            'User-Agent': get_random_useragent(),
            'Host': 'marathon.jd.com',
            'Cookie': 'shshshfpa=a9ddc8a5-81e1-c01a-449d-d1092b7c8194-1637723122; shshshfpb=j1ruWzQtq3DjhNak5h7zz3A%3D%3D; __jdu=16599281313162050207785; areaId=1; ipLoc-djd=1-2802-0-0; pinId=rAnu0Cpjt5L6E1U9ceEJpQ; pin=523%E7%8E%8B%E5%88%9A; unick=u_s91w6nikweor; _tp=nOVpscyCes3%2BNp1X39xKAjFzMt2YX9emVILvj%2FeRV3w%3D; _pst=523%E7%8E%8B%E5%88%9A; user-key=61804443-7386-4a5d-9bb9-77ad05ce4845; unpl=JF8EAMlnNSttD0hRVxkBSBBASF9UW1kLSx5WODNQVVxQGFwNTgRIRkV7XlVdXhRKHx9vYBRUXFNPVw4bACsSEXteXVdZDEsWC2tXVgQFDQ8VXURJQlZAFDNVCV9dSRZRZjJWBFtdT1xWSAYYRRMfDlAKDlhCR1FpMjVkXlh7VAQrAhwWGENeXV5fCEkXBGxmAVVeWU1SDB8yKxUge21SWV4NShUzblcEZB8MF1QEGwAdGl1LWlBWVQtCFwFvZQVTXllPVQYaBB0bFHtcZF0; PCSYCityID=CN_110000_110100_0; TrackID=1Ie27V-HA2L3ZUhcBhwdBCaQ5R2bLuurNp_3tzduNbQWEsW2Soj19esmFwpQWUbCdxpEMjMG9T1POSAKxADkbnfQxvmelc8i-x0I2fJSAIZ0vl8tXkSAcb02ciLlaNqJG; ceshi3.com=201; __jdc=76161171; __jda=76161171.16599281313162050207785.1659928131.1663296734.1663300295.9; __jdb=76161171.1.16599281313162050207785|9.1663300295; __jdv=76161171|baidu-pinzhuan|t_288551095_baidupinzhuan|cpc|0f3d30c8dba7459bb52f2eb5eba8ac7d_0_f24c32b3a23145218dfed009b99d7bed|1663300294541; thor=FFA6225138091B52706D8499703FC64A6191AF401AACDB5BEAC7986A03DD5C61DCC9DB334BD62876632FF98E0D4CCE37B779B8BE6688703AAE945EE0E20A14A770C00759036541B48D18F34E6665C8A7C03DB2BBBA3B6EE59025496680F53F378DCD61FC07F3CAC17032D24D9FFE3F1D49F6CD95B50E0C6E8AEAF504E86DF336; shshshfp=c865ab626706de10e188df63fac4e964; shshshsID=0a2f0f0a392576adf0d42aa779f42fe3_1_1663300295635; 3AB9D23F7A4B3C9B=77724GPN476XAGK7BNSQEVIKTWPLKEETH34HTOQCWNTQ574AXIVJPVBLBMK7H2PUC6G57VUFLTR3PEVL4YGJ3PMFNM',
            'sec-ch-ua': 'Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104',
            'sec-ch-ua-mobile': '?0',
            # 'sec-ch-ua-platform': 'macOS',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-TW,zh;q=0.9,zh-CN;q=0.8',
            'Cache-Control': 'max-age=0',
            'Sec-Fetch-Site': 'none',
            'Referer': 'https://marathon.jd.com/seckillM/seckill.action?skuId={0}&num={1}&rid={2}'.format(
                self.sku_id, self.seckill_num, int(time.time())),
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://marathon.jd.com'
        }
        resp = self.session.post(url=url, data=data, headers=headers)
        return parse_json(resp.text)

    def _get_seckill_order_data(self):
        """生成提交抢购订单所需的请求体参数
        :return: 请求体参数组成的dict
        """
        logger.info('生成提交抢购订单所需参数...')
        # 获取用户秒杀初始化信息
        self.seckill_init_info[self.sku_id] = self._get_seckill_init_info()
        init_info = self.seckill_init_info.get(self.sku_id)
        # token = init_info['token']
        token = '6576c6aa7f5d7973f1f2da36bed2fb4e'
        data = {
            'skuId': self.sku_id,
            'num': self.seckill_num,
            'addressId': '4553344744',
            'yuShou': 'true',
            'isModifyAddress': 'false',
            'name': '王刚',
            'provinceId': 1,
            'cityId': 2901,
            'countyId': 55565,
            'townId': 0,
            'addressDetail': '天通苑西一区5号楼1单元快递柜',
            'mobile': '184****1665',
            'mobileKey': '5cfbf6d3c2fe937b18ea74b0130f37e4',
            'email': '',
            'postCode': '',
            'invoiceTitle': 4,
            'invoiceCompanyName': '',
            'invoiceContent': 1,
            'invoiceTaxpayerNO': '',
            'invoiceEmail': '',
            'invoicePhone': '184****1665',
            'invoicePhoneKey': '5cfbf6d3c2fe937b18ea74b0130f37e4',
            'invoice': 'false',
            'password': '',
            'codTimeType': 3,
            'paymentType': 4,
            'areaCode': '',
            'overseas': 0,
            'phone': '',
            'eid': global_config.getRaw('config', 'eid'),
            'fp': global_config.getRaw('config', 'fp'),
            'token': token,
            'pru': ''
        }
        return data

    def submit_seckill_order(self):
        url = 'https://marathon.jd.com/seckillnew/orderService/submitOrder.action'
        payload = {
            'skuId': self.sku_id,
        }
        self.seckill_order_data[self.sku_id] = self._get_seckill_order_data()
        logger.info('提交抢购订单...')
        headers = {
            'User-Agent': get_random_useragent(),
            'Host': 'marathon.jd.com',
            'Referer': 'https://marathon.jd.com/seckillM/seckill.action?skuId={0}&num={1}&rid={2}'.format(
                self.sku_id, self.seckill_num, int(time.time())),
        }
        resp = self.session.post(
            url=url,
            params=payload,
            data=self.seckill_order_data.get(
                self.sku_id),
            headers=headers)
        resp_json = parse_json(resp.text)
        # 返回信息
        # 抢购失败：
        # {'errorMessage': '很遗憾没有抢到，再接再厉哦。', 'orderId': 0, 'resultCode': 60074, 'skuId': 0, 'success': False}
        # {'errorMessage': '抱歉，您提交过快，请稍后再提交订单！', 'orderId': 0, 'resultCode': 60017, 'skuId': 0, 'success': False}
        # {'errorMessage': '系统正在开小差，请重试~~', 'orderId': 0, 'resultCode': 90013, 'skuId': 0, 'success': False}
        # 抢购成功：
        # {"appUrl":"xxxxx","orderId":820227xxxxx,"pcUrl":"xxxxx","resultCode":0,"skuId":0,"success":true,"totalMoney":"xxxxx"}
        if resp_json.get('success'):
            order_id = resp_json.get('orderId')
            total_money = resp_json.get('totalMoney')
            pay_url = 'https:' + resp_json.get('pcUrl')
            logger.info(
                '抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}'.format(order_id,total_money,pay_url)
                )
            if global_config.getRaw('messenger', 'enable') == 'true':
                success_message = "抢购成功，订单号:{}, 总价:{}, 电脑端付款链接:{}".format(order_id, total_money, pay_url)
                send_wechat(success_message)
            return True
        else:
            logger.info('抢购失败，返回信息:{}'.format(resp_json))
            if global_config.getRaw('messenger', 'enable') == 'true':
                error_message = '抢购失败，返回信息:{}'.format(resp_json)
                send_wechat(error_message)
            return False