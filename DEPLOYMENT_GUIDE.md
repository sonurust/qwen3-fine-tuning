# Qwen3 MCP Server - AWS EKS Deployment Guide

This guide will walk you through deploying the Qwen3 MCP Server with DesktopCommanderMCP integration to AWS EKS.

## Prerequisites

1. **AWS CLI configured** with appropriate permissions
2. **Docker** installed and running
3. **Helm** installed (for AWS Load Balancer Controller)
4. **kubectl** installed
5. **eksctl** installed

## Step 1: Setup AWS EKS Cluster

```bash
# Run the cluster setup script
./k8s/scripts/setup-eks-cluster.sh
```

This script will:
- Create an EKS cluster with managed node groups
- Install AWS Load Balancer Controller
- Install metrics server for HPA
- Create ECR repositories for your images
- Configure OIDC provider

## Step 2: Configure kubectl

```bash
# Update your kubeconfig
aws eks update-kubeconfig --region us-west-2 --name qwen3-mcp-cluster

# Verify connection
kubectl get nodes
```

## Step 3: Build and Push Docker Images

```bash
# Build and push images with version tag
./k8s/scripts/build-and-push.sh v1.0.0

# Or use latest tag
./k8s/scripts/build-and-push.sh latest
```

## Step 4: Configure Secrets

### 4.1 Create API Key Files

```bash
# Create the production secrets directory if it doesn't exist
mkdir -p k8s/overlays/production

# Add your actual OpenRouter API key
echo "your-actual-openrouter-api-key-here" > k8s/overlays/production/openrouter-api-key.txt

# Configure Redis URL (using in-cluster Redis)
echo "redis://redis-service:6379" > k8s/overlays/production/redis-url.txt
```

### 4.2 Update Certificate ARN (Optional - for HTTPS)

Edit `k8s/base/ingress.yaml` and update the certificate ARN:

```yaml
alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:YOUR-ACCOUNT-ID:certificate/YOUR-CERT-ID
```

### 4.3 Update Domain Names

Edit `k8s/base/ingress.yaml` and update the host names:

```yaml
spec:
  rules:
  - host: qwen3-mcp.yourdomain.com  # Update this
  - host: api.qwen3-mcp.yourdomain.com  # Update this
```

## Step 5: Deploy to Production

```bash
# Deploy to production environment
./k8s/scripts/deploy.sh production
```

This will:
- Create the production namespace
- Apply all Kubernetes manifests
- Wait for deployments to be ready
- Show service and ingress information

## Step 6: Verify Deployment

```bash
# Check pod status
kubectl get pods -n qwen3-mcp-prod

# Check services
kubectl get services -n qwen3-mcp-prod

# Check ingress
kubectl get ingress -n qwen3-mcp-prod

# Get load balancer endpoint
kubectl get ingress qwen3-mcp-ingress -n qwen3-mcp-prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

## Step 7: Test the Deployment

```bash
# Get the load balancer URL
LB_URL=$(kubectl get ingress qwen3-mcp-ingress -n qwen3-mcp-prod -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl http://$LB_URL/api/v1/health

# Test API info endpoint
curl http://$LB_URL/api/v1/info

# Test MCP functionality
curl -X POST http://$LB_URL/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": {"type": "text", "text": "What is the weather in Tokyo?"}}]}'
```

## Step 8: Configure DNS (Optional)

Point your domain to the load balancer:

```bash
# Get the load balancer hostname
kubectl get ingress qwen3-mcp-ingress -n qwen3-mcp-prod

# Create CNAME records in your DNS provider:
# qwen3-mcp.yourdomain.com -> your-alb-hostname.elb.amazonaws.com
# api.qwen3-mcp.yourdomain.com -> your-alb-hostname.elb.amazonaws.com
```

## Architecture Overview

```
Internet
    │
    ▼
AWS ALB (Load Balancer)
    │
    ▼
┌─────────────────────────────────────────┐
│              EKS Cluster                │
│                                         │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │   Nginx     │    │  MCP Server x3  │ │
│  │  (2 pods)   │───▶│   (3-10 pods)   │ │
│  └─────────────┘    └─────────────────┘ │
│                              │          │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │    Redis    │    │Desktop Commander│ │
│  │  (1 pod)    │    │   (2 pods)      │ │
│  └─────────────┘    └─────────────────┘ │
└─────────────────────────────────────────┘
```

## Monitoring and Logging

### View Logs

```bash
# MCP Server logs
kubectl logs -f deployment/qwen3-mcp-server -n qwen3-mcp-prod

# Nginx logs
kubectl logs -f deployment/qwen3-nginx -n qwen3-mcp-prod

# Desktop Commander logs
kubectl logs -f deployment/qwen3-desktop-commander -n qwen3-mcp-prod
```

### Monitor Resources

```bash
# Watch pods
kubectl get pods -n qwen3-mcp-prod -w

# Check HPA status
kubectl get hpa -n qwen3-mcp-prod

# Check resource usage
kubectl top pods -n qwen3-mcp-prod
kubectl top nodes
```

## Scaling

### Manual Scaling

```bash
# Scale MCP server
kubectl scale deployment qwen3-mcp-server --replicas=5 -n qwen3-mcp-prod

# Scale Nginx
kubectl scale deployment qwen3-nginx --replicas=3 -n qwen3-mcp-prod
```

### Auto-scaling

HPA is configured to automatically scale based on CPU and memory:

- **MCP Server**: 3-10 replicas (70% CPU, 80% memory)
- **Nginx**: 2-5 replicas (60% CPU)

## Security Considerations

1. **Secrets Management**: Consider using AWS Secrets Manager or Parameter Store
2. **Network Policies**: Implement Kubernetes Network Policies for isolation
3. **RBAC**: Configure proper Role-Based Access Control
4. **Pod Security**: SecurityContext is configured with non-root user
5. **Container Scanning**: Scan images for vulnerabilities before deployment

## Troubleshooting

### Common Issues

1. **Pods not starting**: Check logs and resource limits
2. **Load balancer not accessible**: Verify security groups and subnets
3. **Certificate issues**: Ensure ACM certificate is validated
4. **DNS resolution**: Check CoreDNS configuration

### Debug Commands

```bash
# Describe pod for events
kubectl describe pod <pod-name> -n qwen3-mcp-prod

# Get detailed service info
kubectl describe service qwen3-nginx-service -n qwen3-mcp-prod

# Check ingress events
kubectl describe ingress qwen3-mcp-ingress -n qwen3-mcp-prod

# Check AWS Load Balancer Controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller
```

## Cleanup

To remove the entire deployment:

```bash
# Delete the application
kubectl delete -k k8s/overlays/production

# Delete the EKS cluster (this will take 10-15 minutes)
eksctl delete cluster --name qwen3-mcp-cluster --region us-west-2

# Delete ECR repositories
aws ecr delete-repository --repository-name qwen3-mcp-server --region us-west-2 --force
aws ecr delete-repository --repository-name qwen3-desktop-commander --region us-west-2 --force
```

## Cost Optimization

1. **Use Spot Instances**: Configure node groups with spot instances
2. **Right-size Resources**: Adjust CPU/memory requests and limits
3. **Cluster Autoscaler**: Install cluster autoscaler to scale nodes
4. **Reserved Instances**: Use RIs for long-running workloads

## Next Steps

1. Set up monitoring with Prometheus and Grafana
2. Configure log aggregation with CloudWatch or ELK stack
3. Implement CI/CD pipeline with GitHub Actions or AWS CodePipeline
4. Set up backup strategies for persistent data
5. Configure disaster recovery procedures
