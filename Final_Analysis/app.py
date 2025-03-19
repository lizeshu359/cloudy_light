import os
import json
import pika
import numpy as np
import matplotlib.pyplot as plt
from lmfit.models import PolynomialModel, GaussianModel

# RabbitMQ 连接设置
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'demo_queue'

# 连接到 RabbitMQ
credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host='/', credentials=credentials)
)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME)

def callback(ch, method, properties, body):
    summary = json.loads(body)
    mass_values = np.array(summary["mass_values"])

    # 计算质量分布的直方图
    bin_edges = np.linspace(100, 200, 50)
    bin_centres = 0.5 * (bin_edges[1:] + bin_edges[:-1])
    data_x, _ = np.histogram(mass_values, bins=bin_edges)
    data_x_errors = np.sqrt(data_x)

    # 数据拟合
    polynomial_mod = PolynomialModel(4)  # 4次多项式模型
    gaussian_mod = GaussianModel()  # 高斯模型

    # 设置多项式模型参数初值
    pars = polynomial_mod.guess(data_x, x=bin_centres, c0=data_x.max(), c1=0, c2=0, c3=0, c4=0)
    pars += gaussian_mod.guess(data_x, x=bin_centres, amplitude=100, center=125, sigma=2)

    model = polynomial_mod + gaussian_mod  # 组合模型

    # 拟合数据
    out = model.fit(data_x, pars, x=bin_centres, weights=1 / data_x_errors)

    # *************
    # Main plot
    # *************
    plt.axes([0.1, 0.3, 0.85, 0.65])  # left, bottom, width, height
    main_axes = plt.gca()  # get current axes

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

# 订阅消息
channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback, auto_ack=True)

print('等待消息...')
channel.start_consuming()