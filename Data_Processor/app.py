import os
import time
import json
import uproot             # 用于读取 .root 文件
import awkward as ak       # 用于处理嵌套数据结构
import numpy as np         # 数值计算
import matplotlib.pyplot as plt  # 如需绘图
from matplotlib.ticker import MaxNLocator, AutoMinorLocator
from lmfit.models import PolynomialModel, GaussianModel  # 用于信号和背景拟合
import vector             # 用于向量运算
import requests           # HTTP 访问
import aiohttp            # HTTP 客户端支持
import pika

# RabbitMQ 连接设置
#RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
#RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
#RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
#QUEUE_NAME = 'demo_queue'

## 连接到 RabbitMQ
#credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
#connection = pika.BlockingConnection(
#    pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host='/', credentials=credentials)
#)
#channel = connection.channel()
#channel.queue_declare(queue=QUEUE_NAME)

# ===========================
# 设置 ROOT 文件的路径（URL）
# ===========================
default_path = "https://atlas-opendata.web.cern.ch/atlas-opendata/13TeV/GamGam/Data/"
custom_path = os.getenv("DATA_PATH", default_path)

samples_list = [
    'data15_periodD', 'data15_periodE', 'data15_periodF',
    'data15_periodG', 'data15_periodH', 'data15_periodJ',
    'data16_periodA', 'data16_periodB', 'data16_periodC',
    'data16_periodD', 'data16_periodE', 'data16_periodF'
]

fraction = 1  # 所有数据都用于分析（在循环中实现）
sample_data = []

# Loop over each sample file
for val in samples_list:
    print('Processing ' + val + ' samples')
    fileString = custom_path + val + ".root"

    try:
        with uproot.open(fileString + ":analysis") as t:
            tree = t
    except Exception as e:
        print("打开 ROOT 文件失败:", e)
        continue

    numevents = tree.num_entries

    for data in tree.iterate(["photon_pt", "photon_eta", "photon_phi", "photon_e", "photon_isTightID"], library="ak",
                             entry_stop=numevents * fraction):
        # 数据预处理逻辑
        # (以下为各种切割和计算质量的逻辑)

        # 例如，假设我们已经进行了数据处理并得到了all_data变量
        data['mass'] = np.sqrt(
            (data['photon_e']) ** 2 - (data['photon_pt'] * np.cosh(data['photon_eta'])) ** 2)  # 示例质量计算

        sample_data.append(data)




# Combine all sample data into one array
all_data = ak.concatenate(sample_data)

# 发送处理结果到 RabbitMQ
#if all_data is not None:
#    summary = {
#        "mass_values": ak.to_numpy(all_data['mass']).tolist()  # 将质量值传递给下一个容器
#    }
#    message = json.dumps(summary)
#    channel.basic_publish(
#        exchange="",
#       routing_key=QUEUE_NAME,
#        body=message.encode("utf-8")
#    )
#    print("处理摘要已发送到 RabbitMQ:", summary)
#else:
#    print("未能处理数据，无摘要信息发送。")

#connection.close()