import pika
import os

RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'rabbitmq')
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'admin')
RABBITMQ_PASS = os.getenv('RABBITMQ_PASS', 'password123')
QUEUE_NAME = 'demo_queue'

credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
connection = pika.BlockingConnection(
    pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )
)
channel = connection.channel()
channel.queue_declare(queue=QUEUE_NAME)

channel.basic_publish(
    exchange='',
    routing_key=QUEUE_NAME,
    body='Hello, RabbitMQ!'
)
print(" [x] Sent 'Hello, RabbitMQ!'")
connection.close()