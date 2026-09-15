python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r SetUp/requirements.txt
$env:PYTHONPATH=".\src"
uvicorn src.api.main:app --reload