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
                self._get_seckill_init_info()
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
        logger.info('获取秒杀初始化信息...')
        url = 'https://marathon.jd.com/seckillnew/orderService/pc/init.action'
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
            'Cookie': '__jdu=1662177463554221205683; o2State={%22webp%22:true%2C%22avif%22:true}; areaId=1; PCSYCityID=CN_110000_110100_0; shshshfpa=06531507-0b31-abab-a660-0becc8977463-1662285817; shshshfpb=s8YdvfMYKRZT_9LERv2X1fQ; user-key=887ed46f-e52d-4f76-a4f0-2d7ef5cc872d; pinId=rAnu0Cpjt5L6E1U9ceEJpQ; pin=523%E7%8E%8B%E5%88%9A; unick=u_s91w6nikweor; _tp=nOVpscyCes3%2BNp1X39xKAjFzMt2YX9emVILvj%2FeRV3w%3D; _pst=523%E7%8E%8B%E5%88%9A; ipLoc-djd=1-2901-55565-0.4553344744; ipLocation=%u5317%u4eac; cn=99; unpl=JF8EAMZnNSttWEpQVhpXSRIST19RWw9aGB9WPWJXXAkIQwZVGQIYEkd7XlVdXhRKHx9uYBRUXVNJUw4bBSsSEXteXVdZDEsWC2tXVgQFDQ8VXURJQlZAFDNVCV9dSRZRZjJWBFtdT1xWSAYYRRMfDlAKDlhCR1FpMjVkXlh7VAQrAhwVE0tbUltaCk8TBmxkBVdcXExdBysyHCIge1pXV1gPQicCX2Y1FgkETFYCGQRWEhdMXlRYWw1MFQdrYgZXXVtKUAISACsTIEg; TrackID=1J_ySx6oCs879Cd-PMVmqdWP5n0inMmDa0gUQljE4gXXLMSWc73NVSgNIMtPLf_jQ5JC_UXtqYdVuZ7wOX4p5df1M75zPIUvuyP3-6Csulep_PucmXYRI6uFJ2_sIhI0J; thor=FFA6225138091B52706D8499703FC64A40B921622879BBBE4E2111180C6250DB0BED47E13B701CD80C31BFC2F282B0A1ED6046EB9D358702CE8B82CC1DD55B1006D68578DD2A38E0EA2595116C3CBEF28BB3AD8E63EBFBBEF2DCDF22082AA1A99B3CA17FA55FE21AA29CF5F842E2878F54A77ACE893C42E0DA45E8EF2C0C7E45; ceshi3.com=201; __jda=76161171.1662177463554221205683.1662177464.1662350030.1662435377.6; __jdb=76161171.6.1662177463554221205683|6.1662435377; __jdc=76161171; __jdv=76161171|baidu-pinzhuan|t_288551095_baidupinzhuan|cpc|0f3d30c8dba7459bb52f2eb5eba8ac7d_0_105b0dc135344ccb9dc4c9ea9ca3121f|1662435413544; shshshfp=156abca454c1a26eb7f6ed460819db2b; shshshsID=0365b0368c377996eaa245a3b597b565_3_1662435414571; 3AB9D23F7A4B3C9B=HLFOECNF2JMWL5D3TUDIB5CFXDAVLCC53LDU3BGGLOATDYWDTDEP6XQ64URVUP6W4CUAOQIM4Y7SNV5MN2Y4HPAM34',
            'sec-ch-ua': 'Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': 'macOS',
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
            'Referer': 'https://marathon.jd.com/seckill/seckill.action?skuId={0}&num={1}&rid={2}'.format(
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
        default_address = init_info['address'][0]  # 默认地址dict
        invoice_info = init_info.get('invoiceInfo', {})  # 默认发票信息dict, 有可能不返回
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
            'email': default_address.get('email', ''),
            'postCode': '',
            'invoiceTitle': 4,
            'invoiceCompanyName': '',
            'invoiceContent': 1,
            'invoiceTaxpayerNO': '',
            'invoiceEmail': '',
            'invoicePhone': '184****1665',
            'invoicePhoneKey': '5cfbf6d3c2fe937b18ea74b0130f37e4',
            'invoice': 'true' if invoice_info else 'false',
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
        url = 'https://marathon.jd.com/seckillnew/orderService/pc/submitOrder.action'
        payload = {
            'skuId': self.sku_id,
        }
        self.seckill_order_data[self.sku_id] = self._get_seckill_order_data()
        logger.info('提交抢购订单...')
        headers = {
            'User-Agent': self.default_user_agent,
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