import os
import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
NOTION_API = "https://api.notion.com/v1"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def create_dossier_page(dossier):
    """Create a Notion page with the full dossier content using toggle H1 pattern."""
    company = dossier["company"]
    team_count = dossier["team_count"]

    children = []

    # Header
    children.append(_heading(1, f"{company} — Team Dossier ({team_count} members)"))
    children.append(_divider())

    # Team sections
    for group in dossier.get("groups", []):
        # Toggle heading for each group
        group_children = []
        for member in group.get("members", []):
            # Build member content blocks
            member_blocks = _build_member_blocks(member)
            group_children.extend(member_blocks)
            group_children.append(_divider())

        children.append(
            _toggle_heading(2, f"{group['name']} ({group['count']})", group_children)
        )

    children.append(_divider())

    # Insight sections
    for insight in dossier.get("insights", []):
        insight_blocks = _markdown_to_blocks(insight["content"])
        children.append(_toggle_heading(2, insight["title"], insight_blocks))

    # Create the page (Notion API limits children to 100 per request)
    page_data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": {
                "title": [{"text": {"content": f"{company} — Team Dossier"}}]
            }
        },
        "children": children[:100],
    }

    resp = requests.post(
        f"{NOTION_API}/pages",
        headers=NOTION_HEADERS,
        json=page_data,
    )
    resp.raise_for_status()
    page = resp.json()
    page_id = page["id"]

    # Append remaining children in batches of 100
    remaining = children[100:]
    while remaining:
        batch = remaining[:100]
        remaining = remaining[100:]
        requests.patch(
            f"{NOTION_API}/blocks/{page_id}/children",
            headers=NOTION_HEADERS,
            json={"children": batch},
        )

    return page["url"]


def _build_member_blocks(member):
    """Build Notion blocks for a single team member."""
    blocks = []

    # Name + title as heading
    title_text = member["name"]
    if member.get("title"):
        title_text += f" — {member['title']}"
    blocks.append(_heading(3, title_text))

    # Photo
    if member.get("photo_url"):
        blocks.append({
            "type": "image",
            "image": {
                "type": "external",
                "external": {"url": member["photo_url"]},
            },
        })

    # Bio
    if member.get("bio"):
        # Split bio into chunks of 2000 chars (Notion limit)
        bio = member["bio"]
        while bio:
            chunk = bio[:2000]
            bio = bio[2000:]
            blocks.append(_paragraph(chunk))

    # Education
    if member.get("education"):
        blocks.append(_heading(4, "Education"))
        for edu in member["education"]:
            text = edu.get("school", "")
            if edu.get("degree"):
                text += f" — {edu['degree']}"
            if edu.get("honors"):
                text += f" ({edu['honors']})"
            blocks.append(_bulleted_list(text))

    # Career
    if member.get("career"):
        blocks.append(_heading(4, "Career"))
        for c in member["career"]:
            text = f"{c.get('company', '')} — {c.get('role', '')}"
            if c.get("details"):
                text += f": {c['details']}"
            blocks.append(_bulleted_list(text))

    # Personal
    if member.get("personal"):
        blocks.append(_heading(4, "Personal"))
        for p in member["personal"]:
            blocks.append(_bulleted_list(p))

    return blocks


def _markdown_to_blocks(markdown_text):
    """Convert markdown text to Notion blocks (simplified)."""
    blocks = []
    lines = markdown_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line:
            i += 1
            continue

        if line.startswith("## "):
            blocks.append(_heading(3, line[3:]))
        elif line.startswith("### "):
            blocks.append(_heading(4, line[4:]))
        elif line.startswith("- ") or line.startswith("* "):
            blocks.append(_bulleted_list(line[2:]))
        elif line.startswith("**") and line.endswith("**"):
            blocks.append(_paragraph(line))
        else:
            blocks.append(_paragraph(line))

        i += 1

    return blocks


def _heading(level, text):
    key = f"heading_{level}"
    return {
        "type": key,
        key: {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
        },
    }


def _toggle_heading(level, text, children):
    key = f"heading_{level}"
    return {
        "type": key,
        key: {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
            "is_toggleable": True,
            "children": children[:100] if children else [],
        },
    }


def _paragraph(text):
    # Handle bold markdown in text
    rich_text = _parse_rich_text(text[:2000])
    return {
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text},
    }


def _bulleted_list(text):
    rich_text = _parse_rich_text(text[:2000])
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text},
    }


def _divider():
    return {"type": "divider", "divider": {}}


def _parse_rich_text(text):
    """Parse markdown bold (**text**) into Notion rich text annotations."""
    parts = []
    remaining = text
    while "**" in remaining:
        before, rest = remaining.split("**", 1)
        if "**" in rest:
            bold_text, remaining = rest.split("**", 1)
            if before:
                parts.append({"type": "text", "text": {"content": before}})
            parts.append({
                "type": "text",
                "text": {"content": bold_text},
                "annotations": {"bold": True},
            })
        else:
            remaining = before + "**" + rest
            break
    if remaining:
        parts.append({"type": "text", "text": {"content": remaining}})
    return parts if parts else [{"type": "text", "text": {"content": text}}]
