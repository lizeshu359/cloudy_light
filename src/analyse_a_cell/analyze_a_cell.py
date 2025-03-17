import pika
import time

# 连接到 RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

# 创建队列
channel.queue_declare(queue='queue1')

# 发送消息
for i in range(10):
    message = f"Message {i}"
    channel.basic_publish(exchange='', routing_key='queue1', body=message)
    print(f" [x] Sent {message}")
    time.sleep(1)

connection.close()