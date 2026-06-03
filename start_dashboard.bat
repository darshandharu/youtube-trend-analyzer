@echo off
echo Starting YouTube Trend Analyzer Dashboard...
echo Opening http://localhost:8502
start http://localhost:8502
streamlit run scripts/dashboard.py --server.port 8502
