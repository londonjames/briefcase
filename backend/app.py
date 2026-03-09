import os
import re
import json
import uuid
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import requests as http_requests

load_dotenv()

from scraper import scrape_team
from analyzer import generate_insights
from notion_builder import create_dossier_page

app = Flask(__name__)
CORS(app)

# In-memory job store
jobs = {}

# Upstash Redis REST client (reuses Profiler's instance with briefcase: prefix)
UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")


def redis_set(key, value):
    """Store a value in Upstash Redis via REST API."""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return False
    try:
        resp = http_requests.post(
            f"{UPSTASH_URL}/set/briefcase:{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            json=json.dumps(value),
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Redis SET error: {e}")
        return False


def redis_get(key):
    """Retrieve a value from Upstash Redis via REST API."""
    if not UPSTASH_URL or not UPSTASH_TOKEN:
        return None
    try:
        resp = http_requests.get(
            f"{UPSTASH_URL}/get/briefcase:{key}",
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result"):
                return json.loads(data["result"])
        return None
    except Exception as e:
        print(f"Redis GET error: {e}")
        return None


def run_pipeline(job_id, url):
    """Run the full scraping + analysis pipeline in a background thread."""
    job = jobs[job_id]

    def update_progress(pct, step):
        job["progress"] = pct
        job["step"] = step

    try:
        job["status"] = "in_progress"
        update_progress(5, "Starting...")

        # Step 1-4: Scrape team page and individual profiles
        team_data = scrape_team(url, progress_callback=update_progress)

        # Step 5: Generate insights
        insights = generate_insights(team_data, progress_callback=update_progress)

        # Assemble final result
        result = {
            "dossier_id": job_id,
            "company": team_data["company"],
            "team_count": team_data["team_count"],
            "groups": team_data["groups"],
            "insights": insights,
            "source_url": url,
        }

        # Generate slug: lowercase company name + date
        company_slug = re.sub(r'[^a-z0-9]+', '-', team_data["company"].lower()).strip('-')
        date_slug = datetime.now().strftime("%-d%B%Y")  # e.g. 9March2026
        slug = f"{company_slug}/{date_slug}"
        result["slug"] = slug
        # Persist to Redis (survives redeploys) and in-memory cache
        redis_set(slug, result)

        job["result"] = result
        job["status"] = "complete"
        job["progress"] = 100
        job["step"] = "Done"

    except Exception as e:
        job["status"] = "error"
        job["step"] = f"Error: {str(e)}"
        job["progress"] = 0
        print(f"Pipeline error for job {job_id}: {e}")
        import traceback
        traceback.print_exc()


@app.route("/api/dossier", methods=["POST"])
def create_dossier():
    """Start a new dossier generation job."""
    data = request.get_json()
    url = data.get("url")
    if not url:
        return jsonify({"error": "URL is required"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "step": "Queued",
        "result": None,
    }

    thread = threading.Thread(target=run_pipeline, args=(job_id, url))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/dossier/<job_id>", methods=["GET"])
def get_dossier(job_id):
    """Check status / get result of a dossier job."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({
        "status": job["status"],
        "progress": job["progress"],
        "step": job["step"],
        "result": job["result"],
    })


@app.route("/api/dossier/by-slug/<path:slug>", methods=["GET"])
def get_dossier_by_slug(slug):
    """Retrieve a completed dossier by its slug (company/date)."""
    result = redis_get(slug)
    if not result:
        return jsonify({"error": "Dossier not found"}), 404
    return jsonify({"result": result})


@app.route("/api/dossier/<job_id>/export-notion", methods=["POST"])
def export_to_notion(job_id):
    """Export a completed dossier to Notion."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if job["status"] != "complete":
        return jsonify({"error": "Dossier not yet complete"}), 400

    try:
        notion_url = create_dossier_page(job["result"])
        return jsonify({"notion_url": notion_url})
    except Exception as e:
        return jsonify({"error": f"Notion export failed: {str(e)}"}), 500


@app.route("/api/debug-fetch", methods=["POST"])
def debug_fetch():
    """Debug: fetch a URL and return info about what we get."""
    from scraper import fetch_page
    data = request.get_json()
    url = data.get("url", "")
    try:
        html = fetch_page(url)
        return jsonify({
            "length": len(html),
            "first_500": html[:500],
            "has_content": len(html) > 1000,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5002)
