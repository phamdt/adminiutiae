#!/bin/bash

# Code validation script to catch common GitHub Actions failures
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🔍 Validating code for GitHub Actions...${NC}"
echo "=============================================="

# Check Go code
echo -e "${BLUE}1. Validating Go code...${NC}"
cd go-service

# Check Go formatting
echo "   Checking Go formatting..."
UNFORMATTED=$(gofmt -l . | wc -l)
if [ "$UNFORMATTED" -gt 0 ]; then
    echo -e "${RED}❌ Go code is not formatted. Run: gofmt -w .${NC}"
    gofmt -l .
    exit 1
else
    echo -e "${GREEN}✅ Go code is properly formatted${NC}"
fi

# Check Go vet
echo "   Running go vet..."
if go vet ./...; then
    echo -e "${GREEN}✅ Go vet passed${NC}"
else
    echo -e "${RED}❌ Go vet failed${NC}"
    exit 1
fi

# Check Go build
echo "   Testing Go build..."
if go build ./...; then
    echo -e "${GREEN}✅ Go code builds successfully${NC}"
else
    echo -e "${RED}❌ Go build failed${NC}"
    exit 1
fi

# Check Go modules
echo "   Verifying Go modules..."
if go mod verify; then
    echo -e "${GREEN}✅ Go modules verified${NC}"
else
    echo -e "${RED}❌ Go module verification failed${NC}"
    exit 1
fi

cd ..

# Check Python code structure
echo -e "${BLUE}2. Validating Python code structure...${NC}"
cd python-service

# Check for __init__.py files
echo "   Checking for required __init__.py files..."
REQUIRED_INIT_FILES=(
    "app/__init__.py"
    "app/api/__init__.py"
    "app/core/__init__.py"
    "app/db/__init__.py"
    "app/models/__init__.py"
    "app/schemas/__init__.py"
    "app/services/__init__.py"
)

for init_file in "${REQUIRED_INIT_FILES[@]}"; do
    if [ ! -f "$init_file" ]; then
        echo -e "${RED}❌ Missing $init_file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required __init__.py files present${NC}"

# Check for required main files
echo "   Checking for required main files..."
REQUIRED_FILES=(
    "app/main.py"
    "app/core/config.py"
    "app/db/database.py"
    "app/models/user.py"
    "app/models/job.py"
    "app/api/endpoints.py"
    "requirements.txt"
    "alembic.ini"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}❌ Missing $file${NC}"
        exit 1
    fi
done
echo -e "${GREEN}✅ All required Python files present${NC}"

cd ..

# Check Docker configurations
echo -e "${BLUE}3. Validating Docker configurations...${NC}"

# Check Dockerfiles
echo "   Checking Dockerfiles..."
if [ ! -f "python-service/Dockerfile" ]; then
    echo -e "${RED}❌ Missing python-service/Dockerfile${NC}"
    exit 1
fi

if [ ! -f "go-service/Dockerfile" ]; then
    echo -e "${RED}❌ Missing go-service/Dockerfile${NC}"
    exit 1
fi

# Check .dockerignore files
if [ ! -f "python-service/.dockerignore" ]; then
    echo -e "${YELLOW}⚠️  Missing python-service/.dockerignore${NC}"
fi

if [ ! -f "go-service/.dockerignore" ]; then
    echo -e "${YELLOW}⚠️  Missing go-service/.dockerignore${NC}"
fi

echo -e "${GREEN}✅ Docker configurations present${NC}"

# Check Docker Compose
echo "   Validating Docker Compose..."
if [ -f "docker-compose/docker-compose.yml" ]; then
    # Check basic YAML syntax
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import yaml; yaml.safe_load(open('docker-compose/docker-compose.yml'))" 2>/dev/null; then
            echo -e "${GREEN}✅ Docker Compose YAML syntax is valid${NC}"
        else
            echo -e "${RED}❌ Docker Compose YAML syntax is invalid${NC}"
            exit 1
        fi
    else
        # Just check if file exists and has basic structure
        if grep -q "version:" docker-compose/docker-compose.yml && grep -q "services:" docker-compose/docker-compose.yml; then
            echo -e "${GREEN}✅ Docker Compose file structure looks valid${NC}"
        else
            echo -e "${RED}❌ Docker Compose file structure is invalid${NC}"
            exit 1
        fi
    fi
else
    echo -e "${RED}❌ Missing docker-compose.yml${NC}"
    exit 1
fi

# Check environment files
echo -e "${BLUE}4. Checking environment configuration...${NC}"
if [ ! -f ".env.example" ]; then
    echo -e "${YELLOW}⚠️  Missing .env.example${NC}"
else
    echo -e "${GREEN}✅ .env.example present${NC}"
fi

# Check for potential security issues
echo -e "${BLUE}5. Checking for security issues...${NC}"

# Check for hardcoded secrets
echo "   Checking for hardcoded secrets..."
if grep -r -i "password.*=.*['\"]" . --exclude-dir=.git --exclude="validate_code.sh" --exclude-dir=tests | grep -v "example\|test\|default"; then
    echo -e "${YELLOW}⚠️  Found potential hardcoded passwords${NC}"
else
    echo -e "${GREEN}✅ No hardcoded passwords found${NC}"
fi

# Check for TODO/FIXME comments
echo "   Checking for TODO/FIXME comments..."
TODO_COUNT=$(grep -r -i "TODO\|FIXME\|XXX\|HACK" . --exclude-dir=.git --exclude="validate_code.sh" | wc -l)
if [ "$TODO_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $TODO_COUNT TODO/FIXME comments${NC}"
else
    echo -e "${GREEN}✅ No TODO/FIXME comments${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}🎉 Code validation completed successfully!${NC}"
echo ""
echo "📋 Summary:"
echo "  ✅ Go code formatting and build"
echo "  ✅ Python code structure"
echo "  ✅ Docker configurations"
echo "  ✅ Environment setup"
echo "  ✅ Security checks"
echo ""
echo "🚀 Ready for GitHub Actions!"