# VEYRA

### Every link. One intelligence layer.

VEYRA is a modern URL shortener and link intelligence platform built with FastAPI, SQLite, and Python. It enables users to create short links, manage destinations, generate QR codes, and monitor engagement through an analytics dashboard.

<p align="center">
  <strong>Live Application:</strong>
  <a href="https://veyra-app.azurewebsites.net">veyra-app.azurewebsites.net</a>
</p>

---

## Overview

VEYRA transforms ordinary URLs into manageable, trackable short links.

Designed with a minimal interface and an analytics-oriented architecture, VEYRA brings link management and engagement insights together in one workspace.

## Features

### Link Management
- Create short URLs from long destination URLs.
- Create custom aliases.
- Manage personal links.
- Redirect visitors to original destinations.

### QR Code Generation
- Generate QR codes for short links.
- Download QR codes in SVG format.
- Share links through scannable QR codes.

### Link Intelligence
- Track total clicks.
- Monitor click activity over time.
- Analyze referrers.
- View device and browser information.
- Explore available geographic analytics.

### User Authentication
- User registration and login.
- Secure password hashing.
- Session-based authentication.
- User-specific link management.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| Authentication | Session cookies |
| QR Generation | Python qrcode |
| Web Server | Uvicorn |
| Containerization | Docker |
| Cloud Hosting | Microsoft Azure App Service |
| Version Control | Git and GitHub |

## Architecture

```text
                 USER
                  |
                  v
          VEYRA WEB INTERFACE
                  |
                  v
             FASTAPI
                  |
        +---------+---------+
        |         |         |
        v         v         v
     LINKS      QR CODE   ANALYTICS
        |         |         |
        +---------+---------+
                  |
                  v
              SQLITE DB
                  |
                  v
          AZURE APP SERVICE
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/suresh-vlsi/VEYRA.git
cd VEYRA
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file using `.env.example` as a reference.

Configure the following variables:

```env
DB_PATH=links.db
BASE_URL=http://localhost:8000
SESSION_SECRET=replace-with-a-secure-random-secret
COOKIE_SECURE=false
```

Use a unique, securely generated session secret in production.

### 5. Start the application

```bash
uvicorn main:app --reload
```

Open:

```text
http://localhost:8000
```

## Docker Deployment

Build and start the application:

```bash
docker compose up --build -d
```

View application logs:

```bash
docker compose logs -f
```

Stop the application:

```bash
docker compose down
```

## Production Deployment

VEYRA is hosted using Microsoft Azure App Service.

**Production URL:** https://veyra-app.azurewebsites.net

The production application uses persistent storage for its SQLite database.

## Project Structure

```text
VEYRA/
│
├── main.py
├── requirements.txt
├── README.md
├── Dockerfile
├── compose.yaml
├── .dockerignore
├── .gitignore
├── .env.example
│
└── static/
    └── index.html
```

## Roadmap

- [x] URL shortening
- [x] Custom aliases
- [x] User authentication
- [x] QR code generation
- [x] Link analytics dashboard
- [x] Azure production deployment
- [x] GitHub source control
- [ ] Custom domain integration
- [ ] Advanced analytics and reporting
- [ ] Developer API and API keys
- [ ] Team workspaces
- [ ] AI-powered link intelligence

## Version

**VEYRA v1.0.0**

Initial production release.

## Author

**Kusumuru Suresh Kumar**

GitHub: https://github.com/suresh-vlsi

Project: https://github.com/suresh-vlsi/VEYRA

---

<p align="center">
  <strong>VEYRA</strong><br>
  Every link. One intelligence layer.
</p>
