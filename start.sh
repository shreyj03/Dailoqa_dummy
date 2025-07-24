#!/bin/bash

echo "🔑 Starting PostgreSQL..."
brew services start postgresql@14
sleep 3

echo "🚀 Starting FastAPI app on port 5051..."
uvicorn app.main:app --host 0.0.0.0 --port 5051 --reload &
FASTAPI_PID=$!

sleep 2

echo "🌐 Starting ngrok on port 5051..."
ngrok http 5051 &
NGROK_PID=$!

echo "✅ All services started."
echo "To stop: kill $FASTAPI_PID $NGROK_PID"
