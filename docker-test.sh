#!/bin/bash
# Run tests in Docker container

set -e

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "Please install Docker:"
    echo "  sudo pacman -S docker"
    echo "  sudo systemctl start docker"
    echo "  sudo systemctl enable docker"
    echo ""
    echo "Or use an alternative method from TESTING.md"
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "❌ Docker daemon is not running."
    echo ""
    echo "Please start Docker:"
    echo "  sudo systemctl start docker"
    echo ""
    echo "Or add your user to the docker group:"
    echo "  sudo usermod -aG docker $USER"
    echo "  (then logout and login again)"
    exit 1
fi

echo "Building Docker test image..."
docker build -f Dockerfile.test -t synology-photo-sync-test .

echo ""
echo "Running tests in Docker container..."
docker run --rm -v "$(pwd):/workspace" synology-photo-sync-test

