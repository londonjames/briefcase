import json
import re

import anthropic

from usage_logger import tracked
from prompts import ANALYSIS_PROMPT, GROUNDING_CHECK_PROMPT
from structured import ANALYSIS_SCHEMA, GROUNDING_SCHEMA, json_format, parse_json

client = anthropic.Anthropic()


def _normalise(text):
    """Compare quotes to source without tripping over smart quotes or wrapping."""
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2014", "-"), ("\u2013", "-")):
        text = text.replace(a, b)
    return re.sub(r"\s+", " ", text).strip().lower()


def check_grounding(insights, source_text):
    """Find claims in the analysis that the source pages don't support.

    The model proposes a supporting quote for each claim; this function decides
    whether the quote is real by matching it against the source. That split
    matters — an auditor that is only asked "is this supported?" will happily
    say yes about something it invented, but it cannot fake a string match.

    Audited one section at a time: a big team's six sections produce more claims
    than one response can hold, and a truncated audit is worse than a partial one
    because it looks complete. A section that fails is reported, never fatal —
    a check that can take down the thing it is checking is not a safety net.
    """
    source_norm = _normalise(source_text)
    unsupported, failed = [], []

    for section in insights:
        try:
            with tracked("briefcase", "grounding-check") as _t, client.messages.stream(
                model="claude-sonnet-5",
                max_tokens=64000,
                output_config=json_format(GROUNDING_SCHEMA),
                messages=[
                    {
                        "role": "user",
                        "content": GROUNDING_CHECK_PROMPT.format(
                            source=source_text,
                            analysis=f"## {section['title']}\n{section['content']}",
                        ),
                    }
                ],
            ) as stream:
                message = stream.get_final_message()
                _t.log(message)
            claims = parse_json(message)["claims"]
        except Exception as e:
            print(f"Grounding check failed on '{section['title']}': {e}", flush=True)
            failed.append(section["title"])
            continue

        for claim in claims:
            quote = claim.get("quote")
            if not quote or _normalise(quote) not in source_norm:
                unsupported.append(claim)

    if failed:
        print(f"Grounding: {len(failed)} sections unaudited: {failed}", flush=True)
    return unsupported


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
        progress_callback(88, "Checking every claim against the source pages...")

    unsupported = check_grounding(insights, team_text)
    if unsupported:
        print(f"Grounding: {len(unsupported)} unsupported claims, rewriting", flush=True)
        if progress_callback:
            progress_callback(92, f"Removing {len(unsupported)} unsupported claims...")

        listed = "\n".join(
            f"- {c['person']}: {c['claim']}" for c in unsupported
        )
        with tracked("briefcase", "team-analysis-repair") as _t, client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=64000,
            output_config=json_format(ANALYSIS_SCHEMA),
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": json.dumps({"sections": insights})},
                {
                    "role": "user",
                    "content": (
                        "An audit found these claims nowhere in the team data:\n\n"
                        f"{listed}\n\n"
                        "Each one was invented. Return the six sections again with every "
                        "one of them removed — delete the sentence, or rewrite it to say "
                        "only what the data supports. Do not replace them with different "
                        "unsupported claims, and do not weaken the rest of the analysis "
                        "while you are in there."
                    ),
                },
            ],
        ) as stream:
            repaired = stream.get_final_message()
            _t.log(repaired)
        insights = parse_json(repaired)["sections"]
        unsupported = check_grounding(insights, team_text)
        if unsupported:
            print(f"Grounding: {len(unsupported)} claims still unsupported", flush=True)

    if progress_callback:
        progress_callback(95, "Finalizing dossier...")

    return insights, unsupported
