# Inventory Management System with CI/CD Pipeline

A Flask + SQLite inventory app with a web dashboard, REST API, automated tests,
Docker packaging and a GitHub Actions CI/CD pipeline.

## Features
- Add, edit, delete and search products (SKU, name, category, quantity, price, reorder level)
- Stock in / stock out (+1 / −1) with protection against negative stock
- Dashboard: total products, units, stock value, low-stock count
- REST API + `/health` endpoint
- 12 automated tests, flake8 linting
- Dockerfile, docker-compose, GitHub Actions pipeline (test → build → publish → deploy)

## Project structure
```
inventory-management-system/
├── app/
│   ├── __init__.py          # app factory + SQLite setup
│   ├── routes.py            # REST API + page route
│   └── templates/index.html # web dashboard
├── tests/test_api.py        # automated tests
├── .github/workflows/ci-cd.yml  # CI/CD pipeline
├── Dockerfile
├── docker-compose.yml
├── requirements.txt / requirements-dev.txt
└── run.py                   # entry point
```

## Run locally
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
python run.py
```
Open http://localhost:5000

## Run tests and lint
```bash
pytest -v
flake8 .
```

## Run with Docker
```bash
docker compose up --build
```
Open http://localhost:5000 (data persists in a Docker volume).

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/products?q=term` | List / search |
| POST | `/api/products` | Create |
| GET | `/api/products/<id>` | Get one |
| PUT | `/api/products/<id>` | Update |
| DELETE | `/api/products/<id>` | Delete |
| POST | `/api/products/<id>/adjust` | Body `{"change": 5}` or `{"change": -2}` |
| GET | `/api/stats` | Dashboard numbers |
| GET | `/api/low-stock` | Items at/below reorder level |
| GET | `/health` | Health check |

Example:
```bash
curl -X POST localhost:5000/api/products -H "Content-Type: application/json" \
  -d '{"sku":"P-100","name":"USB Cable","quantity":25,"price":4.99}'
```

## CI/CD pipeline (GitHub Actions)
File: `.github/workflows/ci-cd.yml`

| Stage | Runs on | What it does |
|---|---|---|
| Lint & Test | every push and PR | flake8 + pytest on Python 3.11 and 3.12 |
| Build | after tests pass | builds Docker image and smoke-tests `/health` |
| Publish | push to `main` only | pushes image to GitHub Container Registry (`ghcr.io`) |
| Deploy | optional | SSHs into your server, pulls the new image, restarts container |

### Set it up
1. Create a GitHub repository and push this project to the `main` branch:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. Open the **Actions** tab. The pipeline starts automatically. No secrets are needed for test, build and publish.
3. **Optional deploy stage:** in *Settings → Secrets and variables → Actions*, add secrets
   `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, and a repository variable `ENABLE_DEPLOY` = `true`.
   The server needs Docker installed and must be able to pull from `ghcr.io`
   (make the package public, or run `docker login ghcr.io` on the server).
