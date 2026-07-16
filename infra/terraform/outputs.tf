output "vpc_id" {
  description = "The ID of the provisioned custom VPC"
  value       = aws_vpc.main.id
}

output "alb_dns_name" {
  description = "The DNS entry URL of the Application Load Balancer"
  value       = aws_lb.api.dns_name
}

output "ecr_repository_url" {
  description = "The registry endpoint of the ECR Docker repository"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecs_cluster_name" {
  description = "The name of the serverless ECS Cluster"
  value       = aws_ecs_cluster.main.name
}
