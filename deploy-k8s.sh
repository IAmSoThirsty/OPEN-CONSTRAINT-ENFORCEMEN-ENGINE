#!/bin/bash
set -e

echo "Deploying to Kubernetes..."

kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/policies-configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/networkpolicy.yaml

echo ""
echo "Deployment complete!"
echo "Check status with: kubectl get pods -n constraint-enforcement"
echo "Check logs with: kubectl logs -n constraint-enforcement -l app=constraint-enforcement-engine"
