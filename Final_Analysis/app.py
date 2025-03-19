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
fraction=1
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
        # *************
        # Main plot
        # *************
        plt.axes([0.1, 0.3, 0.85, 0.65])  # left, bottom, width, height
        main_axes = plt.gca()  # get current ax
        # plot the data points
        main_axes.errorbar(x=bin_centres, y=data_x, yerr=data_x_errors,
                           fmt='ko',  # 'k' means black and 'o' means circles
                           label='Data')

        # plot the signal + background fit
        main_axes.plot(bin_centres,  # x
                       out.best_fit,  # y
                       '-r',  # single red line
                       label='Sig+Bkg Fit ($m_H=125$ GeV)')

        # plot the background only fit
        main_axes.plot(bin_centres,  # x
                       background,  # y
                       '--r',  # dashed red line
                       label='Bkg (4th order polynomial)')

        # set the x-limit of the main axes
        main_axes.set_xlim(left=xmin, right=xmax)

        # separation of x-axis minor ticks
        main_axes.xaxis.set_minor_locator(AutoMinorLocator())

        # set the axis tick parameters for the main axes
        main_axes.tick_params(which='both',  # ticks on both x and y axes
                              direction='in',  # Put ticks inside and outside the axes
                              top=True,  # draw ticks on the top axis
                              labelbottom=False,  # don't draw tick labels on bottom axis
                              right=True)  # draw ticks on right axis

        # write y-axis label for main
        main_axes.set_ylabel('Events / ' + str(step_size) + ' GeV',
                             horizontalalignment='right')

        # set the y-axis limit for the main axes
        main_axes.set_ylim(bottom=0, top=np.amax(data_x) * 1.5)

        # set minor ticks on the y-axis of the main axes
        main_axes.yaxis.set_minor_locator(AutoMinorLocator())

        # avoid displaying y=0 on the main axes
        main_axes.yaxis.get_major_ticks()[0].set_visible(False)

        # Add text 'ATLAS Open Data' on plot
        plt.text(0.2,  # x
                 0.92,  # y
                 'ATLAS Open Data',  # text
                 transform=main_axes.transAxes,  # coordinate system used is that of main_axes
                 fontsize=13)

        # Add text 'for education' on plot
        plt.text(0.2,  # x
                 0.86,  # y
                 'for education',  # text
                 transform=main_axes.transAxes,  # coordinate system used is that of main_axes
                 style='italic',
                 fontsize=8)

        lumi = 36.1
        lumi_used = str(lumi * fraction)  # luminosity to write on the plot
        plt.text(0.2,  # x
                 0.8,  # y
                 '$\sqrt{s}$=13 TeV,$\int$L dt = ' + lumi_used + ' fb$^{-1}$',  # text
                 transform=main_axes.transAxes)  # coordinate system used is that of main_axes

        # Add a label for the analysis carried out
        plt.text(0.2,  # x
                 0.74,  # y
                 r'$H \rightarrow \gamma\gamma$',  # text
                 transform=main_axes.transAxes)  # coordinate system used is that of main_axes

        # draw the legend
        main_axes.legend(frameon=False,  # no box around the legend
                         loc='lower left')  # legend location

        # *************
        # Data-Bkg plot
        # *************
        plt.axes([0.1, 0.1, 0.85, 0.2])  # left, bottom, width, height
        sub_axes = plt.gca()  # get the current axes

        # set the y axis to be symmetric about Data-Background=0
        sub_axes.yaxis.set_major_locator(MaxNLocator(nbins='auto',
                                                     symmetric=True))

        # plot Data-Background
        sub_axes.errorbar(x=bin_centres, y=signal_x, yerr=data_x_errors,
                          fmt='ko')  # 'k' means black and 'o' means circles

        # draw the fit to data
        sub_axes.plot(bin_centres,  # x
                      out.best_fit - background,  # y
                      '-r')  # single red line

        # draw the background only fit
        sub_axes.plot(bin_centres,  # x
                      background - background,  # y
                      '--r')  # dashed red line

        # set the x-axis limits on the sub axes
        sub_axes.set_xlim(left=xmin, right=xmax)

        # separation of x-axis minor ticks
        sub_axes.xaxis.set_minor_locator(AutoMinorLocator())

        # x-axis label
        sub_axes.set_xlabel(r'di-photon invariant mass $\mathrm{m_{\gamma\gamma}}$ [GeV]',
                            x=1, horizontalalignment='right',
                            fontsize=13)

        # set the tick parameters for the sub axes
        sub_axes.tick_params(which='both',  # ticks on both x and y axes
                             direction='in',  # Put ticks inside and outside the axes
                             top=True,  # draw ticks on the top axis
                             right=True)  # draw ticks on right axis

        # separation of y-axis minor ticks
        sub_axes.yaxis.set_minor_locator(AutoMinorLocator())

        # y-axis label on the sub axes
        sub_axes.set_ylabel('Events-Bkg')

        # Generic features for both plots
        main_axes.yaxis.set_label_coords(-0.09, 1)  # x,y coordinates of the y-axis label on the main axes
        sub_axes.yaxis.set_label_coords(-0.09, 0.5)  # x,y coordinates of the y-axis label on the sub axes

        img_dir = "fit_images"
        if not os.path.exists(img_dir):
            os.makedirs(img_dir)

        img_filename = os.path.join(img_dir, f"mass_distribution_fit_{int(time.time())}.png")
        plt.savefig(img_filename)
        plt.close()
        print(f"Fit image has been saved to {img_filename}")
    except Exception as e:
        print("[ERROR] 处理消息时出错:", str(e))
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)

# 超时机制，防止 `start_consuming()` 无限阻塞
def timeout_handler(signum, frame):
    print("[INFO] 超时退出监听...")
    channel.stop_consuming()

channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=False)
channel.start_consuming()

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(120)  # 2 分钟超时
