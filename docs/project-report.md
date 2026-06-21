# HarborNet - DevOps Project Exam Report

This report summarizes the deliverables, technical implementations, architecture configurations, and instructions for **HarborNet – Global Port & Maritime Logistics Control Platform**.

---

## 1. Executive Summary

HarborNet is a specialized DevOps-ready web application designed for global maritime logistics, port traffic tracking, and regulatory customs clearance. The application leverages a streamlined Python Flask and SQLite backend, styled with a custom high-fidelity Bootstrap 5 CSS layout. 

The primary goal of this project is to demonstrate standard DevOps workflows—incorporating containerization, continuous integration (CI) pipelines, infrastructure-as-code (IaC), container orchestration, and real-time monitoring/logging infrastructure.

---

## 2. Deliverables Checklist Status

| # | Deliverable File/Folder | Status | Location | Description |
|---|-------------------------|--------|----------|-------------|
| 1 | **Working Flask App**   | Active | [app.py](file:///Users/snehahande/Desktop/Devops/HarborNet/app.py) | Python Flask core backend, handling SQLite transactions and operator sessions. |
| 2 | **Application Styling** | Active | [style.css](file:///Users/snehahande/Desktop/Devops/HarborNet/static/style.css) | Custom CSS stylesheet defining maritime palettes and responsive navbar/sidebar grids. |
| 3 | **Dockerfile**          | Active | [Dockerfile](file:///Users/snehahande/Desktop/Devops/HarborNet/Dockerfile) | Base configuration to containerize the Flask application using Gunicorn. |
| 4 | **Jenkinsfile**         | Active | [Jenkinsfile](file:///Users/snehahande/Desktop/Devops/HarborNet/Jenkinsfile) | Declarative build pipeline automating install, lint, test, build, and deploy stages. |
| 5 | **Kubernetes Specs**    | Active | [k8s/](file:///Users/snehahande/Desktop/Devops/HarborNet/k8s/) | Deployment and service configurations with readiness/liveness checks. |
| 6 | **Terraform Code**      | Active | [terraform/](file:///Users/snehahande/Desktop/Devops/HarborNet/terraform/) | Provisioning templates to stand up VPC networks and EC2 container nodes in AWS. |
| 7 | **Monitoring Setup**    | Active | [monitoring/](file:///Users/snehahande/Desktop/Devops/HarborNet/monitoring/) | Scrape targets for Prometheus and dashboard schemas for Grafana. |
| 8 | **Log Collection**      | Active | [logging/](file:///Users/snehahande/Desktop/Devops/HarborNet/logging/) | Integration configurations for Filebeat, Logstash, and Elasticsearch (ELK). |
| 9 | **Secrets Management**  | Active | [vault/](file:///Users/snehahande/Desktop/Devops/HarborNet/vault/) | HashiCorp Vault authentication, policies, and agent container annotations. |
| 10| **Disaster Recovery**   | Active | [docs/](file:///Users/snehahande/Desktop/Devops/HarborNet/docs/) | RTO/RPO targets, database snapshots script, and server restore guidelines. |

---

## 3. Quick Start & Execution Guide

Follow these instructions to run the application across different environments.

### 3.1. Local Python Run (Development Mode)
To launch the system locally without container wrappers:
```bash
# Navigate to application folder
cd HarborNet/

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required libraries
pip install -r requirements.txt

# Run the Flask development server (port 5000)
python app.py
```
Open a browser and navigate to `http://localhost:5000`. Seed database records will be generated automatically. Log in with:
* **Username**: `admin`
* **Password**: `admin123`

---

### 3.2. Local Docker Run
To compile and test the container structure:
```bash
# Build the Docker image
docker build -t harbornet-platform:latest .

# Run the container mapping host port 5000 to Flask 5000
docker run -d -p 5000:5000 --name harbornet-app harbornet-platform:latest

# Check logs to verify server start
docker logs harbornet-app
```
Access the application at `http://localhost:5000`.

---

### 3.3. Kubernetes Orchestration Run
To instantiate the application inside a local Kubernetes cluster (e.g. Minikube):
```bash
# Create target secrets resource referenced in deployment configs
kubectl create secret generic harbornet-secrets --from-literal=secret-key="k8s-prod-secret-token"

# Apply resources
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check pods status
kubectl get pods -l app=harbornet

# Retrieve external connection port (for NodePort service type)
minikube service harbornet-service --url
```

---

### 3.4. Provision AWS Nodes via Terraform
To provision the remote server infrastructure:
```bash
# Initialize and fetch providers
cd terraform/
terraform init

# Validate configuration scripts
terraform validate

# Plan and execute creation commands
terraform apply -auto-approve
```
Upon completion, the terminal will print the public IP address of the newly provisioned host. The instance will automatically download Docker, build the application layer, and expose port 80.
