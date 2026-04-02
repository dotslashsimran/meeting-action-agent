#!/usr/bin/env python3
"""
meeting-action-agent — CLI entry point.

Usage:
  python main.py --demo
  python main.py --file transcript.txt
  python main.py --text "Alice: do the thing. Bob: I'll handle it."
  cat transcript.txt | python main.py
"""

import argparse
import sys
import os
from dotenv import load_dotenv

# Load environment variables before importing crew (which imports crewai/litellm)
load_dotenv()

DEMO_TRANSCRIPT = """Meeting: Q2 Planning - April 2, 2026
Attendees: Sarah (PM), Marcus (Engineer), Priya (Design), Tom (QA)

Sarah: Let's kick off. Marcus, can you finish the API integration by Friday?
Marcus: Yes, I'll have it done by end of week.
Sarah: Great. Priya, we need the new onboarding screens designed before Marcus starts the frontend work. Can you get those to us by Wednesday?
Priya: Sure, Wednesday works.
Sarah: Tom, once Marcus is done, we need full regression testing completed before the April 15th release.
Tom: Got it, I'll schedule the test runs.
Sarah: I'll send the updated roadmap to the stakeholders today. Also, Marcus, don't forget to update the API documentation.
Marcus: Will do.
Sarah: One more thing — someone needs to set up the staging environment. Tom, can you handle that?
Tom: Sure, I'll do it tomorrow.
"""


def print_banner():
    print("=" * 60)
    print("  Meeting Action Agent")
    print("  Powered by CrewAI + Groq + Notion")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Extract action items from a meeting transcript and push to Notion."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--demo", action="store_true", help="Run with built-in demo transcript")
    group.add_argument("--file", metavar="PATH", help="Path to a transcript text file")
    group.add_argument("--text", metavar="TRANSCRIPT", help="Transcript as a string argument")

    args = parser.parse_args()

    print_banner()

    # Determine transcript source
    if args.demo:
        print("[Source] Using built-in demo transcript.\n")
        transcript = DEMO_TRANSCRIPT
    elif args.file:
        print(f"[Source] Reading transcript from file: {args.file}\n")
        with open(args.file, "r", encoding="utf-8") as f:
            transcript = f.read()
    elif args.text:
        print("[Source] Using transcript from --text argument.\n")
        transcript = args.text
    elif not sys.stdin.isatty():
        print("[Source] Reading transcript from stdin.\n")
        transcript = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    # Validate required env vars
    missing = [v for v in ("GROQ_API_KEY", "NOTION_TOKEN", "NOTION_DATABASE_ID") if not os.getenv(v)]
    if missing:
        print(f"[Error] Missing environment variables: {', '.join(missing)}")
        print("        Please set them in your .env file.")
        sys.exit(1)

    print("[Transcript Preview]")
    preview = transcript.strip()[:300]
    print(preview + ("..." if len(transcript.strip()) > 300 else ""))
    print()
    print("[Starting agents...]\n")

    # Import crew here so env vars are already loaded
    from src.crew import run

    result = run(transcript)

    print()
    print("=" * 60)
    print("  FINAL RESULT")
    print("=" * 60)
    print(result)
    print()
    print("[Done] Action items have been published to Notion.")


if __name__ == "__main__":
    main()
