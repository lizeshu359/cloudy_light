import os
import time
import json
import numpy as np
import awkward as ak
import pika
from lmfit.models import PolynomialModel, GaussianModel
import signal

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

# Histogram bin setup
xmin, xmax, step_size = 100, 160, 2  # GeV
bin_edges = np.arange(start=xmin, stop=xmax+step_size, step=step_size)
bin_centres = np.arange(start=xmin+step_size/2, stop=xmax+step_size/2, step=step_size)

def callback(ch, method, properties, body):
    print("[INFO] 收到消息，开始处理...")
    print(body[:100])
    try:
        body_str=body.decode('utf-8')
        print(body_str)
        summary = json.loads(body_str)
        print("[DEBUG] 解析 JSON 成功:", summary)
        if 'mass_values' not in summary:
            print("[ERROR] 消息中缺少 'mass_values' 键")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        mass_values = summary['mass_values']
        if not isinstance(mass_values, list) or len(mass_values) == 0:
            print("[ERROR] 'mass_values' 为空或格式不正确")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        mass_values = ak.to_numpy(mass_values)
        print("[DEBUG] 转换 mass_values 成功，前10个数据:", mass_values[:10])

        # 计算直方图
        data_x, _ = np.histogram(mass_values, bins=bin_edges)
        data_x_errors = np.sqrt(data_x)
        print("[INFO] 直方图计算成功")

        # 拟合模型
        polynomial_mod = PolynomialModel(4)
        gaussian_mod = GaussianModel()
        pars = polynomial_mod.guess(data_x, x=bin_centres)
        pars += gaussian_mod.guess(data_x, x=bin_centres, amplitude=100, center=125, sigma=2)
        model = polynomial_mod + gaussian_mod
        out = model.fit(data_x, pars, x=bin_centres, weights=1 / data_x_errors)
        print("[INFO] 拟合完成")

        # 提取背景数据
        params_dict = out.params.valuesdict()
        background = sum(params_dict[f'c{i}'] * bin_centres**i for i in range(5))
        signal_x = data_x - background
        print("[INFO] 计算完成，信号前10个值:", signal_x[:10])

    except Exception as e:
        print("[ERROR] 处理消息时出错:", str(e))
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

# 超时机制，防止 `start_consuming()` 无限阻塞
def timeout_handler(signum, frame):
    print("[INFO] 超时退出监听...")
    channel.stop_consuming()

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)  # 2 分钟超时

channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
channel.start_consuming()
