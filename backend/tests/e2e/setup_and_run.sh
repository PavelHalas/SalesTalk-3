#!/bin/bash
#
# Quick Setup Script for E2E Tests with LocalStack
#
# This script helps you quickly set up and run E2E tests locally.
# It checks for dependencies, starts LocalStack, seeds data, and runs tests.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
LOCALSTACK_ENDPOINT="http://localhost:4566"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="${SCRIPT_DIR}/.."

echo "================================================="
echo "  SalesTalk E2E Test Setup with LocalStack"
echo "================================================="
echo ""

# Check if Docker is installed
echo -n "Checking for Docker... "
if ! command -v docker &> /dev/null; then
    echo -e "${RED}NOT FOUND${NC}"
    echo "Docker is required but not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# Check if Python is installed
echo -n "Checking for Python... "
if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
    echo -e "${RED}NOT FOUND${NC}"
    echo "Python 3.11+ is required but not installed."
    exit 1
fi
PYTHON_CMD=$(command -v python3 || command -v python)
echo -e "${GREEN}OK${NC} ($(${PYTHON_CMD} --version))"

# Check if pip is installed
echo -n "Checking for pip... "
if ! ${PYTHON_CMD} -m pip --version &> /dev/null; then
    echo -e "${RED}NOT FOUND${NC}"
    echo "pip is required but not installed."
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
cd "${BACKEND_DIR}"
${PYTHON_CMD} -m pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check if LocalStack is running
echo ""
echo -n "Checking if LocalStack is running... "
if curl -s "${LOCALSTACK_ENDPOINT}/_localstack/health" > /dev/null 2>&1; then
    echo -e "${GREEN}YES${NC}"
    LOCALSTACK_RUNNING=true
else
    echo -e "${YELLOW}NO${NC}"
    LOCALSTACK_RUNNING=false
fi

# Start LocalStack if not running
if [ "$LOCALSTACK_RUNNING" = false ]; then
    echo ""
    echo "Starting LocalStack..."
    
    # Check if container already exists but is stopped
    if docker ps -a --format '{{.Names}}' | grep -q '^salestalk-localstack$'; then
        echo "Removing existing stopped container..."
        docker rm -f salestalk-localstack > /dev/null 2>&1 || true
    fi
    
    # Start LocalStack
    docker run -d \
        --name salestalk-localstack \
        -p 4566:4566 \
        -e SERVICES=dynamodb \
        localstack/localstack:latest > /dev/null
    
    echo -n "Waiting for LocalStack to be ready"
    for i in {1..30}; do
        if curl -s "${LOCALSTACK_ENDPOINT}/_localstack/health" > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}✓ LocalStack is ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    # Final check
    if ! curl -s "${LOCALSTACK_ENDPOINT}/_localstack/health" > /dev/null 2>&1; then
        echo ""
        echo -e "${RED}✗ LocalStack failed to start${NC}"
        echo "Check logs with: docker logs salestalk-localstack"
        exit 1
    fi
fi

# Seed LocalStack DynamoDB
echo ""
echo "Seeding LocalStack DynamoDB with test data..."
cd "${BACKEND_DIR}"
${PYTHON_CMD} scripts/seed_localstack.py
echo -e "${GREEN}✓ Data seeded successfully${NC}"

# Run E2E tests
echo ""
echo "Running E2E tests..."
echo "================================================="
${PYTHON_CMD} -m pytest tests/e2e/ -v --tb=short

# Check test result
TEST_RESULT=$?

echo ""
echo "================================================="
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All E2E tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo "Run tests with more verbose output:"
    echo "  cd backend && pytest tests/e2e/ -vvs"
fi

echo ""
echo "LocalStack Resources:"
echo "  - Endpoint: ${LOCALSTACK_ENDPOINT}"
echo "  - Health: ${LOCALSTACK_ENDPOINT}/_localstack/health"
echo "  - Container: salestalk-localstack"
echo ""
echo "To stop LocalStack:"
echo "  docker stop salestalk-localstack"
echo ""
echo "To view LocalStack logs:"
echo "  docker logs salestalk-localstack"
echo ""
echo "To run tests manually:"
echo "  cd backend && pytest tests/e2e/ -v"
echo "================================================="

exit $TEST_RESULT
