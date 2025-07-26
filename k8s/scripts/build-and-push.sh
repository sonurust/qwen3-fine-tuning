#!/bin/bash

set -e

# Configuration
REGION="us-west-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
VERSION=${1:-latest}

echo "🐳 Building and pushing Docker images to ECR"
echo "   Registry: $ECR_REGISTRY"
echo "   Version: $VERSION"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and push MCP server
echo "🏗️  Building qwen3-mcp-server..."
docker build -t qwen3-mcp-server:$VERSION .
docker tag qwen3-mcp-server:$VERSION $ECR_REGISTRY/qwen3-mcp-server:$VERSION
docker tag qwen3-mcp-server:$VERSION $ECR_REGISTRY/qwen3-mcp-server:latest

echo "📤 Pushing qwen3-mcp-server..."
docker push $ECR_REGISTRY/qwen3-mcp-server:$VERSION
docker push $ECR_REGISTRY/qwen3-mcp-server:latest

# Build and push Desktop Commander
echo "🏗️  Building qwen3-desktop-commander..."
docker build -t qwen3-desktop-commander:$VERSION -f DesktopCommanderMCP/Dockerfile DesktopCommanderMCP/
docker tag qwen3-desktop-commander:$VERSION $ECR_REGISTRY/qwen3-desktop-commander:$VERSION
docker tag qwen3-desktop-commander:$VERSION $ECR_REGISTRY/qwen3-desktop-commander:latest

echo "📤 Pushing qwen3-desktop-commander..."
docker push $ECR_REGISTRY/qwen3-desktop-commander:$VERSION
docker push $ECR_REGISTRY/qwen3-desktop-commander:latest

echo "✅ Docker images pushed successfully!"
echo "📋 Images:"
echo "   $ECR_REGISTRY/qwen3-mcp-server:$VERSION"
echo "   $ECR_REGISTRY/qwen3-desktop-commander:$VERSION"

# Update kustomization files with new image tags
echo "🔄 Updating kustomization files..."
sed -i.bak "s|newTag: .*|newTag: $VERSION|g" k8s/overlays/production/kustomization.yaml
echo "✅ Kustomization files updated with version $VERSION"
