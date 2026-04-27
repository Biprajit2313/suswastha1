# SuSwastha

SuSwastha is a cloud-first AI healthcare screening platform with OTP-based authentication, disease risk prediction, OCR-assisted report extraction, and downloadable PDF reports uploaded to Cloudinary.

## Architecture

- `frontend/`: static HTML/CSS/JS app (GitHub Pages compatible)
- `backend/`: FastAPI app for auth, predictions, reports, OCR, PDF generation, and Cloudinary upload (Render-ready)
- `backend-node/`: optional Node.js microservice (not required for Render deployment)
- `models/`: versioned `.joblib` model artifacts used by FastAPI inference

## Features

- JWT + OTP authentication flow
- Multi-test prediction APIs (`/api/predict/*`) with model-backed risk scoring
- OCR extraction with graceful fallback when OCR engines are unavailable
- PDF report generation + Cloudinary storage
- User report history endpoints (`/api/user/reports`)
- Doctor booking API via Node service
- Environment-variable-only secret handling

## Tech Stack

- Frontend: HTML, CSS, vanilla JavaScript
- Backend API: FastAPI, SQLAlchemy, Pydantic
- ML: scikit-learn + joblib artifacts
- Storage: Cloudinary
- Auth: JWT + OTP email flow
- Secondary API: Node.js + Express

## Environment Variables

Copy `.env.example` values into your environment (Render “Environment” tab, or locally via PowerShell env vars):

- `SECRET_KEY`
- `FERNET_KEY`
- `DATABASE_URL`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`
- `SMTP_USER`
- `SMTP_PASS`

Optional:

- `ML_MODELS_DIR` (defaults to `models/`)
- `SMTP_FROM_EMAIL`
- `ENVIRONMENT` (`production` enables stricter validation)

Notes:

- `DATABASE_URL` must be your **Supabase PostgreSQL** connection string (starts with `postgresql://...`). SSL is enforced automatically.
- If SMTP variables are not set, emails are skipped (OTP/report emails won’t be sent).

## No-Docker Local Run

You can run locally without Docker.

### FastAPI

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
setx DATABASE_URL "postgresql://..."
setx SECRET_KEY "your-secret"
uvicorn app.main:app --host 0.0.0.0 --port 10000
```

### Frontend

Open `frontend/index.html` with a static server (VS Code Live Server or any local server) and set local API values in `frontend/config.js`:

- `fastapiBaseUrl`: `http://127.0.0.1:10000`
- `nodeBaseUrl`: leave empty unless you run the optional Node service

## Production Deployment

### Backend (Render - Python Web Service)

- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`

Set these Render environment variables (at minimum):

- `DATABASE_URL` (Supabase PostgreSQL)
- `SECRET_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Optional:

- `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM_EMAIL` (only if you want email sending enabled)
- `ENVIRONMENT=production`

### Database (Supabase PostgreSQL)

- Create a Supabase project and copy the PostgreSQL connection string into Render as `DATABASE_URL`.
- Ensure your database allows connections from Render (Supabase typically allows by password + SSL).

### Storage (Cloudinary)

- Create a Cloudinary account and set the Cloudinary env vars in Render.

### Frontend (GitHub Pages)

- Deploy the `frontend/` folder using GitHub Pages.
- Update `frontend/config.js`:
  - `fastapiBaseUrl` = your Render backend URL (example: `https://suswastha-api.onrender.com`)

## API Endpoints

### FastAPI Auth

- `POST /api/auth/signup/request-otp`
- `POST /api/auth/signup/verify`
- `POST /api/auth/login/request-otp`
- `POST /api/auth/login/verify`
- `GET /api/me`

### FastAPI Predictions & Reports

- `POST /api/predict/{test_type}`
- `GET /api/predict/{test_type}/metrics`
- `GET /api/predict/{test_type}/feature-importance`
- `GET /api/user/reports`
- `GET /api/reports/me`
- `POST /api/predict-from-image/{test_type}`

### Node API

- `POST /api/auth/send-otp`
- `POST /api/auth/verify-otp`
- `POST /api/bookings`
- `GET /api/bookings`

## Smoke Test Flow

1. Signup and request OTP.
2. Verify OTP and receive JWT.
3. Login with OTP verify endpoint.
4. Submit prediction payload to `/api/predict/{test_type}` with bearer token.
5. Confirm prediction persisted and report task started.
6. Confirm PDF upload URL is generated in Cloudinary.
7. Fetch reports via `/api/user/reports`.