#!/bin/bash
pip install -r requirements.txt
npm install
npm run build -w report
npm run build -w frontend
pkill -f "node report/ssr-dist/server.js"
node report/ssr-dist/server.js & uvicorn main:app --reload
