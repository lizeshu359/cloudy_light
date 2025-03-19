import os
import time
import json
import pika
import signal
import time # to measure time to analyse

import awkward as ak # for handling complex and nested data structures efficiently
import numpy as np # # for numerical calculations such as histogramming
import matplotlib.pyplot as plt # for plotting
from matplotlib.ticker import MaxNLocator,AutoMinorLocator # for minor ticks
from lmfit.models import PolynomialModel, GaussianModel # for the signal and background fits
import vector #to use vectors
import requests # for HTTP access
import aiohttp # HTTP client support

# RabbitMQ 连接信息
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
Input_QUEUE = 'preprocessing_queue'
Output_QUEUE = 'analysis_queue'

# 连接 RabbitMQ
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host='/', credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue=Input_QUEUE)
channel.queue_declare(queue=Output_QUEUE)

# 直方图参数
xmin, xmax, step_size = 100, 160, 2  # GeV
bin_edges = np.arange(start=xmin, stop=xmax + step_size, step=step_size)
bin_centres = np.arange(start=xmin + step_size / 2, stop=xmax + step_size / 2, step=step_size)


def anaylsis_data(ch, method, properties, body):
    print("[INFO] 收到消息，开始数据处理...")

    try:
        summary = json.loads(body.decode('utf-8'))

        if 'mass_values' not in summary:
            print("[ERROR] 消息中缺少 'mass_values' 键")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        mass_values = ak.to_numpy(summary['mass_values'])

        # 计算直方图
        data_x, _ = np.histogram(mass_values, bins=bin_edges)
        data_x_errors = np.sqrt(data_x)

        # 拟合模型
        polynomial_mod = PolynomialModel(4)
        gaussian_mod = GaussianModel()
        pars = polynomial_mod.guess(data_x, x=bin_centres)
        pars += gaussian_mod.guess(data_x, x=bin_centres, amplitude=100, center=125, sigma=2)
        model = polynomial_mod + gaussian_mod
        out = model.fit(data_x, pars, x=bin_centres, weights=1 / data_x_errors)

        # 提取背景数据
        params_dict = out.params.valuesdict()
        background = sum(params_dict[f'c{i}'] * bin_centres ** i for i in range(5))
        signal_x = data_x - background

        # 发送到 `processed_queue`
        processed_data = {
            "bin_centres": bin_centres.tolist(),
            "data_x": data_x.tolist(),
            "data_x_errors": data_x_errors.tolist(),
            "background": background.tolist(),
            "signal_x": signal_x.tolist(),
            "best_fit": out.best_fit.tolist(),
        }
        channel.basic_publish(exchange='', routing_key=Output_QUEUE, body=json.dumps(processed_data))
        print("[INFO] 数据处理完成，已发送到 `processed_queue`")

    except Exception as e:
        print("[ERROR] 数据处理出错:", str(e))

    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# 监听队列
channel.basic_consume(queue=Input_QUEUE, on_message_callback=anaylsis_data, auto_ack=False)
print("[INFO] 监听 `demo_queue` 中，等待数据...")
channel.start_consuming()
