# -*- coding:utf-8 -*-

from urllib.request import urlopen, Request
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


# 提取网站url上面的IP、端口、协议
# INPUT：免费的网站IP代理，以'http://www.xicidaili.com/'为例
# OUTPUT: 返回可用的代理，以词典形式返回：Key-Value 对应 IP:Port-Protocol
def crawl_ip(url):
    user_agent = "User-Agent:" + UserAgent().random  # 利用UserAgent获取随机应用
    headers = {'User-Agent': user_agent}
    request = Request(url, headers=headers)
    response = urlopen(request)
    bs_obj = BeautifulSoup(response, 'lxml')  # 解析获取到的html
    return get_ip_dict(bs_obj)


# INPUT: obj, 通过BeautifulSoup函数，以lxml形式解析html文件获取
# OUTPUT: 返回可用的代理，以词典形式返回：Key-Value 对应 IP:Port-Protocol
def get_ip_dict(obj):
    ip_text = obj.findAll('tr', {'class': 'odd'})  # 获取带有IP地址的表格的所有行
    ip_dict = {}
    for i in range(len(ip_text)):
        ip_tag = ip_text[i].findAll('td')
        ip_port = ip_tag[1].get_text() + ':' + ip_tag[2].get_text()  # 提取出IP地址和端口号
        ip_protocol = ip_tag[5].get_text()  # 提取对应的协议
        if is_available_ip(ip_port, ip_protocol) and ip_protocol != 'socks4/5':  # 除去SOCK通信，只保留HTTP，HTTPS
            ip_dict[ip_port] = ip_protocol
    return ip_dict


# 判断IP是否可用，用‘www.baidu.com’来测试
# INPUT: ip地址及端口, IP协议
# OUTPUT: 当IP有效时，返回真
def is_available_ip(ip_port, ip_protocol):
    proxies = {ip_protocol: ip_port}
    response = requests.get('http://www.baidu.com', proxies=proxies, timeout=10)
    if response.status_code == 200:
        return True
