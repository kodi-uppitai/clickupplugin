#!/usr/bin/env python3
"""Perplexity API client for Life OS. Supports quick search and deep research."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.perplexity.ai"
KEY_PATH = os.path.expanduser("~/.claude/secrets/perplexity.key")
POLL_INTERVAL = 15
POLL_TIMEOUT = 600  # 10 minutes


def load_api_key():
    if not os.path.exists(KEY_PATH):
        print(f"ERROR: API key not found at {KEY_PATH}", file=sys.stderr)
        print("Create the file with your Perplexity API key (single line).", file=sys.stderr)
        sys.exit(1)
    with open(KEY_PATH) as f:
        key = f.read().strip()
    if not key:
        print(f"ERROR: API key file is empty: {KEY_PATH}", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(method, path, body=None, timeout=120):
    key = load_api_key()
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        try:
            err = json.loads(error_body)
            msg = err.get("error", {}).get("message", error_body)
        except (json.JSONDecodeError, AttributeError):
            msg = error_body
        print(f"ERROR {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print("Request timed out.", file=sys.stderr)
        sys.exit(1)


def format_response(data):
    lines = []
    model = data.get("model", "unknown")
    usage = data.get("usage", {})
    prompt_t = usage.get("prompt_tokens", 0)
    comp_t = usage.get("completion_tokens", 0)

    lines.append(f"=== PERPLEXITY RESULT ===")
    lines.append(f"Model: {model} | Tokens: {prompt_t:,} prompt / {comp_t:,} completion")
    lines.append("")

    # Content
    choices = data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        lines.append(content)
    lines.append("")

    # Citations
    citations = data.get("citations", [])
    if citations:
        lines.append("--- CITATIONS ---")
        for i, cite in enumerate(citations, 1):
            if isinstance(cite, dict):
                title = cite.get("title", "")
                url = cite.get("url", "")
                date = cite.get("date", "")
                label = f"[{i}] {title} - {url}"
                if date:
                    label += f" ({date})"
            else:
                label = f"[{i}] {cite}"
            lines.append(label)
        lines.append("")

    # Related questions
    related = data.get("related_questions", [])
    if related:
        lines.append("--- RELATED QUESTIONS ---")
        for q in related:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)


def cmd_search(args):
    body = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.query}],
        "temperature": 0.2,
        "return_related_questions": True,
    }
    if args.recency:
        body["search_recency_filter"] = args.recency
    if args.domains:
        body["search_domain_filter"] = [d.strip() for d in args.domains.split(",")]

    print(f"Searching with {args.model}...", file=sys.stderr)
    data = api_request("POST", "/chat/completions", body)
    print(format_response(data))


def cmd_research(args):
    if args.status:
        return cmd_research_status(args.status)
    if args.retrieve:
        return cmd_research_retrieve(args.retrieve)
    if not args.query:
        print("ERROR: Provide a query or use --status/--retrieve with a job ID.", file=sys.stderr)
        sys.exit(1)

    # Submit async deep research job
    body = {
        "model": "sonar-deep-research",
        "messages": [{"role": "user", "content": args.query}],
    }
    print("Submitting deep research job...", file=sys.stderr)

    # Try sync first — the /chat/completions endpoint may handle deep research synchronously
    # with a long timeout. If the API returns an async job, we'll poll.
    try:
        data = api_request("POST", "/chat/completions", body, timeout=POLL_TIMEOUT)

        # Check if this is a completed response or an async job
        if data.get("choices"):
            print(format_response(data))
            return

        # If we got a job ID back, switch to polling
        job_id = data.get("id")
        if job_id and data.get("status"):
            print(f"Job ID: {job_id}", file=sys.stderr)
            poll_research_job(job_id)
            return

        # Unknown format — print raw
        print(json.dumps(data, indent=2))
    except SystemExit:
        raise
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def poll_research_job(job_id):
    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        elapsed = int(time.time() - start)
        print(f"  Polling... ({elapsed}s elapsed)", file=sys.stderr)

        data = api_request("GET", f"/chat/completions/{job_id}")
        status = data.get("status", "")

        if status == "COMPLETED" or data.get("choices"):
            print(format_response(data))
            return
        elif status == "FAILED":
            print(f"Research job FAILED: {data.get('error', 'unknown error')}", file=sys.stderr)
            sys.exit(1)

    print(f"Timed out after {POLL_TIMEOUT}s. Job ID: {job_id}", file=sys.stderr)
    print("Use: research --retrieve <job-id> to check later.", file=sys.stderr)
    sys.exit(2)


def cmd_research_status(job_id):
    data = api_request("GET", f"/chat/completions/{job_id}")
    status = data.get("status", "unknown")
    print(f"Job {job_id}: {status}")
    if status == "COMPLETED" and data.get("choices"):
        print(format_response(data))


def cmd_research_retrieve(job_id):
    data = api_request("GET", f"/chat/completions/{job_id}")
    if data.get("choices"):
        print(format_response(data))
    else:
        status = data.get("status", "unknown")
        print(f"Job {job_id}: {status} (not yet complete)")


def main():
    parser = argparse.ArgumentParser(description="Perplexity API — search and deep research")
    sub = parser.add_subparsers(dest="command")

    # search
    sp = sub.add_parser("search", help="Quick web search (sonar-pro)")
    sp.add_argument("query", help="Search query")
    sp.add_argument("--recency", choices=["hour", "day", "week", "month", "year"],
                     help="Filter by recency")
    sp.add_argument("--domains", help="Comma-separated domain filter")
    sp.add_argument("--model", default="sonar-pro",
                     choices=["sonar", "sonar-pro", "sonar-reasoning-pro"],
                     help="Model (default: sonar-pro)")

    # research
    rp = sub.add_parser("research", help="Deep research (sonar-deep-research)")
    rp.add_argument("query", nargs="?", help="Research query")
    rp.add_argument("--status", metavar="JOB_ID", help="Check status of a job")
    rp.add_argument("--retrieve", metavar="JOB_ID", help="Retrieve completed job")

    args = parser.parse_args()

    if args.command == "search":
        cmd_search(args)
    elif args.command == "research":
        cmd_research(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
