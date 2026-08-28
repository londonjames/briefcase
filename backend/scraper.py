import re
import time

import requests
import cloudscraper
from curl_cffi import requests as curl_requests
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


class FetchError(Exception):
    """No fetcher could retrieve the page."""


def _fetch_requests(url):
    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    return resp.status_code, resp.text


def _fetch_impersonated(url):
    """Chrome's real TLS fingerprint — what Cloudflare checks before any header."""
    resp = curl_requests.get(url, impersonate="chrome", timeout=30)
    return resp.status_code, resp.text


def _fetch_cloudscraper(url):
    resp = cloudscraper.create_scraper().get(url, timeout=30)
    return resp.status_code, resp.text


def _fetch_via_claude(url):
    """Last resort: have Anthropic's servers fetch it.

    Bot-protection that blocks on IP reputation rejects any datacenter client,
    however good its TLS fingerprint. The server-side web_fetch tool comes from
    a different network entirely, and returns the page as markdown — which the
    extraction step reads just as happily as HTML.
    """
    with tracked("briefcase", "fetch-web") as _t:
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            tools=[{"type": "web_fetch_20250910", "name": "web_fetch", "max_uses": 1}],
            tool_choice={"type": "tool", "name": "web_fetch"},
            messages=[{"role": "user", "content": f"Fetch {url}"}],
        )
        _t.log(message)

    for block in message.content:
        if getattr(block, "type", None) != "web_fetch_tool_result":
            continue
        result = block.content
        source = getattr(getattr(result, "content", None), "source", None)
        if source and getattr(source, "data", None):
            return 200, source.data
        raise RuntimeError(getattr(result, "error_code", None) or "no document returned")

    raise RuntimeError("web_fetch was not called")


FETCHERS = [
    ("requests", _fetch_requests),
    ("impersonated", _fetch_impersonated),
    ("cloudscraper", _fetch_cloudscraper),
    ("claude", _fetch_via_claude),
]


def fetch_page(url, retries=2):
    """Fetch a web page and return its HTML.

    Plain requests handles most sites. Bot-protected ones reject it on the TLS
    handshake before a single header is read, so we escalate to a Chrome-
    impersonating client, then cloudscraper, and finally to a server-side fetch
    from Anthropic's network for sites that block our IP outright.
    """
    failures = []
    for name, fetch in FETCHERS:
        for attempt in range(retries + 1):
            try:
                status, text = fetch(url)
            except Exception as e:
                failures.append(f"{name}: {e}")
                break
            if status == 200:
                return text
            if status in (429, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            failures.append(f"{name}: HTTP {status}")
            break

    raise FetchError(f"Could not fetch {url} ({'; '.join(failures)})")


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
    """Structure one person's background.

    Prefers their own profile page. Where a team page carries the whole bio inline and
    links nowhere — common on leadership pages — that text is structured instead, because
    it is the only evidence the dossier will get about this person.
    """
    profile_url = member.get("profile_url")
    inline_bio = member.get("bio")

    if not profile_url and not inline_bio:
        return {**member, "bio": None, "education": [], "career": [], "personal": []}

    for attempt in range(3):
        try:
            return _extract_profile(member, profile_url, inline_bio)
        except Exception as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            # Returning an empty profile here would be indistinguishable from a
            # person whose page says nothing about them — which is how evidence
            # goes missing without anyone noticing. Say so instead.
            print(f"Profile extraction failed for {member['name']}: {e}", flush=True)
            return {
                **member,
                "bio": inline_bio,
                "education": [],
                "career": [],
                "personal": [],
                "extraction_failed": True,
            }


def _extract_profile(member, profile_url, inline_bio):
    if profile_url:
        html = fetch_page(profile_url)
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "iframe"]):
            tag.decompose()
        cleaned_html = str(soup)
    else:
        cleaned_html = inline_bio

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
                    "content": (
                        f"Profile page URL: {profile_url}\n\nHTML:\n\n{cleaned_html}"
                        if profile_url
                        else f"Biography text from {member['name']}'s team page:\n\n{cleaned_html}"
                    )
                    + f"\n\n{prompt}",
                }
            ],
        )
        _t.log(message)

    profile_data = parse_json(message)
    merged = {**member, **profile_data}
    if not merged.get("bio"):
        merged["bio"] = inline_bio
    return merged


def _person_key(name):
    """Match people across sections despite spacing and punctuation."""
    return re.sub(r"[^a-z]", "", (name or "").lower())


def _merge_person(first, second):
    """Fold a second appearance of the same person into the first.

    Leadership pages routinely list a founder-CEO under both the executive team
    and the board. Two cards for one person is wrong on the page and worse in
    the analysis, where it inflates every count they appear in.
    """
    titles = [t for t in (first.get("title"), second.get("title")) if t]
    merged = {**second, **first}
    merged["title"] = " · ".join(dict.fromkeys(titles)) or None

    # The two entries are usually different prose about the same career, so keep
    # both — the second often names the prior employers the first leaves out.
    bios = [b.strip() for b in (first.get("bio"), second.get("bio")) if b and b.strip()]
    merged["bio"] = "\n\n".join(dict.fromkeys(bios)) or None

    for field, key in (
        ("education", lambda e: (e.get("school"), e.get("degree"))),
        ("career", lambda c: (c.get("company"), c.get("role"))),
    ):
        seen, out = set(), []
        for item in (first.get(field) or []) + (second.get(field) or []):
            k = key(item)
            if k not in seen:
                seen.add(k)
                out.append(item)
        merged[field] = out

    merged["personal"] = list(
        dict.fromkeys((first.get("personal") or []) + (second.get("personal") or []))
    )
    return merged


def dedupe_across_groups(groups):
    """One card per person, keeping them in the group they first appear in.

    Returns the groups and the roles each duplicated person held, so the
    analysis can talk about someone sitting on both sides of the table instead
    of counting them twice.
    """
    canonical = {}
    order = []
    memberships = {}

    for group in groups:
        for member in group.get("members", []):
            key = _person_key(member.get("name"))
            memberships.setdefault(key, []).append(group["name"])
            if key in canonical:
                gname, existing = canonical[key]
                canonical[key] = (gname, _merge_person(existing, member))
            else:
                canonical[key] = (group["name"], member)
                order.append((group["name"], key))

    for key, (_, member) in canonical.items():
        groups_in = list(dict.fromkeys(memberships[key]))
        if len(groups_in) > 1:
            member["also_in"] = groups_in

    deduped = []
    for group in groups:
        members = [canonical[k][1] for gname, k in order if gname == group["name"]]
        deduped.append({"name": group["name"], "members": members})
    return [g for g in deduped if g["members"]]


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

    # Reconstruct groups with enriched data, then collapse anyone listed twice.
    result_groups = dedupe_across_groups([
        {"name": group["name"], "members": enriched_groups[group["name"]]}
        for group in groups
    ])
    for group in result_groups:
        group["count"] = len(group["members"])

    return {
        "company": company,
        "team_count": sum(g["count"] for g in result_groups),
        "groups": result_groups,
    }
