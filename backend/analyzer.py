import anthropic

from usage_logger import tracked
from prompts import ANALYSIS_PROMPT
from structured import ANALYSIS_SCHEMA, json_format, parse_json

client = anthropic.Anthropic()


def generate_insights(team_data, progress_callback=None):
    """Generate rich analytical insights from structured team data using Claude Opus."""
    if progress_callback:
        progress_callback(75, "Generating deep insights with AI (this may take a minute)...")

    # Build a clean text representation of all team members for the prompt
    team_text_parts = []
    for group in team_data.get("groups", []):
        team_text_parts.append(f"\n### {group['name']} ({group['count']} members)\n")
        for member in group.get("members", []):
            parts = [f"**{member['name']}** — {member.get('title', 'N/A')}"]
            if member.get("bio"):
                parts.append(f"  Bio: {member['bio']}")
            if member.get("education"):
                edu_strs = []
                for edu in member["education"]:
                    s = edu.get("school") or ""
                    if edu.get("degree"):
                        s += f", {edu['degree']}"
                    if edu.get("honors"):
                        s += f" ({edu['honors']})"
                    edu_strs.append(s)
                parts.append(f"  Education: {'; '.join(edu_strs)}")
            if member.get("career"):
                career_strs = []
                for c in member["career"]:
                    s = f"{c.get('role') or ''} at {c.get('company') or ''}"
                    if c.get("details"):
                        s += f" — {c['details']}"
                    career_strs.append(s)
                parts.append(f"  Career: {'; '.join(career_strs)}")
            if member.get("personal"):
                parts.append(f"  Personal: {'; '.join(member['personal'])}")
            team_text_parts.append("\n".join(parts))

    team_text = "\n\n".join(team_text_parts)

    # State the coverage explicitly. Left to infer it, the model reads thin data as an
    # invitation to fill the gaps from memory — which is how a roster of names and titles
    # became a dossier full of employers nobody on it ever worked for.
    members = [m for g in team_data.get("groups", []) for m in g.get("members", [])]
    total = len(members) or 1
    coverage = (
        f"EVIDENCE COVERAGE — of {len(members)} people: "
        f"{sum(1 for m in members if m.get('bio'))} have a bio, "
        f"{sum(1 for m in members if m.get('career'))} have prior employers listed, "
        f"{sum(1 for m in members if m.get('education'))} have education listed. "
        "Anything not listed above is absent from the source pages, not absent from their "
        "careers — treat it as unknown and say so."
    )
    if sum(1 for m in members if m.get("bio")) / total < 0.25:
        coverage += (
            " This is a names-and-titles roster with almost no biographical evidence. "
            "Sections that depend on career history should say plainly that the source "
            "page does not carry it, rather than reaching for detail that isn't there."
        )
    team_text = f"{coverage}\n\n{team_text}"

    prompt = ANALYSIS_PROMPT.format(
        team_count=team_data["team_count"],
        company=team_data["company"],
        team_data=team_text,
    )

    # Stream the response so Railway doesn't kill the process during long generation
    with tracked("briefcase", "team-analysis") as _t, client.messages.stream(
        model="claude-sonnet-5",
        max_tokens=64000,
        output_config=json_format(ANALYSIS_SCHEMA),
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    ) as stream:
        message = stream.get_final_message()
        _t.log(message)

    insights = parse_json(message)["sections"]

    if progress_callback:
        progress_callback(95, "Finalizing dossier...")

    return insights
