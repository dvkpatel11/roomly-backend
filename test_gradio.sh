#!/bin/bash

echo "🎨 STARTING GRADIO FRONTEND FOR TESTING"
echo "======================================="

# Check if backend is running
echo "🔍 Checking if backend is running..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend is running on http://localhost:8000"
else
    echo "❌ Backend not running! Please start it first:"
    echo "   Terminal 1: uvicorn app.main:app --reload"
    echo ""
    exit 1
fi

echo ""
echo "🚀 Starting Gradio frontend..."
echo "📍 Frontend will be available at: http://localhost:7860"
echo ""

cd ../roomly-frontend
python app.py
