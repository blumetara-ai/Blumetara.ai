variable "aws_region" {
  description = "AWS Target Region for Deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project identifier used for tagging and resource naming"
  type        = string
  default     = "blumetara"
}

variable "environment" {
  description = "Target deployment environment"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the main VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets (hosting ALB)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets (hosting serverless ECS containers)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}
