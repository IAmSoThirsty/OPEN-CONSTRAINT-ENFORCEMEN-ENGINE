#!/bin/bash
set -e

echo "Building Docker image..."
docker build -t constraint-enforcement-engine:latest .

echo ""
echo "Docker image built successfully!"
echo "To run locally: docker run -p 5000:5000 -v $(pwd)/policies:/app/policies:ro constraint-enforcement-engine:latest"
