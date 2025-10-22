# SIGNUM Provider & Reviews MVP (Flask + React)

## Prereqs
- Python 3.10+
- Node.js 18+

## 1) Backend
```bash
cd server
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate (use Git Bash/WSL)
pip install -r requirements.txt
cp .env.example .env        # put your YELP_API_KEY in .env
python app.py               # runs on http://localhost:5000

