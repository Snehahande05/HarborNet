# ELK Stack Log Aggregation & Analysis Guide

This guide details the integration of the **ELK (Elasticsearch, Logstash, Kibana) Stack** to aggregate, parse, and monitor application stdout and access logs for the HarborNet Maritime Control Platform.

```
+------------------+     +------------------+     +-------------------+     +------------------+
|  HarborNet App   | --> | Filebeat Agent   | --> | Logstash Pipeline | --> |  Elasticsearch   |
| (Flask/Gunicorn) |     | (Log Harvester)  |     | (Filter & Parse)  |     | (Storage/Index)  |
+------------------+     +------------------+     +-------------------+     +------------------+
                                                                                     |
                                                                                     v
                                                                            +------------------+
                                                                            |   Kibana UI      |
                                                                            | (Visualization)  |
                                                                            +------------------+
```

---

## 1. Filebeat Collector Configuration
Filebeat runs as a DaemonSet or sidecar container in Kubernetes, harvesting logs directly from the container path `/var/log/containers/*` or container stdout paths.

Create `/etc/filebeat/filebeat.yml`:

```yaml
filebeat.inputs:
- type: container
  enabled: true
  paths:
    - /var/log/containers/harbornet-*.log
  processors:
    - add_kubernetes_metadata:
        host: ${NODE_NAME}
        matchers:
        - logs_path:
            resource_type: "pod"

output.logstash:
  hosts: ["logstash-service.logging.svc.cluster.local:5044"]
```

---

## 2. Logstash Pipeline Configuration
Logstash listens for incoming Filebeat logs, parses them into structured JSON elements (extracting request methods, statuses, and execution errors), and indexes them.

Create `/etc/logstash/conf.d/harbornet-pipeline.conf`:

```conf
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse standard Flask/Gunicorn HTTP access logs
  if [kubernetes][container][name] == "harbornet" {
    grok {
      match => { 
        "message" => "%{IPORHOST:client_ip} - - \[%{HTTPDATE:timestamp}\] \"%{WORD:method} %{URIPATHPARAM:request_path} HTTP/%{NUMBER:http_version}\" %{NUMBER:status_code} %{NUMBER:response_bytes}" 
      }
      add_field => { "app_name" => "harbornet" }
    }
    
    # Parse response integers for Grafana analytics
    mutate {
      convert => {
        "status_code" => "integer"
        "response_bytes" => "integer"
      }
    }
    
    date {
      match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
      target => "@timestamp"
    }
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch-service.logging.svc.cluster.local:9200"]
    index => "harbornet-logs-%{+YYYY.MM.dd}"
    # If security is configured:
    # user => "elastic"
    # password => "${ELASTIC_PASSWORD}"
  }
}
```

---

## 3. Kibana Log Search & Dashboarding
1. **Create Index Pattern**:
   - Access the Kibana control panel (`http://localhost:5601`).
   - Navigate to **Management** &rarr; **Stack Management** &rarr; **Index Patterns**.
   - Create an index pattern matching `harbornet-logs-*` with `@timestamp` as the primary time field.
2. **Standard Discover Queries**:
   - Filter HTTP error status logs: `status_code >= 400`
   - Monitor database updates: `message : "DB" or message : "sqlite"`
   - Watch failed login attempts: `message : "Invalid operator"`
3. **Recommended Visualizations**:
   - **Log Volume Rate**: Area chart tracking request counts over time.
   - **HTTP Status Code Breakdown**: Pie chart illustrating percentage of `200`, `302`, `404`, and `500` codes.
   - **Geolocation Map**: Map visualizing requests based on client IPs.
