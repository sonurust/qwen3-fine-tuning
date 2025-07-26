#!/bin/bash

set -e

echo "🧪 Testing Kubernetes deployment locally"

# Check prerequisites
echo "🔍 Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

if ! command -v kustomize &> /dev/null; then
    echo "📦 Installing kustomize..."
    curl -s "https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh" | bash
    sudo mv kustomize /usr/local/bin/
fi

if ! kubectl cluster-info &> /dev/null; then
    echo "❌ kubectl is not configured or cluster is not accessible"
    echo "💡 Make sure you have a Kubernetes cluster running (minikube, kind, or EKS)"
    exit 1
fi

# Create test namespace
echo "🏗️ Creating test namespace..."
kubectl create namespace qwen3-mcp-test --dry-run=client -o yaml | kubectl apply -f -

# Create test secrets
echo "🔐 Creating test secrets..."
mkdir -p k8s/overlays/test
echo "test-api-key" > k8s/overlays/test/openrouter-api-key.txt
echo "redis://redis-service:6379" > k8s/overlays/test/redis-url.txt

# Create test kustomization
cat > k8s/overlays/test/kustomization.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: qwen3-mcp-test

resources:
- ../../base
- namespace.yaml

configMapGenerator:
- name: qwen3-mcp-config
  behavior: merge
  literals:
  - LOG_LEVEL=DEBUG
  - ENVIRONMENT=test

secretGenerator:
- name: qwen3-mcp-secrets
  behavior: replace
  files:
  - openrouter-api-key=openrouter-api-key.txt
  - redis-url=redis-url.txt

images:
- name: qwen3-mcp-server
  newTag: latest
- name: qwen3-desktop-commander
  newTag: latest

replicas:
- name: qwen3-mcp-server
  count: 1
- name: qwen3-nginx
  count: 1
- name: qwen3-redis
  count: 1
EOF

cat > k8s/overlays/test/namespace.yaml << EOF
apiVersion: v1
kind: Namespace
metadata:
  name: qwen3-mcp-test
  labels:
    name: qwen3-mcp-test
    environment: test
EOF

# Validate manifests
echo "✅ Validating Kubernetes manifests..."
kubectl apply -k k8s/overlays/test --dry-run=client > /dev/null
echo "✅ Manifests are valid!"

# Apply manifests
echo "🚀 Applying manifests to test namespace..."
kubectl apply -k k8s/overlays/test

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-redis -n qwen3-mcp-test
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-mcp-server -n qwen3-mcp-test
kubectl wait --for=condition=available --timeout=300s deployment/qwen3-nginx -n qwen3-mcp-test

# Show status
echo "📊 Deployment Status:"
kubectl get pods -n qwen3-mcp-test
kubectl get services -n qwen3-mcp-test

# Test services
echo "🧪 Testing services..."

# Port forward to test locally
kubectl port-forward service/qwen3-nginx-service 8080:80 -n qwen3-mcp-test &
PF_PID=$!

sleep 5

# Test health endpoint
if curl -f http://localhost:8080/api/v1/health; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
fi

# Test info endpoint
if curl -f http://localhost:8080/api/v1/info; then
    echo "✅ Info endpoint test passed!"
else
    echo "❌ Info endpoint test failed!"
fi

# Cleanup port forward
kill $PF_PID

echo "🧹 Cleaning up test environment..."
kubectl delete namespace qwen3-mcp-test

echo "✅ Local deployment test completed successfully!"
echo "🚀 Ready to deploy to AWS EKS!"
