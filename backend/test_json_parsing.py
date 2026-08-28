"""Regression tests for parsing JSON out of Claude responses.

The pipeline used to ask for JSON in prose and parse it with a markdown-fence
split plus json.loads(). That fails whenever the model emits an unescaped quote
inside a string value, which killed whole jobs intermittently
(e.g. "Expecting ',' delimiter: line 8 column 1277").
"""
import json
import sys
import types

sys.path.insert(0, __import__("os").path.dirname(__file__))


def legacy_parse(response_text):
    """The old parsing path, kept here only to document what used to break."""
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]
    return json.loads(response_text.strip())


# A realistic analyzer response: markdown content containing an unescaped quote.
UNESCAPED_QUOTE = '''```json
[
  {
    "title": "Cultural DNA",
    "content": "The team calls itself "the seed mafia" in public talks."
  }
]
```'''

# A realistic response where the model wrote prose around the JSON.
PROSE_WRAPPED = '''Here is the analysis you asked for:

[{"title": "Standouts", "content": "Satya Patel co-founded Homebrew."}]'''


def test_legacy_parser_breaks_on_unescaped_quote():
    try:
        legacy_parse(UNESCAPED_QUOTE)
    except json.JSONDecodeError:
        return
    raise AssertionError("expected the legacy parser to fail on an unescaped quote")


def test_legacy_parser_breaks_on_prose_wrapped_json():
    try:
        legacy_parse(PROSE_WRAPPED)
    except json.JSONDecodeError:
        return
    raise AssertionError("expected the legacy parser to fail on prose-wrapped JSON")


def test_response_text_skips_non_text_blocks():
    """content[0] is not guaranteed to be the text block on thinking models."""
    from structured import response_text

    message = types.SimpleNamespace(
        stop_reason="end_turn",
        content=[
            types.SimpleNamespace(type="thinking", thinking="hmm"),
            types.SimpleNamespace(type="text", text='{"ok": true}'),
        ],
    )
    assert response_text(message) == '{"ok": true}'


def test_parse_json_reads_the_text_block():
    from structured import parse_json

    message = types.SimpleNamespace(
        stop_reason="end_turn",
        content=[
            types.SimpleNamespace(type="thinking", thinking="hmm"),
            types.SimpleNamespace(type="text", text='{"sections": []}'),
        ],
    )
    assert parse_json(message) == {"sections": []}


def test_parse_json_reports_truncation_clearly():
    """Hitting max_tokens truncates the JSON; say so instead of a parse error."""
    from structured import parse_json

    message = types.SimpleNamespace(
        stop_reason="max_tokens",
        content=[types.SimpleNamespace(type="text", text='{"sections": [{"title": "Cul')],
    )
    try:
        parse_json(message)
    except ValueError as e:
        assert "max_tokens" in str(e), f"unhelpful message: {e}"
        return
    raise AssertionError("expected a truncation error")


def test_parse_json_reports_truncation_with_no_text_block():
    """A truncated response can come back with no complete text block at all."""
    from structured import parse_json

    message = types.SimpleNamespace(stop_reason="max_tokens", content=[])
    try:
        parse_json(message)
    except ValueError as e:
        assert "max_tokens" in str(e), f"unhelpful message: {e}"
        return
    raise AssertionError("expected a truncation error")


def test_schemas_are_strict():
    """json_schema output requires every object to be closed and fully required."""
    from structured import ANALYSIS_SCHEMA, PROFILE_SCHEMA, TEAM_SCHEMA

    def check(node, path="root"):
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, f"{path}: additionalProperties must be False"
            props = set(node.get("properties", {}))
            assert set(node.get("required", [])) == props, f"{path}: every property must be required"
            for key, child in node.get("properties", {}).items():
                check(child, f"{path}.{key}")
        if node.get("type") == "array":
            check(node.get("items", {}), f"{path}[]")

    for name, schema in [("TEAM", TEAM_SCHEMA), ("PROFILE", PROFILE_SCHEMA), ("ANALYSIS", ANALYSIS_SCHEMA)]:
        check(schema, name)


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                failures += 1
                print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
