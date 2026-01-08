#!/bin/bash

# 1. Upload a file first
# UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:5000/api/upload \
#   -F "file=@anothertest.csv" \
#   -F "uploaded_by=user123")

# echo "Upload Response:"
# echo $UPLOAD_RESPONSE

# Extract document_id (using jq if installed, or manually copy)
 DOCUMENT_ID=  '067c7911-b2d7-48ff-b4c3-8b28d77a08b6' #$(echo $UPLOAD_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

echo "\nDocument ID: 067c7911-b2d7-48ff-b4c3-8b28d77a08b6"

# 2. Create a job
echo "\n\nCreating job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d "{
    \"document_id\": \"067c7911-b2d7-48ff-b4c3-8b28d77a08b6\",
    \"job_type\": \"extract_data\"
  }")

echo $JOB_RESPONSE

# Extract job_id
JOB_ID=$(echo $JOB_RESPONSE | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

echo "\nJob ID: $JOB_ID"

# 3. Get job status
echo "\n\nGetting job status..."
curl -s http://localhost:5000/api/jobs/$JOB_ID | json_pp