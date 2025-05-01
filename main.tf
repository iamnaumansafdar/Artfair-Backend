# Define AWS provider and set the region for resource provisioning
provider "aws" {
  region = "us-east-1"
}

# Create a Virtual Private Cloud to isolate the infrastructure
resource "aws_vpc" "default" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name = "ArtFair_CoreAPI_Dev_VPC"
  }
}

# Internet Gateway to allow internet access to the VPC
resource "aws_internet_gateway" "default" {
  vpc_id = aws_vpc.default.id
  tags = {
    Name = "ArtFair_EC2_Internet_Gateway"
  }
}

# Route table for controlling traffic leaving the VPC
resource "aws_route_table" "default" {
  vpc_id = aws_vpc.default.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.default.id
  }
  tags = {
    Name = "ArtFair_EC2_Route_Table"
  }
}

# Subnet within VPC for resource allocation, in availability zone us-east-1a
resource "aws_subnet" "subnet1" {
  vpc_id                  = aws_vpc.default.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = false
  availability_zone       = "us-east-1a"
  tags = {
    Name = "ArtFair_EC2_Subnet_1"
  }
}

# Another subnet for redundancy, in availability zone us-east-1b
resource "aws_subnet" "subnet2" {
  vpc_id                  = aws_vpc.default.id
  cidr_block              = "10.0.2.0/24"
  map_public_ip_on_launch = false
  availability_zone       = "us-east-1b"
  tags = {
    Name = "ArtFair_EC2_Subnet_2"
  }
}

# Associate subnets with route table for internet access
resource "aws_route_table_association" "a" {
  subnet_id      = aws_subnet.subnet1.id
  route_table_id = aws_route_table.default.id
}
resource "aws_route_table_association" "b" {
  subnet_id      = aws_subnet.subnet2.id
  route_table_id = aws_route_table.default.id
}



# Security group for EC2 instance
resource "aws_security_group" "ec2_sg" {
  vpc_id = aws_vpc.default.id
  ingress {
    from_port   = 22
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Only allow HTTPS traffic from everywhere
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "EC2_Security_Group"
  }
}

# Define variable for RDS password to avoid hardcoding secrets
variable "secret_key" {
  description = "The Secret Key for Django"
  type        = string
  sensitive   = true
}

# Add variable for bucket name
variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
  default     = "artfair-development"  # Your bucket name from Django settings
}

# EC2 instance for the local web app
resource "aws_instance" "web" {
  ami                    = "ami-0a7a4e87939439934"  # Ubuntu ARM
  instance_type          = "m8g.2xlarge"
  subnet_id              = aws_subnet.subnet1.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]

  root_block_device {
    volume_size = 20 # 20 GB
    volume_type = "gp3"
    delete_on_termination = true
    tags = {
      Name = "ArtFair_CoreAPI_Dev_Root_Volume"
    }
  }


  associate_public_ip_address = true
  user_data_replace_on_change = true

  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  user_data = <<-EOF
    #!/bin/bash
    set -ex

    # Update system
    sudo apt-get update
    sudo apt-get install -y unzip curl apt-transport-https ca-certificates software-properties-common

    # Install AWS CLI v2 for ARM
    sudo curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
    sudo unzip awscliv2.zip
    sudo ./aws/install

    # Install Docker
    sudo curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo systemctl start docker
    sudo systemctl enable docker

    # Wait for docker to be ready
    sleep 10

    # ECR Login (using non-interactive mode)
    sudo aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 851725533006.dkr.ecr.us-east-1.amazonaws.com

    # Pull the Docker image
    sudo docker pull 851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev:latest

    # Run the Docker container with the correct Django secret key env var
    sudo docker run -d -p 80:8080 \
    --env DJANGO_SECRET_KEY="django-insecure-wlgjuo53y49%-4y5(!%ksylle_ud%b=7%__@9hh+@$d%_^y3s!" \
    --env DB_NAME=djangodb \
    --env DB_USER_NM=artfair \
    --env DB_USER_PW=pass1234 \
    --env DB_IP=54.173.134.34 \
    --env DB_PORT=5432 \
    851725533006.dkr.ecr.us-east-1.amazonaws.com/core-api-dev:latest

    # Clean up installation files
    rm -rf aws awscliv2.zip get-docker.sh
    EOF

  tags = {
    Name = "Django_EC2_Complete_Server"
  }
}

# IAM role for EC2 instance to access ECR
resource "aws_iam_role" "ec2_role" {
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Effect = "Allow"
    }]
  })

  tags = {
    Name = "ArtFair_EC2_Role"
  }
}

# Add S3 policy for EC2 role
resource "aws_iam_role_policy" "s3_policy" {
  name = "s3_access_policy"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.bucket_name}/*",
          "arn:aws:s3:::${var.bucket_name}"
        ]
      }
    ]
  })
}

# Attach the AmazonEC2ContainerRegistryReadOnly policy to the role
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# IAM instance profile for EC2 instance
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "core_api_ec2_complete_profiles"
  role = aws_iam_role.ec2_role.name
}