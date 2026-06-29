# Terminal 1: FastAPI server
cd assetwatch-backend
source .venv/bin/activate
uvicorn app.app:app --reload

# Terminal 2: Monitoring Worker
cd assetwatch-backend
source .venv/bin/activate
python -m worker.main