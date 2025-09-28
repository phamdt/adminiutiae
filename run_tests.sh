#!/bin/bash

# Test Runner Script for Hybrid Go/Python Microservices
# This script sets up test environment and runs tests in TDD order

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
TEST_DB_NAME="testdb"
TEST_DB_USER="testuser"
TEST_DB_PASS="testpass"
TEST_DB_PORT="5433"
TEST_REDIS_PORT="6380"
GO_SERVICE_PORT="8080"

echo -e "${BLUE}🚀 Hybrid Go/Python Microservices Test Runner${NC}"
echo "=================================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    echo -e "${YELLOW}⏳ Waiting for $service_name to be ready...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port 2>/dev/null; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: $service_name not ready yet..."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo -e "${RED}❌ $service_name failed to start within $max_attempts seconds${NC}"
    return 1
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

MISSING_DEPS=()

if ! command_exists docker; then
    MISSING_DEPS+=("docker")
fi

if ! command_exists python3; then
    MISSING_DEPS+=("python3")
fi

if ! command_exists go; then
    MISSING_DEPS+=("go")
fi

if ! command_exists psql; then
    MISSING_DEPS+=("postgresql-client")
fi

if ! command_exists redis-cli; then
    MISSING_DEPS+=("redis-tools")
fi

if [ ${#MISSING_DEPS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing dependencies: ${MISSING_DEPS[*]}${NC}"
    echo "Please install missing dependencies and try again."
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites found${NC}"

# Setup test environment
setup_test_env() {
    echo -e "${BLUE}🏗️  Setting up test environment...${NC}"
    
    # Set environment variables
    export TEST_DATABASE_URL="postgresql+asyncpg://$TEST_DB_USER:$TEST_DB_PASS@localhost:$TEST_DB_PORT/$TEST_DB_NAME"
    export TEST_REDIS_URL="redis://localhost:$TEST_REDIS_PORT/0"
    export GO_SERVICE_URL="http://localhost:$GO_SERVICE_PORT"
    export TESTING="true"
    
    echo "Environment variables set:"
    echo "  TEST_DATABASE_URL=$TEST_DATABASE_URL"
    echo "  TEST_REDIS_URL=$TEST_REDIS_URL"
    echo "  GO_SERVICE_URL=$GO_SERVICE_URL"
}

# Start test database
start_test_database() {
    echo -e "${BLUE}🐘 Starting test PostgreSQL database...${NC}"
    
    # Stop existing container if running
    if docker ps -q -f name=test-postgres | grep -q .; then
        echo "Stopping existing test database..."
        docker stop test-postgres >/dev/null 2>&1 || true
        docker rm test-postgres >/dev/null 2>&1 || true
    fi
    
    # Start new container
    docker run -d --name test-postgres \
        -e POSTGRES_DB=$TEST_DB_NAME \
        -e POSTGRES_USER=$TEST_DB_USER \
        -e POSTGRES_PASSWORD=$TEST_DB_PASS \
        -p $TEST_DB_PORT:5432 \
        postgres:16-alpine >/dev/null
    
    # Wait for database to be ready
    wait_for_service localhost $TEST_DB_PORT "PostgreSQL"
    
    # Test connection
    if PGPASSWORD=$TEST_DB_PASS psql -h localhost -p $TEST_DB_PORT -U $TEST_DB_USER -d $TEST_DB_NAME -c "SELECT 1;" >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Test database is ready${NC}"
    else
        echo -e "${RED}❌ Failed to connect to test database${NC}"
        return 1
    fi
}

# Start test Redis
start_test_redis() {
    echo -e "${BLUE}📦 Starting test Redis...${NC}"
    
    # Stop existing container if running
    if docker ps -q -f name=test-redis | grep -q .; then
        echo "Stopping existing test Redis..."
        docker stop test-redis >/dev/null 2>&1 || true
        docker rm test-redis >/dev/null 2>&1 || true
    fi
    
    # Start new container
    docker run -d --name test-redis \
        -p $TEST_REDIS_PORT:6379 \
        redis:8.2-alpine >/dev/null
    
    # Wait for Redis to be ready
    wait_for_service localhost $TEST_REDIS_PORT "Redis"
    
    # Test connection
    if redis-cli -p $TEST_REDIS_PORT ping >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Test Redis is ready${NC}"
    else
        echo -e "${RED}❌ Failed to connect to test Redis${NC}"
        return 1
    fi
}

# Install Python dependencies
install_python_deps() {
    echo -e "${BLUE}🐍 Installing Python dependencies...${NC}"
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt >/dev/null 2>&1
        echo -e "${GREEN}✅ Python dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  No requirements.txt found, skipping Python deps${NC}"
    fi
    
    # Install test dependencies
    pip install pytest pytest-asyncio httpx pytest-mock pytest-cov >/dev/null 2>&1
    echo -e "${GREEN}✅ Test dependencies installed${NC}"
}

# Install Go dependencies
install_go_deps() {
    echo -e "${BLUE}🐹 Installing Go dependencies...${NC}"
    
    if [ -f "go-service/go.mod" ]; then
        cd go-service
        go mod download >/dev/null 2>&1
        go get github.com/stretchr/testify/assert >/dev/null 2>&1
        go get github.com/stretchr/testify/mock >/dev/null 2>&1
        go get github.com/stretchr/testify/suite >/dev/null 2>&1
        cd ..
        echo -e "${GREEN}✅ Go dependencies installed${NC}"
    else
        echo -e "${YELLOW}⚠️  No go.mod found, skipping Go deps${NC}"
    fi
}

# Run Python tests
run_python_tests() {
    echo -e "${BLUE}🐍 Running Python tests...${NC}"
    
    if [ "$1" = "unit" ]; then
        echo "Running unit tests only..."
        pytest tests/python/ -m unit -v
    elif [ "$1" = "integration" ]; then
        echo "Running integration tests only..."
        pytest tests/integration/ -m integration -v
    else
        echo "Running all Python tests..."
        pytest tests/python/ tests/integration/ -v
    fi
}

# Run Go tests
run_go_tests() {
    echo -e "${BLUE}🐹 Running Go tests...${NC}"
    
    if [ -d "go-service" ]; then
        cd go-service
        go test ./tests/... -v
        cd ..
    else
        echo -e "${YELLOW}⚠️  No go-service directory found, skipping Go tests${NC}"
    fi
}

# Start Go service for integration tests
start_go_service() {
    echo -e "${BLUE}🚀 Starting Go service for integration tests...${NC}"
    
    if [ -f "go-service/cmd/worker/main.go" ]; then
        cd go-service
        
        # Set environment variables for Go service
        export DATABASE_URL="postgresql://$TEST_DB_USER:$TEST_DB_PASS@localhost:$TEST_DB_PORT/$TEST_DB_NAME"
        export REDIS_URL="redis://localhost:$TEST_REDIS_PORT/0"
        export PORT=$GO_SERVICE_PORT
        
        # Start Go service in background
        go run cmd/worker/main.go &
        GO_SERVICE_PID=$!
        cd ..
        
        # Wait for Go service to be ready
        wait_for_service localhost $GO_SERVICE_PORT "Go service"
        
        echo "Go service started with PID: $GO_SERVICE_PID"
        return 0
    else
        echo -e "${YELLOW}⚠️  Go service main.go not found, skipping service startup${NC}"
        return 1
    fi
}

# Stop Go service
stop_go_service() {
    if [ ! -z "$GO_SERVICE_PID" ]; then
        echo -e "${BLUE}🛑 Stopping Go service...${NC}"
        kill $GO_SERVICE_PID 2>/dev/null || true
        wait $GO_SERVICE_PID 2>/dev/null || true
        echo -e "${GREEN}✅ Go service stopped${NC}"
    fi
}

# Cleanup test environment
cleanup() {
    echo -e "${BLUE}🧹 Cleaning up test environment...${NC}"
    
    # Stop Go service
    stop_go_service
    
    # Stop Docker containers
    docker stop test-postgres test-redis >/dev/null 2>&1 || true
    docker rm test-postgres test-redis >/dev/null 2>&1 || true
    
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    local test_type=${1:-"all"}
    
    case $test_type in
        "unit")
            echo -e "${BLUE}🔴 Running UNIT tests only (TDD Red Phase)${NC}"
            setup_test_env
            start_test_database
            start_test_redis
            install_python_deps
            install_go_deps
            run_python_tests unit
            run_go_tests
            ;;
        "integration")
            echo -e "${BLUE}🟡 Running INTEGRATION tests (TDD Green Phase)${NC}"
            setup_test_env
            start_test_database
            start_test_redis
            install_python_deps
            install_go_deps
            if start_go_service; then
                run_python_tests integration
            else
                echo -e "${YELLOW}⚠️  Skipping integration tests - Go service not available${NC}"
            fi
            ;;
        "e2e"|"end-to-end")
            echo -e "${BLUE}🟢 Running END-TO-END tests (TDD Refactor Phase)${NC}"
            setup_test_env
            start_test_database
            start_test_redis
            install_python_deps
            install_go_deps
            if start_go_service; then
                run_python_tests
                run_go_tests
            else
                echo -e "${RED}❌ Cannot run E2E tests without Go service${NC}"
                exit 1
            fi
            ;;
        "all"|"")
            echo -e "${BLUE}🎯 Running ALL tests${NC}"
            setup_test_env
            start_test_database
            start_test_redis
            install_python_deps
            install_go_deps
            
            echo -e "${BLUE}Phase 1: Unit Tests${NC}"
            run_python_tests unit
            run_go_tests
            
            echo -e "${BLUE}Phase 2: Integration Tests${NC}"
            if start_go_service; then
                run_python_tests integration
            fi
            ;;
        "setup")
            echo -e "${BLUE}🔧 Setting up test environment only${NC}"
            setup_test_env
            start_test_database
            start_test_redis
            install_python_deps
            install_go_deps
            echo -e "${GREEN}✅ Test environment ready!${NC}"
            echo "You can now run tests manually:"
            echo "  pytest tests/python/ -v"
            echo "  cd go-service && go test ./tests/... -v"
            ;;
        "cleanup")
            echo -e "${BLUE}🧹 Cleaning up only${NC}"
            cleanup
            ;;
        *)
            echo "Usage: $0 [unit|integration|e2e|all|setup|cleanup]"
            echo ""
            echo "Test types:"
            echo "  unit        - Run unit tests only (fast)"
            echo "  integration - Run integration tests (medium)"
            echo "  e2e         - Run end-to-end tests (slow)"
            echo "  all         - Run all tests (default)"
            echo "  setup       - Setup test environment only"
            echo "  cleanup     - Cleanup test environment only"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}🎉 Test execution completed!${NC}"
}

# Run main function with all arguments
main "$@"