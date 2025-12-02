#!/bin/bash
# Скрипт запуска приложения
cd "$(dirname "$0")/backend"
source ../venv/bin/activate
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

