terraform {
  required_version = ">= 1.0.0"
}

resource "local_file" "harbornet_infra_plan" {
  filename = "${path.module}/harbornet_infrastructure_plan.txt"
  content  = "HarborNet Infrastructure Plan: Dockerized Flask app deployed on Kubernetes with Jenkins CI/CD, monitoring, logging, Vault secrets, and disaster recovery."
}
