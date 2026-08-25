# Briefcase — Team Dossier Generator

Frontend: React 19 + Vite 7 (JavaScript) on Vercel. Backend: Python Flask on Railway.
Repo: `londonjames/briefcase` (auto-deploys on push to main).

## Critical Rules
- Split deployment: frontend on Vercel (`frontend/`), backend on Railway (`backend/`).
- Backend URL: `https://briefcase-production-9752.up.railway.app/api`
- Railway timeout: 300s — very large teams can still time out.
- In-memory job store — jobs are lost on Railway redeploy.
- Notion API limits 100 blocks per request — code batches automatically.
- Some team pages are Cloudflare-protected — falls back to cloudscraper.

## Commands
- Frontend build: `cd frontend && npm run build`
- Backend: `cd backend && gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300`

## Environment Variables
Backend: `ANTHROPIC_API_KEY`, `NOTION_TOKEN`, `NOTION_DATABASE_ID`
Frontend: `VITE_API_URL` (points to Railway backend)
