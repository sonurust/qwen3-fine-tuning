#!/bin/bash

set -e

# Configuration
CLUSTER_NAME="qwen3-mcp-cluster"
REGION="us-west-2"
NODE_GROUP_NAME="qwen3-workers"
KUBERNETES_VERSION="1.28"

echo "🚀 Setting up EKS cluster for Qwen3 MCP deployment"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if eksctl is installed
if ! command -v eksctl &> /dev/null; then
    echo "📦 Installing eksctl..."
    curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
    sudo mv /tmp/eksctl /usr/local/bin
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "📦 Installing kubectl..."
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
fi

echo "🏗️  Creating EKS cluster..."
eksctl create cluster \
  --name $CLUSTER_NAME \
  --region $REGION \
  --version $KUBERNETES_VERSION \
  --nodegroup-name $NODE_GROUP_NAME \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 10 \
  --managed \
  --asg-access \
  --external-dns-access \
  --full-ecr-access \
  --appmesh-access \
  --alb-ingress-access

echo "🔧 Installing AWS Load Balancer Controller..."
eksctl utils associate-iam-oidc-provider --region=$REGION --cluster=$CLUSTER_NAME --approve

curl -o iam_policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.7.2/docs/install/iam_policy.json

aws iam create-policy \
    --policy-name AWSLoadBalancerControllerIAMPolicy \
    --policy-document file://iam_policy.json

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

eksctl create iamserviceaccount \
  --cluster=$CLUSTER_NAME \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --role-name AmazonEKSLoadBalancerControllerRole \
  --attach-policy-arn=arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

echo "📦 Installing AWS Load Balancer Controller via Helm..."
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$CLUSTER_NAME \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller

echo "📊 Installing metrics server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

echo "🎯 Setting up ECR repositories..."
aws ecr create-repository --repository-name qwen3-mcp-server --region $REGION || true
aws ecr create-repository --repository-name qwen3-desktop-commander --region $REGION || true

echo "✅ EKS cluster setup complete!"
echo "📋 Cluster details:"
echo "   Name: $CLUSTER_NAME"
echo "   Region: $REGION"
echo "   Kubernetes version: $KUBERNETES_VERSION"
echo ""
echo "🔗 Update your kubeconfig:"
echo "   aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME"
