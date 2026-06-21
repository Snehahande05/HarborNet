# Disaster Recovery & Business Continuity Plan

This document details the disaster recovery (DR) strategies, backup workflows, and server restoration protocols for the **HarborNet – Global Port & Maritime Logistics Control Platform**.

---

## 1. Disaster Recovery Goals

To support maritime logistics, we define the following objectives:
* **Recovery Point Objective (RPO)**: **4 Hours**. Maximum allowable period of database updates lost during outage.
* **Recovery Time Objective (RTO)**: **30 Minutes**. Maximum allowable application server downtime before failover site takes traffic.

---

## 2. SQLite Database Backup Strategy

Since HarborNet uses a local SQLite database (`harbornet.db`), backups must be captured using atomic file copies to prevent database corruption.

### 2.1. Online Database Backup Script
Using SQLite's `.backup` command ensures that write operations are not blocked, and backup is consistent.

Create backup shell script `bin/db-backup.sh`:
```bash
#!/bin/bash
# Configuration
DB_PATH="/app/harbornet.db"
BACKUP_DIR="/var/backups/harbornet"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/harbornet_backup_${TIMESTAMP}.sqlite"
S3_BUCKET="s3://harbornet-disaster-recovery-backups/database"

# Ensure local backup directory exists
mkdir -p "${BACKUP_DIR}"

# Execute safe, atomic SQLite backup
sqlite3 "${DB_PATH}" ".backup '${BACKUP_FILE}'"

# Compress backup
gzip "${BACKUP_FILE}"

# Upload to Amazon S3 bucket (or secure block storage)
aws s3 cp "${BACKUP_FILE}.gz" "${S3_BUCKET}/"

# Clean up local backups older than 7 days
find "${BACKUP_DIR}" -name "*.gz" -mtime +7 -exec rm {} \;
```

Set this script to run as a cron job every 4 hours.

---

## 3. High Availability & Regional Failover

If the primary infrastructure (configured via Terraform in AWS `us-east-1` region) experiences a catastrophic hardware failure, operators must execute the following failover pipeline:

```
                  +--------------------------------+
                  |  Users (Browser Client Access) |
                  +--------------------------------+
                                  |
                                  | [DNS Route 53 Traffic Policy]
                                  v
                  +--------------------------------+
                  |   AWS Route 53 Health Checks   |
                  +--------------------------------+
                     /                          \
       (Active)     /                            \     (Passive Standby)
                   v                              v
    +-----------------------------+        +-----------------------------+
    |  Primary Node: us-east-1    |        |  Secondary Node: us-west-2  |
    |  - EC2 Container Hosting    |        |  - Standby Deployment       |
    |  - SQLite DB Active Updates |        |  - Restores DB from S3      |
    +-----------------------------+        +-----------------------------+
```

1. **DNS Health Probes**: Route 53 is configured with an active-passive failover routing policy, pinging `/health` every 10 seconds.
2. **Automated Redirection**: If the primary endpoint fails to respond for 3 consecutive intervals, Route 53 updates DNS maps to point traffic to the secondary standby node in region `us-west-2`.

---

## 4. Disaster Recovery Restoration Procedure

In the event of database loss or migration to new compute nodes, operators should execute these recovery steps:

### Step 4.1: Deploy Standby Compute Node
Run Terraform in the recovery region to instantiate the security controls and the target EC2 node:
```bash
cd terraform/
terraform init
terraform apply -var="aws_region=us-west-2" -var="instance_type=t3.small" -auto-approve
```

### Step 4.2: Retrieve Database Snapshot
SSH into the new instance, retrieve the latest backup archive from the secure S3 storage bucket, and decompress it:
```bash
# Fetch latest backup object from S3
aws s3 cp s3://harbornet-disaster-recovery-backups/database/harbornet_backup_latest.sqlite.gz /tmp/

# Extract archive
gunzip /tmp/harbornet_backup_latest.sqlite.gz

# Stop primary docker container
docker stop harbornet || true

# Overwrite active database file inside container volume path
mv /tmp/harbornet_backup_latest.sqlite /var/lib/docker/volumes/harbornet_data/_data/harbornet.db

# Restart primary container
docker start harbornet
```

### Step 4.3: Verify System Integration
Confirm database operations by querying the health check API:
```bash
curl -f http://localhost:5000/health
# Expected Output: {"status":"healthy","database":"connected"}
```
Once verified, switch DNS traffic tags to make the standby node primary.
