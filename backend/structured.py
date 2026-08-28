"""Schema-constrained JSON responses from Claude.

Every model call in the pipeline needs JSON back. Asking for it in prose and
parsing the result is unreliable: one unescaped quote inside a markdown string
and json.loads() kills the whole job. `output_config.format` constrains
generation instead, so the response is valid JSON matching the schema.
"""
import json


def json_format(schema):
    """output_config for a response constrained to `schema`."""
    return {"format": {"type": "json_schema", "schema": schema}}


def response_text(message):
    """Text of a message, ignoring thinking and other non-text blocks.

    content[0] is not necessarily the text block — thinking models put a
    thinking block first — so never index into content.
    """
    for block in message.content:
        if getattr(block, "type", None) == "text":
            return block.text
    raise ValueError("Claude returned no text block")


def parse_json(message):
    """Parse the JSON body of a schema-constrained response.

    The schema guarantees valid JSON only for a response that finished. A run
    that hits the output cap is cut off mid-string, so check for that first —
    otherwise it surfaces as a baffling "Unterminated string" parse error.
    """
    if getattr(message, "stop_reason", None) == "max_tokens":
        raise ValueError(
            "Claude hit max_tokens and the JSON was cut off. Raise max_tokens "
            "for this call, or feed it less input."
        )
    return json.loads(response_text(message))


def _member():
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "title": {"type": ["string", "null"]},
            "photo_url": {"type": ["string", "null"]},
            "profile_url": {"type": ["string", "null"]},
            # Leadership pages often carry the whole bio inline and link nowhere.
            # Without this the text is dropped and the analysis has nothing to stand on.
            "bio": {"type": ["string", "null"]},
        },
        "required": ["name", "title", "photo_url", "profile_url", "bio"],
        "additionalProperties": False,
    }


TEAM_SCHEMA = {
    "type": "object",
    "properties": {
        "company": {"type": "string"},
        "groups": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "members": {"type": "array", "items": _member()},
                },
                "required": ["name", "members"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["company", "groups"],
    "additionalProperties": False,
}


PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "bio": {"type": ["string", "null"]},
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "school": {"type": ["string", "null"]},
                    "degree": {"type": ["string", "null"]},
                    "honors": {"type": ["string", "null"]},
                },
                "required": ["school", "degree", "honors"],
                "additionalProperties": False,
            },
        },
        "career": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": ["string", "null"]},
                    "role": {"type": ["string", "null"]},
                    "details": {"type": ["string", "null"]},
                },
                "required": ["company", "role", "details"],
                "additionalProperties": False,
            },
        },
        "personal": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["bio", "education", "career", "personal"],
    "additionalProperties": False,
}


# The dossier is a list of sections, but json_schema needs an object at the
# root, so the sections live under one key and the analyzer unwraps them.
ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["sections"],
    "additionalProperties": False,
}


# The grounding audit: every claim, plus the words from the source that back it.
# A null quote is an unsupported claim; a quote that isn't in the source is too.
GROUNDING_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "person": {"type": "string"},
                    "claim": {"type": "string"},
                    "quote": {"type": ["string", "null"]},
                },
                "required": ["person", "claim", "quote"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}
