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

# RabbitMQ 连接信息
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'demo_queue'

# 连接重试参数
RETRY_INTERVAL = 5  # 每次重试间隔（秒）
MAX_RETRIES = 12    # 最多重试次数（5 秒 * 12 = 60 秒）

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)

for attempt in range(MAX_RETRIES):
    try:
        print(f"[INFO] 尝试连接 RabbitMQ ({attempt + 1}/{MAX_RETRIES})...")
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host='/', credentials=credentials)
        )
        print("[INFO] 成功连接 RabbitMQ！")
        break  # 连接成功，跳出循环
    except pika.exceptions.AMQPConnectionError as e:
        print(f"[WARNING] RabbitMQ 未就绪，{RETRY_INTERVAL} 秒后重试...")
        time.sleep(RETRY_INTERVAL)
else:
    print("[ERROR] 无法连接到 RabbitMQ，退出程序！")
    exit(1)  # 达到最大重试次数后退出

channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME)

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

# Controls the fraction of all the events analysed
fraction = 1  # all of the data is used to run this analysis (implemented in the loop over the tree)
# reduce this if you want the code to run quicker

all_data = []
sample_data = []
print("部署完成")
# Loop over each file
for val in samples_list:

    # Print which sample is being processed
    print('Processing ' + val + ' samples')

    fileString = custom_path + val + ".root"  # file name to open

    # Open file
    with uproot.open(fileString + ":analysis") as t:
        tree = t

    numevents = tree.num_entries
    variables = ['photon_pt', 'photon_eta', 'photon_phi', 'photon_e', 'photon_isTightID', 'photon_ptcone20']


    def cut_photon_reconstruction(photon_isTightID):
        # Only the events which have True for both photons are kept
        return (photon_isTightID[:, 0] == False) | (photon_isTightID[:, 1] == False)

        # Cut on the transverse momentum


    def cut_photon_pt(photon_pt):
        # Only the events where photon_pt[0] > 50 GeV and photon_pt[1] > 30 GeV are kept
        return (photon_pt[:, 0] < 50) | (photon_pt[:, 1] < 30)


    # Cut on the energy isolation
    def cut_isolation_pt(photon_ptcone20, photon_pt):
        # Only the events where the calorimeter isolation is less than 5.5% are kept
        return ((photon_ptcone20[:, 0] / photon_pt[:, 0]) > 0.055) | ((photon_ptcone20[:, 1] / photon_pt[:, 1]) > 0.055)


    # Cut on the pseudorapidity in barrel/end-cap transition region
    def cut_photon_eta_transition(photon_eta):
        # Only the events where modulus of photon_eta is outside the range 1.37 to 1.52 are kept
        condition_0 = (np.abs(photon_eta[:, 0]) < 1.52) & (np.abs(photon_eta[:, 0]) > 1.37)
        condition_1 = (np.abs(photon_eta[:, 1]) < 1.52) & (np.abs(photon_eta[:, 1]) > 1.37)
        return condition_0 | condition_1


    # This function calculates the invariant mass of the 2-photon state
    def calc_mass(photon_pt, photon_eta, photon_phi, photon_e):
        p4 = vector.zip({"pt": photon_pt, "eta": photon_eta, "phi": photon_phi, "e": photon_e})
        invariant_mass = (p4[:, 0] + p4[:, 1]).M  # .M calculates the invariant mass
        return invariant_mass


    # Cut on null diphoton invariant mass
    def cut_mass(invariant_mass):
        return (invariant_mass == 0)


    # Cut on diphoton invariant mass based isolation
    # Only the events where the invididual photon invariant mass based isolation is larger than 35% are kept
    def cut_iso_mass(photon_pt, invariant_mass):
        return ((photon_pt[:, 0] / invariant_mass) < 0.35) | ((photon_pt[:, 1] / invariant_mass) < 0.35)
    # Perform the cuts for each data entry in the tree and calculate the invariant mass
    print("准备计算")
    for data in tree.iterate(variables, library="ak", entry_stop=numevents * fraction):
        photon_isTightID = data['photon_isTightID']
        data = data[~cut_photon_reconstruction(photon_isTightID)]

        photon_pt = data['photon_pt']
        data = data[~cut_photon_pt(photon_pt)]

        data = data[~cut_isolation_pt(data['photon_ptcone20'], data['photon_pt'])]

        photon_eta = data['photon_eta']
        data = data[~cut_photon_eta_transition(photon_eta)]

        data['mass'] = calc_mass(data['photon_pt'], data['photon_eta'], data['photon_phi'], data['photon_e'])

        data = data[~cut_mass(data['mass'])]

        data = data[~cut_iso_mass(data['photon_pt'], data['mass'])]

        # Append data to the whole sample data list
        sample_data.append(data)

# turns sample_data back into an awkward array
all_data = ak.concatenate(sample_data)
print("计算完成")
# 发送处理结果到 RabbitMQ
if all_data is not None:
    summary = {
        "mass_values": ak.to_numpy(all_data['mass']).tolist()  # 将质量值传递给下一个容器
    }
    message = json.dumps(summary)
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=message.encode("utf-8")
    )
    print("处理摘要已发送到 RabbitMQ:", summary)
else:
    print("未能处理数据，无摘要信息发送。")

#connection.close()