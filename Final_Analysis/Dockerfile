# 数据预处理容器
FROM python:3.9-slim

# 设置工作目录为 /Data_Processor
WORKDIR /app

# 安装必要的库
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制数据预处理脚本到容器
COPY app.py /app/app.py

# 设置环境变量
ENV RABBITMQ_HOST rabbitmq
ENV RABBITMQ_USER admin
ENV RABBITMQ_PASS password123

# 运行数据预处理脚本
CMD ["python", "app.py"]
