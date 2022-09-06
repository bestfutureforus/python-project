import requests
from config import global_config
from util import get_random_useragent


class DouBanZq(object):
    def __init__(self):
        self.url = "https://movie.douban.com/top250?filter="
        self.default_user_agent = global_config.getRaw('config', 'DEFAULT_USER_AGENT')

    def getMoiveList(self):
        headers = {
            'User-Agent': get_random_useragent(),
            'Referer': 'https://movie.douban.com/top250?filter=unwatched',
            'Cookie': 'll="108288"; bid=v4df8TGeou4; __utma=30149280.1806510338.1662388229.1662388229.1662388229.1; __utmc=30149280; __utmz=30149280.1662388229.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utma=223695111.405377479.1662388234.1662388234.1662388234.1; __utmb=223695111.0.10.1662388234; __utmc=223695111; __utmz=223695111.1662388234.1.1.utmcsr=douban.com|utmccn=(referral)|utmcmd=referral|utmcct=/; _pk_ref.100001.4cf6=%5B%22%22%2C%22%22%2C1662388234%2C%22https%3A%2F%2Fwww.douban.com%2F%22%5D; _pk_ses.100001.4cf6=*; ap_v=0,6.0; _vwo_uuid_v2=D3D1C488C2A4D29E644823A6AA114007A|25eaf907659582bb50be7996bebe311b; __gads=ID=fa038d5a16aed5b5-2203c3c443d6006f:T=1662388295:RT=1662388295:S=ALNI_MbdKyiRuWZdGiXssiIYWByqga02Rg; __gpi=UID=0000097bd7f23ac1:T=1662388295:RT=1662388295:S=ALNI_MbiGRLSQylXABEXrFKkbVrG3KQCvA; __utmb=30149280.10.10.1662388229; _pk_id.100001.4cf6=a6e99b8cb8c20c8d.1662388234.1.1662390076.1662388234.; dbcl2="256063906:MtOucZPD5Cg"; ck=rouP',
            'Host': 'movie.douban.com',
            'sec-ch-ua': 'Chromium";v="104", " Not A;Brand";v="99", "Google Chrome";v="104',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-TW,zh;q=0.9,zh-CN;q=0.8',
            'Connection': 'keep-alive',
            'sec - ch - ua - mobile': '?0',
            'sec-ch-ua-platform': 'macOS',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        response = requests.get(url=self.url, headers=headers)
        print(response.text)
        print(response.status_code)
