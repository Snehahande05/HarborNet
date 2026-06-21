# Terraform Provider Configuration for AWS
terraform {
  required_version = ">= 1.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Input Variables
variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "Target AWS Region"
}

variable "instance_type" {
  type        = string
  default     = "t3.micro"
  description = "EC2 Instance Size"
}

# VPC Configuration
resource "aws_vpc" "harbornet_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = {
    Name = "harbornet-vpc"
  }
}

# Internet Gateway for public subnet access
resource "aws_internet_gateway" "harbornet_gw" {
  vpc_id = aws_vpc.harbornet_vpc.id
  tags = {
    Name = "harbornet-gateway"
  }
}

# Public Subnet
resource "aws_subnet" "harbornet_subnet" {
  vpc_id                  = aws_vpc.harbornet_vpc.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"
  tags = {
    Name = "harbornet-public-subnet"
  }
}

# Route Table mapping public traffic to Internet Gateway
resource "aws_route_table" "harbornet_rt" {
  vpc_id = aws_vpc.harbornet_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.harbornet_gw.id
  }
  tags = {
    Name = "harbornet-route-table"
  }
}

resource "aws_route_table_association" "harbornet_rta" {
  subnet_id      = aws_subnet.harbornet_subnet.id
  route_table_id = aws_route_table.harbornet_rt.id
}

# Security Group Rules (allowing HTTP, SSH, Flask Port)
resource "aws_security_group" "harbornet_sg" {
  name        = "harbornet-security-group"
  description = "Allow inbound SSH, HTTP, and Flask container traffic"
  vpc_id      = aws_vpc.harbornet_vpc.id

  ingress {
    description = "SSH access"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Standard HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Flask Application Server"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "harbornet-security-group"
  }
}

# EC2 Instance Provisioning
resource "aws_instance" "harbornet_host" {
  ami                    = "ami-0c7217cdde317cfec" # Amazon Linux 2 AMI in us-east-1
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.harbornet_subnet.id
  vpc_security_group_ids = [aws_security_group.harbornet_sg.id]

  # User Data Script to configure Docker and deploy HarborNet Container
  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              amazon-linux-extras install docker -y
              service docker start
              usermod -a -G docker ec2-user
              
              # Run HarborNet application directly from public registry
              # (Replacing with local image or CI build as needed)
              docker run -d -p 80:5000 --name harbornet --restart unless-stopped your-dockerhub-username/harbornet-platform:latest
              EOF

  tags = {
    Name = "harbornet-application-node"
  }
}

# Output variables to return public connection details
output "application_public_ip" {
  value       = aws_instance.harbornet_host.public_ip
  description = "Public IP Address of HarborNet server node"
}

output "application_url" {
  value       = "http://${aws_instance.harbornet_host.public_ip}"
  description = "Live access URL of the deployed application"
}
