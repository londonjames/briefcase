# Briefcase Architecture Reference

## Key Files
| File | Purpose |
|------|---------|
| `backend/app.py` | Flask API routes + async job runner (threading) |
| `backend/scraper.py` | HTML fetch + Claude team extraction + parallel profile fetching |
| `backend/analyzer.py` | Claude Opus team insights generation (6 sections) |
| `backend/prompts.py` | System prompts for extraction + analysis |
| `backend/notion_builder.py` | Notion page creation with batched blocks |
| `frontend/src/App.jsx` | Main app (form → progress → dossier state machine) |
| `frontend/src/components/Progress.jsx` | Two-phase progress indicator |
| `frontend/src/components/Dossier.jsx` | Tab interface (Team + Insights) |
| `frontend/src/components/ProfileCard.jsx` | Individual profile card |

## API Routes (Backend)
- `POST /api/dossier` — Start async scraping job, returns job_id
- `GET /api/dossier/<job_id>` — Poll job status/progress (every 2s from frontend)
- `POST /api/dossier/<job_id>/export-notion` — Export to Notion database
- `GET /api/health` — Health check

## Data Pipeline
1. Fetch team page HTML (cloudscraper fallback for Cloudflare)
2. Claude Sonnet extracts team structure (names, titles, URLs)
3. ThreadPoolExecutor (10 workers) fetches individual profiles in parallel
4. Claude Haiku extracts bio/education/career from each profile
5. Claude Opus generates 6-section team analysis (max 16k tokens)
6. Optional: export to Notion

## Progress Phases
- Phase 1 (0-70%): "X/Y profiles pulled" — individual profile fetching
- Phase 2 (75-95%): Elapsed timer — insight generation ("usually 60-90 seconds")
