# Cloudy Light Project
Welcome to the Cloudy Light project! This repository provides a distributed computing solution using Docker, Kubernetes, and RabbitMQ for efficient data processing and analysis.

File Structure

📂 project-root/

│── 📂 k8s/                     # Kubernetes Deployment Files

│   ├── final-analysis-deployment.yaml   # K8s configuration for final-analysis task

│   ├── drawer-deployment.yaml           # K8s configuration for drawer task

│   ├── data-processor-deployment.yaml   # K8s configuration for data-processor message queue

│   ├── rabbitmq-service.yaml            # RabbitMQ Service configuration

│   ├── rabbitmq-deployment.yaml         # K8s configuration for RabbitMQ message queue

│── 📂 Data_Processor/                  # Automation Scripts

│   ├── app.py                           # Python code for preprocessing data

│   ├── Dockerfile                       

│   ├── requirements.txt                # Required environment

│── 📂 Final_Analysis/                   # Configuration Files

│   ├── app.py                           # Python code for data computation

│   ├── Dockerfile                       

│   ├── requirements.txt                # Required environment

│── 📂 visualizer-outcome/               # Configuration Files

│   ├── app.py                           # Python code for visualization

│   ├── Dockerfile                       

│   ├── requirements.txt                # Required environment

│── README.md                            # Running and Deployment Instructions

│── requirements.txt                     # Python dependency libraries

│── docker-compose.yaml                  # For local testing

——————————————————————prepare—————————————

Running and Usage Instructions

Prerequisites

Docker

Kubernetes (kubectl)

RabbitMQ (optional for local testing)

——————————————————————————running————————

Build Docker Images

```python
docker build -t username/data_processor:latest ./Data_Processor
```
```python
docker build -t username/final-analysis:latest ./Final_Analysis
```
```python
docker build -t username/drawer:latest ./visualizer-outcome
```
——————————————————Push Docker Images to Registry————————————————
```python
docker push username/data_processor:latest
```
```python
docker push username/final-analysis:latest
```
```python
docker push username/drawer:latest
```
——————————————Deploy to Kubernetes————————————————
```python
kubectl apply -f ./k8s
```
————————————————————————————Check Pod Status————————————————
```python
kubectl get pods
```
————————————————Access RabbitMQ Management Interface————————————

kubectl port-forward svc/rabbitmq 15672:15672

Open http://localhost:15672 in your browser and log in with admin/password123.

————————————————————Clean Up————————————————————

To delete all deployed resources, run:

```python
kubectl delete all --all
```
——————————————————————Project Overview————————————————————————

This project is designed to handle large-scale data processing using a distributed computing approach. It leverages Docker for containerization, Kubernetes for orchestration, and RabbitMQ for message passing. The system is divided into three main components:

Data Processor: Handles data preprocessing and sends processed data to the message queue.

Final Analysis: Performs computations on the preprocessed data.

Visualizer: Generates visualizations from the computed data.

————————————————Features ————————————————————

Scalability: Easily scale the number of containers using Kubernetes.

Efficiency: Parallel processing of data using multiple containers.

Flexibility: Supports different data sources and processing tasks.

————————————————Future Work————————————————————————————

Improve data flow monitoring to prevent message congestion.

Enhance fault tolerance for network issues and data processing errors.

Implement data encryption for secure handling of sensitive information.



