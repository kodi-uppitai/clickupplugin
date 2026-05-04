#!/usr/bin/env python3
"""Apify API client for Life OS. Supports LinkedIn profile search and company employee scraping."""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_BASE = "https://api.apify.com/v2"
KEY_PATH = os.path.expanduser("~/.claude/secrets/apify.key")
POLL_INTERVAL = 10
POLL_TIMEOUT = 300  # 5 minutes


def load_api_key():
    if not os.path.exists(KEY_PATH):
        print(f"ERROR: API key not found at {KEY_PATH}", file=sys.stderr)
        print("Create the file with your Apify API token (single line).", file=sys.stderr)
        sys.exit(1)
    with open(KEY_PATH) as f:
        key = f.read().strip()
    if not key:
        print(f"ERROR: API key file is empty: {KEY_PATH}", file=sys.stderr)
        sys.exit(1)
    return key


def api_request(method, url, body=None, timeout=120):
    headers = {"Content-Type": "application/json"}
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


def run_actor(actor_id, input_data):
    """Start an actor run and poll until completion. Returns dataset items."""
    token = load_api_key()
    url = f"{API_BASE}/acts/{actor_id}/runs?token={token}"

    print(f"Starting actor {actor_id}...", file=sys.stderr)
    result = api_request("POST", url, input_data)
    run_data = result.get("data", result)
    run_id = run_data["id"]
    ds_id = run_data["defaultDatasetId"]
    status = run_data.get("status", "")

    print(f"Run ID: {run_id}", file=sys.stderr)

    # Poll for completion
    start = time.time()
    while status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
        if time.time() - start > POLL_TIMEOUT:
            print(f"Timed out after {POLL_TIMEOUT}s. Run ID: {run_id}", file=sys.stderr)
            sys.exit(2)
        time.sleep(POLL_INTERVAL)
        elapsed = int(time.time() - start)
        print(f"  Polling... ({elapsed}s elapsed)", file=sys.stderr)
        poll_url = f"{API_BASE}/actor-runs/{run_id}?token={token}"
        poll_result = api_request("GET", poll_url)
        status = poll_result.get("data", poll_result).get("status", "")

    if status != "SUCCEEDED":
        # Print log for debugging
        log_url = f"{API_BASE}/actor-runs/{run_id}/log?token={token}"
        try:
            log_req = urllib.request.Request(log_url)
            with urllib.request.urlopen(log_req, timeout=30) as resp:
                log = resp.read().decode()
                print(f"Run {status}. Log tail:\n{log[-500:]}", file=sys.stderr)
        except Exception:
            print(f"Run {status}. Could not retrieve log.", file=sys.stderr)
        sys.exit(1)

    # Fetch dataset items
    items_url = f"{API_BASE}/datasets/{ds_id}/items?token={token}"
    items_req = urllib.request.Request(items_url)
    with urllib.request.urlopen(items_req, timeout=60) as resp:
        items = json.loads(resp.read().decode())

    print(f"Completed. {len(items)} profiles found.", file=sys.stderr)
    return items


def format_profiles(items):
    lines = []
    lines.append(f"=== APIFY LINKEDIN RESULTS ===")
    lines.append(f"Profiles found: {len(items)}")
    lines.append("")

    for i, item in enumerate(items, 1):
        name = f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
        headline = item.get("headline", "N/A")
        linkedin_url = item.get("linkedinUrl", "N/A")
        about = item.get("about", "") or ""

        # Location
        loc = item.get("location", {})
        if isinstance(loc, dict):
            location = loc.get("linkedinText", "N/A")
        else:
            location = str(loc) if loc else "N/A"

        # Current position(s)
        positions = item.get("currentPosition", []) or []
        current_roles = []
        for pos in positions:
            company = pos.get("companyName", "")
            title_text = pos.get("title", "")
            if company:
                current_roles.append(f"{title_text} at {company}" if title_text else company)

        # Past positions
        past_positions = item.get("pastPosition", []) or []
        past_roles = []
        for pos in past_positions:
            company = pos.get("companyName", "")
            title_text = pos.get("title", "")
            if company:
                past_roles.append(f"{title_text} at {company}" if title_text else company)

        lines.append(f"[{i}] {name}")
        lines.append(f"    Headline: {headline}")
        if current_roles:
            lines.append(f"    Current: {'; '.join(current_roles)}")
        if past_roles:
            lines.append(f"    Past: {'; '.join(past_roles[:5])}")
        lines.append(f"    Location: {location}")
        lines.append(f"    URL: {linkedin_url}")
        if about:
            summary = about[:200].replace("\n", " ").strip()
            if len(about) > 200:
                summary += "..."
            lines.append(f"    About: {summary}")
        lines.append("")

    return "\n".join(lines)


def cmd_linkedin_search(args):
    input_data = {}

    if args.titles:
        input_data["currentJobTitles"] = [t.strip() for t in args.titles.split(",")]
    if args.companies:
        input_data["companies"] = [c.strip() for c in args.companies.split(",")]
    if args.locations:
        input_data["locations"] = [l.strip() for l in args.locations.split(",")]
    if args.past_companies:
        input_data["pastCompanies"] = [c.strip() for c in args.past_companies.split(",")]

    input_data["maxItems"] = args.limit

    if not input_data.get("currentJobTitles") and not input_data.get("companies"):
        print("ERROR: Provide at least --titles or --companies.", file=sys.stderr)
        sys.exit(1)

    print(f"Searching LinkedIn profiles...", file=sys.stderr)
    print(f"  Filters: {json.dumps(input_data)}", file=sys.stderr)

    items = run_actor("harvestapi~linkedin-profile-search", input_data)
    output = format_profiles(items)
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def cmd_company_employees(args):
    companies = [c.strip() for c in args.companies.split(",")]
    input_data = {
        "companies": companies,
        "maxItems": args.limit,
    }

    print(f"Scraping employees from: {', '.join(companies)}", file=sys.stderr)

    items = run_actor("harvestapi~linkedin-company-employees", input_data)
    output = format_profiles(items)
    sys.stdout.buffer.write(output.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")


def main():
    parser = argparse.ArgumentParser(description="Apify API — LinkedIn profile search and scraping")
    sub = parser.add_subparsers(dest="command")

    # linkedin-search
    sp = sub.add_parser("linkedin-search", help="Search LinkedIn profiles by title, company, location")
    sp.add_argument("--titles", help="Comma-separated job titles (e.g., 'VP Engineering,Head of Engineering')")
    sp.add_argument("--companies", help="Comma-separated LinkedIn company URLs or names")
    sp.add_argument("--past-companies", help="Comma-separated LinkedIn company URLs for past employers")
    sp.add_argument("--locations", help="Comma-separated locations (e.g., 'New York,San Francisco')")
    sp.add_argument("--limit", type=int, default=10, help="Max results (default: 10, cap: 50)")

    # company-employees
    ep = sub.add_parser("company-employees", help="Get all employees of a company")
    ep.add_argument("companies", help="Comma-separated LinkedIn company URLs")
    ep.add_argument("--limit", type=int, default=25, help="Max results (default: 25, cap: 100)")

    args = parser.parse_args()

    # Cap limits
    if hasattr(args, "limit"):
        if args.command == "linkedin-search":
            args.limit = min(args.limit, 50)
        elif args.command == "company-employees":
            args.limit = min(args.limit, 100)

    if args.command == "linkedin-search":
        cmd_linkedin_search(args)
    elif args.command == "company-employees":
        cmd_company_employees(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
