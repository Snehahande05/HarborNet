# System Architecture - HarborNet Platform

This document describes the structural layout, logical architecture, data design, and deployment design of the **HarborNet – Global Port & Maritime Logistics Control Platform**.

---

## 1. High-Level Architecture Overview

HarborNet uses a multi-tier architectural pattern. The system consists of a web client, a Python Flask application server, an SQLite relational database, and supporting infrastructure layers.

```mermaid
graph TD
    Client[Web Browser Client] -->|HTTP / HTTPS: Port 80/5000| WebApp[Flask Application Server]
    
    subgraph Web Application Layer
        WebApp -->|Route Mapping| Auth[Auth Controller]
        WebApp -->|Route Mapping| Fleet[Fleet Manager]
        WebApp -->|Route Mapping| Cargo[Cargo Tracker]
        WebApp -->|Route Mapping| Customs[Customs Auditor]
        WebApp -->|Route Mapping| PortSys[Port Hub System]
    end
    
    subgraph Storage Layer
        Auth -->|Read/Write| DB[(SQLite Database)]
        Fleet -->|Read/Write| DB
        Cargo -->|Read/Write| DB
        Customs -->|Read/Write| DB
        PortSys -->|Read/Write| DB
    end
    
    subgraph Security & Monitoring
        K8sEnv[Kubernetes Probes] -->|Uptime Check: /health| WebApp
        Prom[Prometheus] -->|Scrape: /health| WebApp
        Vault[HashiCorp Vault] -->|Inject Env Secret| WebApp
    end
```

---

## 2. Component Design

1. **User Client**: Serves responsive HTML/Bootstrap 5 templates to operators.
2. **Application Server (Flask)**:
   - **Authentication System**: Secures access using hashed passwords (`werkzeug.security`) and cookie-based session state (`flask.session`).
   - **Health Endpoint (`/health`)**: Public API returning JSON server state for load balancers and container orchestrators.
   - **Database Helpers**: Establishes SQLite connection streams, initializes table structures, and seeds mock records on startup.
3. **Database (SQLite)**: File-based relational storage engine (`harbornet.db`). Extremely fast, lightweight, and zero-configuration, making it perfect for rapid deployments.

---

## 3. Data Relationships (ERD)

The database tables are linked relationally through IDs and string keys to coordinate real-time tracking:

```mermaid
erDiagram
    users {
        int id PK
        string username
        string email
        string password
    }
    
    vessels {
        int id PK
        string vessel_name
        string imo_number UK
        string port_name
        string berth_number
        string cargo_type
        string status
    }
    
    cargo {
        int id PK
        string container_id UK
        string vessel_name FK
        string origin
        string destination
        string current_location
        string status
    }
    
    customs {
        int id PK
        string container_id FK
        string clearance_status
        string officer_name
        string remarks
    }
    
    ports {
        int id PK
        string port_name UK
        string country
        string operational_status
        string congestion_level
    }

    vessels ||--o{ cargo : "transports"
    ports ||--o{ vessels : "hosts"
    cargo ||--|| customs : "triggers inspection"
```

---

## 4. Infrastructure Deployment Lifecycle

The HarborNet platform implements DevOps infrastructure-as-code principles at every stage of development:

```
+------------+     +-------------------+     +------------------+     +------------------------+
| Local Git  | --> | Jenkins CI Build  | --> | Docker Image Hub | --> | Kubernetes Cluster /   |
| Commit     |     | (Syntax & Docker) |     | (Version Tags)   |     | AWS EC2 Node (Terraform)|
+------------+     +-------------------+     +------------------+     +------------------------+
```

* **Version Control**: Infrastructure state stored in git alongside application code.
* **CI/CD Pipeline**: Jenkins Declarative Pipeline automates quality gates, dependencies management, and image containerization.
* **Orchestration**: Kubernetes schedules redundant Pods, manages port mappings, and isolates secret files.
* **Infrastructure Provisioning**: Terraform structures AWS environments (VPCs, Subnets, Routing, and Security Policies).
* **Uptime Scrapes**: Prometheus logs metric charts directly from `/health` hooks.
