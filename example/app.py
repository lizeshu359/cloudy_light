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

#===========================
# RabbitMQ 连接设置
#===========================
#RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
#RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
#RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
#QUEUE_NAME = 'demo_queue'

#credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
#for i in range(10):  # 最多重试 10 次
#    try:
#        connection = pika.BlockingConnection(
#            pika.ConnectionParameters(
#                host=RABBITMQ_HOST,
#                virtual_host='/',
#                credentials=credentials
#            )
#        )
#        break
#   except pika.exceptions.AMQPConnectionError:
#        print(f"RabbitMQ 未准备好，重试 {i+1}/10 ...")
#        time.sleep(5)
#else:
#    print("无法连接到 RabbitMQ，退出程序")
#    exit(1)
#
#channel = connection.channel()
#channel.queue_declare(queue=QUEUE_NAME)

#===========================
# 定义预处理函数
#===========================
def cut_photon_reconstruction(photon_isTightID):
    # 仅保留两个光子都为 True 的事件
    return (photon_isTightID[:, 0] == False) | (photon_isTightID[:, 1] == False)

def cut_photon_pt(photon_pt):
    # 仅保留第一个光子 pt > 50 GeV 且第二个光子 pt > 30 GeV 的事件
    return (photon_pt[:, 0] < 50) | (photon_pt[:, 1] < 30)

def cut_isolation_pt(photon_ptcone20, photon_pt):
    # 保留 calorimeter isolation 小于 5.5% 的事件
    return ((photon_ptcone20[:, 0] / photon_pt[:, 0]) > 0.055) | ((photon_ptcone20[:, 1] / photon_pt[:, 1]) > 0.055)

def cut_photon_eta_transition(photon_eta):
    # 保留 |eta| 不在 1.37 到 1.52 区间的事件
    condition_0 = (np.abs(photon_eta[:, 0]) < 1.52) & (np.abs(photon_eta[:, 0]) > 1.37)
    condition_1 = (np.abs(photon_eta[:, 1]) < 1.52) & (np.abs(photon_eta[:, 1]) > 1.37)
    return condition_0 | condition_1

def calc_mass(photon_pt, photon_eta, photon_phi, photon_e):
    # 利用 vector 库计算双光子不变量质量
    p4 = vector.zip({"pt": photon_pt, "eta": photon_eta, "phi": photon_phi, "e": photon_e})
    return (p4[:, 0] + p4[:, 1]).M

def cut_mass(invariant_mass):
    return (invariant_mass == 0)

def cut_iso_mass(photon_pt, invariant_mass):
    # 保留 (pt / invariant_mass) 小于 35% 的事件
    return ((photon_pt[:, 0] / invariant_mass) < 0.35) | ((photon_pt[:, 1] / invariant_mass) < 0.35)

#===========================
# 设置 ROOT 文件的路径（URL）
#===========================
default_path = "https://atlas-opendata.web.cern.ch/atlas-opendata/13TeV/GamGam/Data/"
custom_path = os.getenv("DATA_PATH", default_path)

samples_list = [
    'data15_periodD', 'data15_periodE', 'data15_periodF',
    'data15_periodG', 'data15_periodH', 'data15_periodJ',
    'data16_periodA', 'data16_periodB', 'data16_periodC',
    'data16_periodD', 'data16_periodE', 'data16_periodF'
]

# 这里选取 data15_periodG 样本（索引 3）
print("选取的样本:", samples_list[3])
root_file_url = custom_path + samples_list[3] + ".root"
print("ROOT 文件地址:", root_file_url)

#===========================
# 读取 ROOT 文件并获取 tree
#===========================
try:
    with uproot.open(root_file_url + ":analysis") as t:
        tree = t
except Exception as e:
    print("打开 ROOT 文件失败:", e)
    exit(1)

print("Tree 条目数:", tree.num_entries)
print("Tree 键列表:", tree.keys())

#===========================
# 数据预处理
#===========================
sample_data = []
variables = ["photon_pt", "photon_eta", "photon_phi", "photon_e", "photon_isTightID", "photon_ptcone20"]

for data in tree.iterate(variables, library="ak"):
    # 应用各项切割条件
    photon_isTightID = data['photon_isTightID']
    data = data[~cut_photon_reconstruction(photon_isTightID)]

    photon_pt = data['photon_pt']
    data = data[~cut_photon_pt(photon_pt)]

    data = data[~cut_isolation_pt(data['photon_ptcone20'], data['photon_pt'])]

    photon_eta = data['photon_eta']
    data = data[~cut_photon_eta_transition(photon_eta)]

    # 计算双光子不变量质量并存入数据中
    data['mass'] = calc_mass(data['photon_pt'], data['photon_eta'], data['photon_phi'], data['photon_e'])

    data = data[~cut_mass(data['mass'])]
    data = data[~cut_iso_mass(data['photon_pt'], data['mass'])]

    sample_data.append(data)

try:
    final_data = ak.concatenate(sample_data)
    print("预处理后数据条目数:", len(final_data))
except Exception as e:
    print("合并数据出错:", e)
    final_data = None

#===========================
# 发送处理结果摘要到 RabbitMQ（可选）
#===========================
#if final_data is not None:
#    summary = {
#        "num_entries_processed": len(final_data),
#        "fields": list(final_data.fields) if hasattr(final_data, "fields") else "unknown"
#    }
#    message = json.dumps(summary)
#    channel.basic_publish(
#        exchange="",
#        routing_key=QUEUE_NAME,
#        body=message.encode("utf-8")
#    )
#    print("处理摘要已发送到 RabbitMQ:", summary)
#else:
#    print("未能处理数据，无摘要信息发送。")

#connection.close()