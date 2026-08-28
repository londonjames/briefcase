import json
import re
from concurrent.futures import ThreadPoolExecutor

import anthropic

from usage_logger import tracked
from prompts import ANALYSIS_PROMPT, GROUNDING_CHECK_ANALYSIS, GROUNDING_CHECK_PROMPT
from structured import ANALYSIS_SCHEMA, GROUNDING_SCHEMA, json_format, parse_json

client = anthropic.Anthropic()


def _normalise(text):
    """Compare quotes to source without tripping over presentation.

    Quotes come back with the source's own markdown emphasis around them, and
    sometimes with a doubled escape sequence where a character belongs. Neither
    changes what the source says, so neither should read as a fabrication.
    """
    if "\\u" in text:
        try:
            text = text.encode("latin-1", "backslashreplace").decode("unicode_escape")
        except (UnicodeDecodeError, UnicodeEncodeError):
            pass
    for a, b in (("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2014", "-"), ("\u2013", "-")):
        text = text.replace(a, b)
    text = re.sub(r"[*_`]", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _supported(quote, source_norm):
    """Is this quote actually in the source?

    Two kinds of loose quoting are honest and shouldn't read as fabrication: an
    ellipsis eliding the middle of a long sentence, and a word or two of framing
    added at the edges ("she is a certified public accountant" for a source that
    says "and is a certified public accountant"). Both are tolerated by matching
    segments in order and by trimming a few words off each end.

    What is never tolerated is a quote whose core does not appear as a
    contiguous run of the source — which is what an invented one looks like.
    """
    q = _normalise(quote)
    if not q:
        return False

    segments = [seg.strip() for seg in re.split(r"\.{3}|\u2026", q) if seg.strip()]

    def run_in_order(parts):
        position = 0
        for part in parts:
            found = source_norm.find(part, position)
            if found == -1:
                return False
            position = found + len(part)
        return True

    if run_in_order(segments):
        return True

    # Retry with up to two words trimmed from each end of the whole quote, so
    # long as most of it still has to match.
    words = q.split()
    for lead in range(3):
        for trail in range(3):
            if lead + trail == 0:
                continue
            trimmed = words[lead : len(words) - trail or None]
            if len(trimmed) < max(4, len(words) * 0.6):
                continue
            if run_in_order([" ".join(trimmed)]):
                return True
    return False


def _safe(fn, arg):
    """Run fn, returning (result, error) — a failed audit must not kill the run."""
    try:
        return fn(arg), None
    except Exception as e:
        return None, str(e)


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

    def audit(batch):
        with tracked("briefcase", "grounding-check") as _t, client.messages.stream(
            model="claude-sonnet-5",
            max_tokens=32000,
            output_config=json_format(GROUNDING_SCHEMA),
            messages=[
                {
                    "role": "user",
                    "content": [
                        # The bios are identical in every batch, so this block is
                        # a stable prefix and gets cached. Without the split the
                        # whole source was re-read at full price each time.
                        {
                            "type": "text",
                            "text": GROUNDING_CHECK_PROMPT.format(source=source_text),
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": GROUNDING_CHECK_ANALYSIS.format(
                                analysis="\n\n".join(
                                    f"## {s['title']}\n{s['content']}" for s in batch
                                )
                            ),
                        },
                    ],
                }
            ],
        ) as stream:
            message = stream.get_final_message()
            _t.log(message)
        return parse_json(message)["claims"]

    # Three sections per call: one call for everything truncates on a big team,
    # one call per section pays to re-audit the same claim six times over.
    batches = [insights[i : i + 3] for i in range(0, len(insights), 3)]
    with ThreadPoolExecutor(max_workers=len(batches) or 1) as executor:
        results = list(executor.map(lambda b: (b, _safe(audit, b)), batches))

    seen_claims = set()
    for batch, (claims, error) in results:
        titles = ", ".join(s["title"] for s in batch)
        if error:
            print(f"Grounding check failed on [{titles}]: {error}", flush=True)
            failed.extend(s["title"] for s in batch)
            continue
        for claim in claims:
            key = (claim.get("person"), claim.get("claim"))
            if key in seen_claims:
                continue
            seen_claims.add(key)
            quote = claim.get("quote")
            if not quote or not _supported(quote, source_norm):
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
