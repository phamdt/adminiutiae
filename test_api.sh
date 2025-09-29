#!/bin/bash

# Simple API test script
set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

BASE_URL="http://localhost:8000"

echo -e "${BLUE}🧪 Testing Hybrid Go/Python API${NC}"
echo "=================================="

# Test 1: Health check
echo -e "${BLUE}1. Testing health check...${NC}"
if curl -f -s "$BASE_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test 2: Create user
echo -e "${BLUE}2. Creating test user...${NC}"
USER_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "password": "password123"
  }')

if echo "$USER_RESPONSE" | grep -q "test@example.com"; then
    echo -e "${GREEN}✅ User created successfully${NC}"
    USER_ID=$(echo "$USER_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo "   User ID: $USER_ID"
else
    echo -e "${RED}❌ User creation failed${NC}"
    echo "$USER_RESPONSE"
    exit 1
fi

# Test 3: Login
echo -e "${BLUE}3. Testing login...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }')

if echo "$LOGIN_RESPONSE" | grep -q "access_token"; then
    echo -e "${GREEN}✅ Login successful${NC}"
    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo "   Token obtained: ${TOKEN:0:20}..."
else
    echo -e "${RED}❌ Login failed${NC}"
    echo "$LOGIN_RESPONSE"
    exit 1
fi

# Test 4: Create external data job
echo -e "${BLUE}4. Creating external data job...${NC}"
JOB_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/users/$USER_ID/external-data" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "data_sources": [
      "https://jsonplaceholder.typicode.com/posts/1",
      "https://jsonplaceholder.typicode.com/users/1"
    ],
    "filters": {
      "category": "test"
    }
  }')

if echo "$JOB_RESPONSE" | grep -q "job_id"; then
    echo -e "${GREEN}✅ Job created successfully${NC}"
    JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"job_id":[0-9]*' | cut -d':' -f2)
    echo "   Job ID: $JOB_ID"
else
    echo -e "${RED}❌ Job creation failed${NC}"
    echo "$JOB_RESPONSE"
    exit 1
fi

# Test 5: Check job status (with retry)
echo -e "${BLUE}5. Checking job status...${NC}"
MAX_ATTEMPTS=10
ATTEMPT=1

while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    STATUS_RESPONSE=$(curl -s "$BASE_URL/api/v1/jobs/$JOB_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
    echo "   Attempt $ATTEMPT: Status = $STATUS"
    
    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}✅ Job completed successfully${NC}"
        echo "   Results available"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo -e "${RED}❌ Job failed${NC}"
        echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}❌ Job did not complete within expected time${NC}"
        echo "$STATUS_RESPONSE"
        exit 1
    fi
    
    sleep 2
    ATTEMPT=$((ATTEMPT + 1))
done

# Test 6: Get job results
echo -e "${BLUE}6. Getting job results...${NC}"
RESULTS_RESPONSE=$(curl -s "$BASE_URL/api/v1/jobs/$JOB_ID/results" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESULTS_RESPONSE" | grep -q "results"; then
    echo -e "${GREEN}✅ Job results retrieved successfully${NC}"
    echo "   Results contain external API data"
else
    echo -e "${RED}❌ Failed to get job results${NC}"
    echo "$RESULTS_RESPONSE"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 All tests passed! The hybrid Go/Python API is working correctly.${NC}"
echo ""
echo "📋 Test Summary:"
echo "  ✅ Health check"
echo "  ✅ User creation"
echo "  ✅ Authentication"
echo "  ✅ Job creation (Python → Go)"
echo "  ✅ Job processing (Go external APIs)"
echo "  ✅ Result retrieval"
echo ""
echo "🔗 Try the interactive API docs: $BASE_URL/docs"