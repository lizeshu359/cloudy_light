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
Input_QUEUE = 'analysis_queue'

# 连接 RabbitMQ
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
channel.queue_declare(queue=Input_QUEUE)


def draw_plot(ch, method, properties, body):
    print("[INFO] 收到处理后的数据，开始绘图...")

    try:
        data = json.loads(body.decode('utf-8'))
        bin_centres = np.array(data["bin_centres"])
        data_x = np.array(data["data_x"])
        data_x_errors = np.array(data["data_x_errors"])
        background = np.array(data["background"])
        signal_x = np.array(data["signal_x"])
        best_fit = np.array(data["best_fit"])

        # 绘制主图
        plt.axes([0.1, 0.3, 0.85, 0.65])
        main_axes = plt.gca()
        main_axes.errorbar(bin_centres, data_x, yerr=data_x_errors, fmt='ko', label='Data')
        main_axes.plot(bin_centres, best_fit, '-r', label='Sig+Bkg Fit')
        main_axes.plot(bin_centres, background, '--r', label='Background')

        main_axes.set_xlim(100, 160)
        main_axes.set_ylabel('Events / 2 GeV')
        main_axes.legend(frameon=False, loc='lower left')

        # 副图
        plt.axes([0.1, 0.1, 0.85, 0.2])
        sub_axes = plt.gca()
        sub_axes.errorbar(bin_centres, signal_x, yerr=data_x_errors, fmt='ko')
        sub_axes.plot(bin_centres, best_fit - background, '-r')
        sub_axes.plot(bin_centres, np.zeros_like(bin_centres), '--r')

        sub_axes.set_xlim(100, 160)
        sub_axes.set_xlabel(r'di-photon invariant mass $\mathrm{m_{\gamma\gamma}}$ [GeV]')
        sub_axes.set_ylabel('Events-Bkg')

        img_dir = "fit_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)
        img_filename = os.path.join(img_dir, f"mass_distribution_fit_{int(time.time())}.png")
        plt.savefig(img_filename)
        plt.close()
        print(f"[INFO] 图像已保存: {img_filename}")

    except Exception as e:
        print("[ERROR] 绘图时出错:", str(e))

    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


# 监听 `processed_queue`
channel.basic_consume(queue=Input_QUEUE, on_message_callback=draw_plot, auto_ack=False)
print("[INFO] 监听 `processed_queue` 中，等待数据...")
channel.start_consuming()