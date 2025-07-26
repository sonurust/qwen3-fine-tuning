#!/bin/bash

set -e

# Configuration
ENVIRONMENT=${1:-production}
REGION="us-west-2"
CLUSTER_NAME="qwen3-mcp-cluster"

echo "🚀 Deploying Qwen3 MCP to Kubernetes"
echo "   Environment: $ENVIRONMENT"
echo "   Cluster: $CLUSTER_NAME"
echo "   Region: $REGION"

# Check if kubectl is configured
if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured. Run: aws eks update-kubeconfig --region $REGION --name $CLUSTER_NAME"
    exit 1
fi

# Check if kustomize is installed
if ! command -v kustomize &> /dev/null; then
    echo "📦 Installing kustomize..."
    curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
    sudo mv kustomize /usr/local/bin/
fi

# Create secrets (you should replace these with actual values)
echo "🔐 Creating secrets..."
kubectl create namespace qwen3-mcp-${ENVIRONMENT} --dry-run=client -o yaml | kubectl apply -f -

# Create secrets from files (make sure these files exist)
if [ ! -f "k8s/overlays/$ENVIRONMENT/openrouter-api-key.txt" ]; then
    echo "⚠️  Creating placeholder API key file. Replace with actual key!"
    echo "your-actual-openrouter-api-key" > "k8s/overlays/$ENVIRONMENT/openrouter-api-key.txt"
fi

if [ ! -f "k8s/overlays/$ENVIRONMENT/redis-url.txt" ]; then
    echo "redis://redis-service:6379" > "k8s/overlays/$ENVIRONMENT/redis-url.txt"
fi

# Apply the manifests
echo "📋 Applying Kubernetes manifests..."
kubectl apply -k k8s/overlays/$ENVIRONMENT

# Wait for deployments to be ready
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-mcp-server -n qwen3-mcp-${ENVIRONMENT}
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-nginx -n qwen3-mcp-${ENVIRONMENT}
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-redis -n qwen3-mcp-${ENVIRONMENT}

# Get service information
echo "🌐 Getting service information..."
kubectl get services -n qwen3-mcp-${ENVIRONMENT}
kubectl get ingress -n qwen3-mcp-${ENVIRONMENT}

# Get load balancer endpoint
LB_HOSTNAME=$(kubectl get ingress qwen3-mcp-ingress -n qwen3-mcp-${ENVIRONMENT} -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [ ! -z "$LB_HOSTNAME" ]; then
    echo "🔗 Load Balancer Endpoint: $LB_HOSTNAME"
else
    echo "⏳ Load Balancer is still provisioning. Check again in a few minutes."
fi

# Show pod status
echo "📊 Pod Status:"
kubectl get pods -n qwen3-mcp-${ENVIRONMENT}

echo "✅ Deployment complete!"
echo "📋 Next steps:"
echo "   1. Update your DNS records to point to the load balancer"
echo "   2. Update the certificate ARN in the ingress if using HTTPS"
echo "   3. Monitor the pods: kubectl get pods -n qwen3-mcp-${ENVIRONMENT} -w"
echo "   4. Check logs: kubectl logs -f deployment/qwen3-mcp-server -n qwen3-mcp-${ENVIRONMENT}"
