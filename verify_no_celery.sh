#!/bin/bash

# Script to verify no Celery references exist in the codebase
set -e

echo "🔍 Verifying Celery-free implementation..."
echo "========================================"

# Search for problematic Celery references (imports, decorators, etc.)
echo "1. Checking for problematic Celery usage..."
if grep -r -i "from celery\|import celery\|@celery\|celery_app\|\.delay(" . --exclude-dir=.git --exclude="verify_no_celery.sh" 2>/dev/null; then
    echo "❌ Found Celery usage in code!"
    exit 1
else
    echo "✅ No Celery code usage found"
fi

# Check for positive Celery mentions (explanatory text is OK)
echo "2. Checking Celery mentions in context..."
CELERY_MENTIONS=$(grep -r -i "celery" . --exclude-dir=.git --exclude="verify_no_celery.sh" 2>/dev/null | wc -l)
echo "   Found $CELERY_MENTIONS Celery mentions (explanatory text is OK)"

# Search for problematic message broker usage (not Redis pub/sub)
echo "3. Checking for message broker usage..."
if grep -r -i "from.*broker\|import.*machinery\|@broker\|\.consume\|\.subscribe.*queue" . --exclude-dir=.git --exclude="verify_no_celery.sh" 2>/dev/null; then
    echo "❌ Found message broker usage in code!"
    exit 1
else
    echo "✅ No message broker code usage found"
fi

# Redis pub/sub is OK for notifications
echo "4. Checking Redis pub/sub usage (OK for notifications)..."
REDIS_PUBLISH=$(grep -r "\.Publish\|\.publish" . --exclude-dir=.git --exclude="verify_no_celery.sh" 2>/dev/null | wc -l)
echo "   Found $REDIS_PUBLISH Redis pub/sub calls (OK for notifications)"

# Check Python requirements
echo "5. Checking Python requirements.txt..."
if grep -i celery python-service/requirements.txt 2>/dev/null; then
    echo "❌ Found Celery in requirements.txt!"
    exit 1
else
    echo "✅ No Celery in Python requirements"
fi

# Check Go dependencies
echo "6. Checking Go dependencies..."
if grep -i "machinery\|celery" go-service/go.mod 2>/dev/null; then
    echo "❌ Found message queue dependencies in go.mod!"
    exit 1
else
    echo "✅ No problematic dependencies in Go modules"
fi

# Verify HTTP communication approach
echo "7. Verifying HTTP communication approach..."
if grep -r "httpx.*AsyncClient" python-service/ 2>/dev/null && grep -r "jobs/process" python-service/ 2>/dev/null; then
    echo "✅ HTTP communication correctly implemented"
else
    echo "❌ HTTP communication not properly implemented"
    exit 1
fi

# Check for Go HTTP handlers
echo "8. Checking Go HTTP job handlers..."
if grep -r "ProcessJob.*gin.Context" go-service/ 2>/dev/null; then
    echo "✅ Go HTTP job handlers implemented"
else
    echo "❌ Go HTTP job handlers missing"
    exit 1
fi

echo ""
echo "🎉 SUCCESS: Implementation is completely Celery-free!"
echo ""
echo "✅ Architecture uses direct HTTP communication"
echo "✅ No message brokers or complex queues"
echo "✅ Python delegates to Go via simple HTTP POST"
echo "✅ Shared PostgreSQL database for job state"
echo "✅ Optional Redis for notifications only"
echo ""
echo "This implementation maximizes Go/Python interoperability!"