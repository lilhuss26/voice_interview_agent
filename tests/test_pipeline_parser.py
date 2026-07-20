import base64

import pytest

from pipeline.gmail.parser import (
    extract_body,
    extract_email,
    header,
    parse_message,
    strip_quoted_reply,
)


def b64(text):
    # Unpadded, exactly as Gmail returns it.
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def part(mime, text, filename=None):
    node = {"mimeType": mime, "body": {"data": b64(text)}}
    if filename:
        node["filename"] = filename
    return node


@pytest.mark.parametrize("name", ["Subject", "subject", "SUBJECT"])
def test_header_is_case_insensitive(name):
    payload = {"headers": [{"name": name, "value": "hello"}]}
    assert header(payload, "Subject") == "hello"


def test_header_missing_returns_empty_string():
    assert header({"headers": []}, "Subject") == ""
    assert header({}, "From") == ""


def test_single_part_plain_body():
    payload = {"mimeType": "text/plain", "body": {"data": b64("just text")}}
    assert extract_body(payload) == "just text"


def test_multipart_alternative_prefers_plain():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [part("text/plain", "plain wins"), part("text/html", "<p>html</p>")],
    }
    assert extract_body(payload) == "plain wins"


def test_nested_multipart_mixed_is_walked():
    # mixed(alternative(plain, html), attachment) — the shape Gmail's web
    # composer produces when there is an attachment. A one-level scan misses it.
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [
            {
                "mimeType": "multipart/alternative",
                "parts": [
                    part("text/plain", "buried deep"),
                    part("text/html", "<p>nope</p>"),
                ],
            },
            part("application/pdf", "binary", filename="spec.pdf"),
        ],
    }
    assert extract_body(payload) == "buried deep"


def test_attachment_parts_are_skipped():
    payload = {
        "mimeType": "multipart/mixed",
        "parts": [part("text/plain", "attached", filename="notes.txt")],
    }
    assert extract_body(payload) == ""


def test_html_fallback_strips_tags_and_unescapes():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [part("text/html", "<p>a &amp; b</p><br><script>x=1</script>c")],
    }
    body = extract_body(payload)
    assert "a & b" in body
    assert "x=1" not in body
    assert "<" not in body


@pytest.mark.parametrize("text", ["a", "ab", "abc", "abcd", "abcde"])
def test_unpadded_base64_decodes_at_every_length(text):
    payload = {"mimeType": "text/plain", "body": {"data": b64(text)}}
    assert extract_body(payload) == text


def test_undecodable_body_returns_empty_not_raises():
    payload = {"mimeType": "text/plain", "body": {"data": "!!!not base64!!!"}}
    assert extract_body(payload) == ""


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Do the thing.\n\nOn Tue, 1 Jan 2030, Foo <f@b.com> wrote:\n> old", "Do the thing."),
        ("Do the thing.\n\n-----Original Message-----\nold stuff", "Do the thing."),
        ("Do the thing.\n\n" + "_" * 30 + "\nold stuff", "Do the thing."),
        ("Do the thing.\n\n-- \nHussam\nEngineer", "Do the thing."),
        ("Do the thing.\n\nSent from my iPhone", "Do the thing."),
        ("Do the thing.\n> quoted line\n> another", "Do the thing."),
        ("Do the thing.\n\nFrom: a@b.com\nSent: today\nTo: c@d.com", "Do the thing."),
    ],
)
def test_strip_quoted_reply(raw, expected):
    assert strip_quoted_reply(raw) == expected


def test_author_text_is_preserved_verbatim():
    text = "Line one.\n\nLine two with detail.\n\nLine three."
    assert strip_quoted_reply(text) == text


def test_strip_quoted_reply_handles_empty():
    assert strip_quoted_reply("") == ""


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Foo Bar <A@B.com>", "a@b.com"),
        ("a@b.com", "a@b.com"),
        ("  Foo <a@b.com>  ", "a@b.com"),
        ("", ""),
        ("not an address", ""),
    ],
)
def test_extract_email(raw, expected):
    assert extract_email(raw) == expected


def test_parse_message_shape():
    msg = {
        "id": "m123",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "[TASK] do it"},
                {"name": "From", "value": "Foo <a@b.com>"},
            ],
            "body": {"data": b64("body text\n\nOn Mon, X wrote:\n> quoted")},
        },
    }
    assert parse_message(msg) == {
        "message_id": "m123",
        "subject": "[TASK] do it",
        "sender": "Foo <a@b.com>",
        "body": "body text",
    }


def test_parse_message_tolerates_missing_everything():
    assert parse_message({}) == {
        "message_id": "",
        "subject": "",
        "sender": "",
        "body": "",
    }
