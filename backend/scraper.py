import requests
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import anthropic

from usage_logger import tracked
from prompts import TEAM_EXTRACTION_PROMPT, PROFILE_EXTRACTION_PROMPT
from structured import PROFILE_SCHEMA, TEAM_SCHEMA, json_format, parse_json

client = anthropic.Anthropic()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


def fetch_page(url, retries=2):
    """Fetch a web page and return its HTML content.
    Falls back to cloudscraper for Cloudflare-protected pages."""
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 403:
                # Cloudflare or similar — try cloudscraper
                scraper = cloudscraper.create_scraper()
                resp2 = scraper.get(url, timeout=30)
                resp2.raise_for_status()
                return resp2.text
            if attempt < retries and resp.status_code in (429, 503):
                import time
                time.sleep(2 * (attempt + 1))
                continue
            raise


def extract_team_structure(html, url):
    """Use Claude to parse team page HTML and extract team member data."""
    # Trim HTML to reduce token usage — remove scripts, styles, nav, footer
    soup = BeautifulSoup(html, "html.parser")

    # Extract background-image URLs from <style> tags before removing them
    # Sites like Apple use CSS background-image instead of <img> tags
    import re
    bg_class_to_url = {}
    for style_tag in soup.find_all("style"):
        style_text = style_tag.string or ""
        for match in re.finditer(
            r'\.([\w-]+)\s*\{[^}]*background-image:\s*url\(([^)]+)\)', style_text
        ):
            cls, img_url = match.group(1), match.group(2).strip("'\"")
            if not img_url.startswith("http"):
                img_url = urljoin(url, img_url)
            # Prefer 1x images (skip 2x retina duplicates)
            if cls not in bg_class_to_url:
                bg_class_to_url[cls] = img_url

    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
        tag.decompose()

    # Inject background-image URLs as <img> tags so Claude can see them
    for cls, img_url in bg_class_to_url.items():
        for el in soup.find_all(class_=cls):
            img_tag = soup.new_tag("img", src=img_url)
            el.insert(0, img_tag)

    # Convert lazy-loaded images to regular src for Claude to see
    for img in soup.find_all("img"):
        if not img.get("src") or img["src"].startswith("data:"):
            for attr in ("data-image-path", "data-src", "data-lazy-src"):
                if img.get(attr):
                    img["src"] = img[attr]
                    break
    for source in soup.find_all("source"):
        if source.get("data-srcset"):
            source["srcset"] = source["data-srcset"]

    cleaned_html = str(soup)
    # Truncate if extremely large (Claude context limit)
    if len(cleaned_html) > 300_000:
        cleaned_html = cleaned_html[:300_000]

    # A big team page is a lot of JSON — stream it so a long generation can't
    # hit the request timeout, and give it room so it isn't cut off mid-member.
    with tracked("briefcase", "team-extract") as _t, client.messages.stream(
        model="claude-sonnet-5",
        max_tokens=64000,
        output_config=json_format(TEAM_SCHEMA),
        messages=[
            {
                "role": "user",
                "content": f"The page URL is: {url}\n\nHTML content:\n\n{cleaned_html}\n\n{TEAM_EXTRACTION_PROMPT}",
            }
        ],
    ) as stream:
        message = stream.get_final_message()
        _t.log(message)

    team_data = parse_json(message)

    # Resolve relative URLs
    base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    for group in team_data.get("groups", []):
        for member in group.get("members", []):
            if member.get("photo_url") and not member["photo_url"].startswith("http"):
                member["photo_url"] = urljoin(url, member["photo_url"])
            if member.get("profile_url") and not member["profile_url"].startswith("http"):
                member["profile_url"] = urljoin(url, member["profile_url"])

    return team_data


def fetch_profile(member, progress_callback=None):
    """Fetch and parse an individual profile page."""
    profile_url = member.get("profile_url")
    if not profile_url:
        return {**member, "bio": None, "education": [], "career": [], "personal": []}

    try:
        html = fetch_page(profile_url)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
            tag.decompose()

        cleaned_html = str(soup)
        if len(cleaned_html) > 100_000:
            cleaned_html = cleaned_html[:100_000]

        prompt = PROFILE_EXTRACTION_PROMPT.format(
            name=member["name"], title=member.get("title", "Unknown")
        )

        with tracked("briefcase", "profile-extract") as _t:
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16000,
                output_config=json_format(PROFILE_SCHEMA),
                messages=[
                    {
                        "role": "user",
                        "content": f"Profile page URL: {profile_url}\n\nHTML:\n\n{cleaned_html}\n\n{prompt}",
                    }
                ],
            )
            _t.log(message)

        profile_data = parse_json(message)
        return {**member, **profile_data}

    except Exception as e:
        print(f"Error fetching profile for {member['name']}: {e}")
        return {**member, "bio": None, "education": [], "career": [], "personal": []}


def scrape_team(url, progress_callback=None):
    """Full scraping pipeline: fetch page → extract team → fetch profiles."""
    if progress_callback:
        progress_callback(5, "Fetching team page...")

    html = fetch_page(url)

    if progress_callback:
        progress_callback(10, "Analyzing page structure with AI...")

    team_data = extract_team_structure(html, url)
    company = team_data.get("company", "Unknown Company")
    groups = team_data.get("groups", [])

    # Count total members
    total_members = sum(len(g.get("members", [])) for g in groups)

    if progress_callback:
        progress_callback(20, f"Found {total_members} team members. Fetching individual profiles...")

    # Fetch all individual profiles in parallel (track index to preserve order)
    all_members = []
    for group in groups:
        for idx, m in enumerate(group.get("members", [])):
            all_members.append((group["name"], idx, m))

    completed = 0
    enriched_groups = {g["name"]: [] for g in groups}

    def fetch_and_track(group_name, idx, member):
        return group_name, idx, fetch_profile(member)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_and_track, gn, idx, m): (gn, idx, m)
            for gn, idx, m in all_members
        }
        for future in as_completed(futures):
            group_name, idx, enriched_member = future.result()
            enriched_groups[group_name].append((idx, enriched_member))
            completed += 1
            if progress_callback:
                pct = 20 + int((completed / total_members) * 50)
                progress_callback(pct, f"Fetching profiles ({completed}/{total_members})...")

    # Sort each group by original index to preserve page order
    for group_name in enriched_groups:
        enriched_groups[group_name].sort(key=lambda x: x[0])
        enriched_groups[group_name] = [m for _, m in enriched_groups[group_name]]

    # Reconstruct groups with enriched data
    result_groups = []
    for group in groups:
        result_groups.append({
            "name": group["name"],
            "count": len(enriched_groups[group["name"]]),
            "members": enriched_groups[group["name"]],
        })

    return {
        "company": company,
        "team_count": total_members,
        "groups": result_groups,
    }
