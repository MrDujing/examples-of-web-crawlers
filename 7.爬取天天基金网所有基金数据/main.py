# -*- coding:utf-8 -*-
import csv
import json
import os
import pathlib
import queue
import random
import re
import threading
import time

import requests
from fake_useragent import UserAgent

import IPProxy


# referer列表
referer_list = [
    'http://fund.eastmoney.com/110022.html',
    'http://fund.eastmoney.com/110023.html',
    'http://fund.eastmoney.com/110024.html',
    'http://fund.eastmoney.com/110025.html'
]


# 返回一个可用代理，格式为ip:端口
# 利用IPProxy模块获取IP池
# 一次获取的IP次会存入IPPool.json文件，下次读取前先判断时间
# 当创建时间超过1h，则重新获取；小于1小时，则仍然使用现有IP池
# 返回dict类型，格式为Key-Value : ip:port - protocol
def get_proxy(url):
    json_file = pathlib.Path('.\\IPPool.json')
    if json_file.exists():
        time_interval = time.time() - os.stat('.\\IPPool.json').st_ctime
        if time_interval > 3600:
            ip_dict = IPProxy.crawl_ip(url)
            dict_to_json(ip_dict)
    else:
        ip_dict = IPProxy.crawl_ip(url)
        dict_to_json(ip_dict)
    with open('IPPool.json', encoding='utf-8') as f:
        available_ip = json.load(f)
    ip_port, protocol = random.choice(list(available_ip.items()))
    proxy = {protocol: ip_port}
    return proxy


# 将词典写入到IPPool.json文件
def dict_to_json(ip_dict):
    with open('IPPool.json', 'w') as f:
        json.dump(ip_dict, f)


# 获取所有基金代码
# 后期的应用中，基金代码由手工输入
# 因为需要获取指定基金的数据
def get_fund_code():
    # 获取一个随机user_agent和Referer
    header = {'User-Agent': UserAgent().random,
              'Referer': random.choice(referer_list)
              }

    # 访问网页接口
    req = requests.get('http://fund.eastmoney.com/js/fundcode_search.js', timeout=5, headers=header)
    # 获取所有基金代码
    fund_code = req.content.decode()
    fund_code = fund_code.replace("﻿var r = [", "").replace("];", "")

    # 正则批量提取
    fund_code = re.findall(r"[\[](.*?)[\]]", fund_code)
    fund_code_list = []
    # 对每行数据进行处理，并存储到fund_code_list列表中
    for sub_data in fund_code:
        data = sub_data.replace("\"", "").replace("'", "")
        data_list = data.split(",")
        fund_code_list.append(data_list)
    return fund_code_list


# 获取基金数据
def get_fund_data():
    # 当队列不为空时
    while not fund_code_queue.empty():

        # 从队列读取一个基金代码
        # 读取是阻塞操作
        fund_code = fund_code_queue.get()

        # 获取一个代理，格式为ip:端口
        proxy = get_proxy('http://www.xicidaili.com/')

        # 获取一个随机user_agent和Referer
        header = {'User-Agent': UserAgent().random,
                  'Referer': random.choice(referer_list)
                  }

        # 使用try、except来捕获异常
        # 如果不捕获异常，程序可能崩溃
        try:
            # 使用代理访问
            req = requests.get("http://fundgz.1234567.com.cn/js/" + str(fund_code) + ".js", proxies=proxy, timeout=3,
                               headers=header)
            # 没有报异常，说明访问成功
            # 获得返回数据
            data = (req.content.decode()).replace("jsonpgz(", "").replace(");", "").replace("'", "\"")
            data_dict = json.loads(data)

            # 申请获取锁，此过程为阻塞等待状态，直到获取锁完毕
            mutex_lock.acquire()

            # 追加数据写入csv文件，若文件不存在则自动创建
            with open('./fund_data.csv', 'a+', encoding='utf-8') as csv_file:
                csv_writer = csv.writer(csv_file)
                data_list = [x for x in data_dict.values()]
                csv_writer.writerow(data_list)
                print('写入成功')

            # 释放锁
            mutex_lock.release()
        except Exception:
            # 访问失败了，所以要把我们刚才取出的数据再放回去队列中
            fund_code_queue.put(fund_code)
            print("访问失败，尝试使用其他代理访问")


if __name__ == '__main__':

    # 获取所有基金代码
    fund_code_list = get_fund_code()

    # 将所有基金代码放入先进先出FIFO队列中
    # 队列的写入和读取都是阻塞的，故在多线程情况下不会乱
    # 在不使用框架的前提下，引入多线程，提高爬取效率
    # 创建一个队列
    fund_code_queue = queue.Queue(len(fund_code_list))
    # 写入基金代码数据到队列
    for i in range(len(fund_code_list)):
        # fund_code_list[i]也是list类型，其中该list中的第0个元素存放基金代码
        fund_code_queue.put(fund_code_list[i][0])

    # 创建一个线程锁，防止多线程写入文件时发生错乱
    mutex_lock = threading.Lock()
    # 线程数为50，在一定范围内，线程数越多，速度越快
    for i in range(2):
        t = threading.Thread(target=get_fund_data, name='LoopThread' + str(i))
        t.start()
