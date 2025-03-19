import pika
import os
import time

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'demo_queue'

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)

# 添加重试逻辑
for i in range(10):  # 最多尝试10次
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                virtual_host='/',
                credentials=credentials
            )
        )
        break  # 成功连接，跳出循环
    except pika.exceptions.AMQPConnectionError:
        print(f"RabbitMQ 未准备好，重试 {i+1}/10 ...")
        time.sleep(5)  # 等待5秒后重试
else:
    print("无法连接到 RabbitMQ，退出程序")
    exit(1)



# Controls the fraction of all the events analysed
fraction = 1  # all of the data is used to run this analysis (implemented in the loop over the tree)
# reduce this if you want the code to run quicker

all_data = []
sample_data = []

# Loop over each file
for val in samples_list:

    # Print which sample is being processed
    print('Processing ' + val + ' samples')

    fileString = path + val + ".root"  # file name to open

    # Open file
    with uproot.open(fileString + ":analysis") as t:
        tree = t

    numevents = tree.num_entries

    # Perform the cuts for each data entry in the tree and calculate the invariant mass
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