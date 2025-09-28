#!/bin/bash

# Development startup script for hybrid Go/Python microservices
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Hybrid Go/Python Microservices (Development)${NC}"
echo "=================================================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found, copying from .env.example${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}🔍 Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo "❌ Docker not found. Please install Docker."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites found${NC}"

# Start services
echo -e "${BLUE}🐳 Starting services with Docker Compose...${NC}"
cd docker-compose
docker-compose up --build -d

# Wait for services to be ready
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check service health
echo -e "${BLUE}🏥 Checking service health...${NC}"

# Check Python API
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Python API is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Python API health check failed${NC}"
fi

# Check Go Worker
if curl -f -s http://localhost:8080/health > /dev/null; then
    echo -e "${GREEN}✅ Go Worker is healthy${NC}"
else
    echo -e "${YELLOW}⚠️  Go Worker health check failed${NC}"
fi

# Run database migrations
echo -e "${BLUE}📊 Running database migrations...${NC}"
cd ../python-service
if command_exists alembic; then
    alembic upgrade head
    echo -e "${GREEN}✅ Database migrations completed${NC}"
else
    echo -e "${YELLOW}⚠️  Alembic not found, skipping migrations${NC}"
    echo "Install with: pip install alembic"
fi

cd ..

echo -e "${GREEN}🎉 Services started successfully!${NC}"
echo ""
echo "📋 Service URLs:"
echo "  🐍 Python API:    http://localhost:8000"
echo "  📖 API Docs:      http://localhost:8000/docs"
echo "  🐹 Go Worker:     http://localhost:8080"
echo "  🏥 Health Checks: http://localhost:8000/health"
echo ""
echo "📊 Database & Cache:"
echo "  🐘 PostgreSQL:    localhost:5432"
echo "  📦 Redis:         localhost:6379"
echo ""
echo "🛠️  Development Commands:"
echo "  View logs:        docker-compose -f docker-compose/docker-compose.yml logs -f"
echo "  Stop services:    docker-compose -f docker-compose/docker-compose.yml down"
echo "  Rebuild:          docker-compose -f docker-compose/docker-compose.yml up --build"
echo ""
echo "🧪 Test the API:"
echo "  curl -X POST http://localhost:8000/api/v1/users/ \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"email\":\"test@example.com\",\"username\":\"testuser\",\"password\":\"password123\"}'"