# ELK Stack for HarborNet

## Purpose
ELK Stack is used for centralized log management and monitoring of the HarborNet application.

## ELK Components

### Elasticsearch
Stores application and system logs.

### Logstash
Collects and processes logs before sending them to Elasticsearch.

### Kibana
Provides dashboards and visualizations for log analysis.

## HarborNet Logging Flow

HarborNet Application
↓
Logstash
↓
Elasticsearch
↓
Kibana Dashboard

## Benefits

- Centralized log management
- Faster troubleshooting
- Error detection and monitoring
- Operational visibility

## Example Use Cases

- Detect failed login attempts
- Monitor application errors
- Analyze system activity
- Track service availability

## Viva Answer

ELK Stack helps HarborNet collect, store, analyze, and visualize logs from different services through a centralized monitoring platform.
