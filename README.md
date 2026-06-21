# HarborNet - Global Port & Maritime Logistics Control Platform

## Project Overview

HarborNet is a cloud-native maritime logistics platform designed to manage vessel operations, cargo tracking, customs processing, warehouse coordination, and logistics monitoring across global ports.

The project demonstrates a complete DevOps lifecycle using Docker, Jenkins, Kubernetes, Terraform, Prometheus, Grafana, ELK Stack, and Vault.

---

## Technology Stack

* Flask (Python)
* SQLite Database
* Docker
* Jenkins
* Kubernetes
* Terraform
* Prometheus
* Grafana
* ELK Stack
* HashiCorp Vault
* GitHub

---

## Application Features

* User Login
* User Registration
* Cargo Tracking Dashboard
* Vessel Monitoring
* Port Operations Dashboard
* System Health Monitoring

---

## DevOps Implementation

### Docker

Containerized the HarborNet application.

### Jenkins

Implemented CI/CD pipeline for automated build and deployment.

### Kubernetes

Deployed HarborNet using Kubernetes Deployment and Service.

### Terraform

Implemented Infrastructure as Code (IaC).

### Prometheus & Grafana

Configured monitoring and dashboard visualization.

### ELK Stack

Implemented centralized log management.

### Vault

Secured application secrets and credentials.

---

## Kubernetes Scaling

Deployment scaled from 2 replicas to 3 replicas demonstrating horizontal scalability.

---

## Disaster Recovery Plan

* Multiple application replicas
* Kubernetes self-healing
* Container redeployment
* Centralized monitoring
* Backup and recovery procedures

---

## Project Architecture

User
↓
HarborNet Web Application
↓
Docker Container
↓
Kubernetes Cluster
↓
Monitoring (Prometheus + Grafana)
↓
Logging (ELK Stack)
↓
Secret Management (Vault)

---

## Outcome

Successfully implemented a production-style DevOps pipeline demonstrating automation, deployment, monitoring, security, scalability, and operational resilience for HarborNet.

