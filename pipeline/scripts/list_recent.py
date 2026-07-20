"""Local smoke test for Task 1.1: auth once, print the 10 newest emails.

This is the ONLY entry point that may open a browser. Run it on your laptop to
mint pipeline/token.json, then produce the production value with:

    base64 -w0 pipeline/token.json

Prints nothing derived from the token itself.
"""

from pipeline.auth.gmail_auth import get_gmail_service
from pipeline.gmail.parser import parse_message

PREVIEW_CHARS = 200


def main() -> None:
    service = get_gmail_service(allow_interactive=True)
    messages = (
        service.users()
        .messages()
        .list(userId="me", maxResults=10)
        .execute()
        .get("messages", [])
    )

    if not messages:
        print("no messages found")
        return

    for i, ref in enumerate(messages, 1):
        raw = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        parsed = parse_message(raw)
        preview = parsed["body"][:PREVIEW_CHARS].replace("\n", " ")
        print(f"\n--- {i} ---")
        print(f"subject: {parsed['subject']}")
        print(f"sender : {parsed['sender']}")
        print(f"body   : {preview}")


if __name__ == "__main__":
    main()
