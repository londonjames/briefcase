import json
import anthropic
from prompts import ANALYSIS_PROMPT

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
                    s = edu.get("school", "")
                    if edu.get("degree"):
                        s += f", {edu['degree']}"
                    if edu.get("honors"):
                        s += f" ({edu['honors']})"
                    edu_strs.append(s)
                parts.append(f"  Education: {'; '.join(edu_strs)}")
            if member.get("career"):
                career_strs = []
                for c in member["career"]:
                    s = f"{c.get('role', '')} at {c.get('company', '')}"
                    if c.get("details"):
                        s += f" — {c['details']}"
                    career_strs.append(s)
                parts.append(f"  Career: {'; '.join(career_strs)}")
            if member.get("personal"):
                parts.append(f"  Personal: {'; '.join(member['personal'])}")
            team_text_parts.append("\n".join(parts))

    team_text = "\n\n".join(team_text_parts)

    prompt = ANALYSIS_PROMPT.format(
        team_count=team_data["team_count"],
        company=team_data["company"],
        team_data=team_text,
    )

    message = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=16384,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
    )

    response_text = message.content[0].text

    # Extract JSON from response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    insights = json.loads(response_text.strip())

    if progress_callback:
        progress_callback(95, "Finalizing dossier...")

    return insights
