terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.20"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }

  backend "s3" {
    # Configure this for your environment
    bucket = "qwen3-mcp-terraform-state"
    key    = "terraform.tfstate"
    region = "us-west-2"
    
    # Enable state locking
    dynamodb_table = "qwen3-mcp-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "qwen3-mcp"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local values
locals {
  cluster_name = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  project_name        = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = data.aws_availability_zones.available.names
  
  tags = local.common_tags
}

# ECR Module
module "ecr" {
  source = "./modules/ecr"
  
  project_name = var.project_name
  environment  = var.environment
  
  repositories = [
    "qwen3-mcp-server",
    "qwen3-desktop-commander"
  ]
  
  tags = local.common_tags
}

# EKS Module
module "eks" {
  source = "./modules/eks"
  
  project_name    = var.project_name
  environment     = var.environment
  cluster_name    = local.cluster_name
  cluster_version = var.kubernetes_version
  
  vpc_id                    = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnet_ids
  control_plane_subnet_ids = module.vpc.public_subnet_ids
  
  node_groups = var.node_groups
  
  tags = local.common_tags
  
  depends_on = [module.vpc]
}

# Monitoring Module
module "monitoring" {
  source = "./modules/monitoring"
  
  project_name = var.project_name
  environment  = var.environment
  cluster_name = local.cluster_name
  
  tags = local.common_tags
  
  depends_on = [module.eks]
}
