import sys
from DouBan import DouBanZq


if __name__ == '__main__':
    msg = """
    开始豆瓣电影查看
    """
    print(msg)
    douBan = DouBanZq()
    douBan.getMoiveList()
    sys.exit()
