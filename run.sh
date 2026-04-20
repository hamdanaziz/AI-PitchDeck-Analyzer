#!/bin/bash

# kill anything using port 8000 (backend)
lsof -ti :8000 | xargs kill -9 2>/dev/null

# start backend
(cd backend && uvicorn main:app --reload --port 8000) &

# start frontend
(cd frontend && npm run dev)