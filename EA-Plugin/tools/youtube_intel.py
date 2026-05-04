"""
YouTube Investment Intelligence Tool
Fetches recent videos from monitored channels, grabs transcripts,
and outputs structured data for investment analysis.

Usage:
    python tools/youtube_intel.py                  # Check all channels, last 24h
    python tools/youtube_intel.py --hours 48       # Check last 48 hours
    python tools/youtube_intel.py --max-videos 5   # Max videos per channel
    python tools/youtube_intel.py --channel pizzino # Single channel by alias
    python tools/youtube_intel.py --video URL      # Single video by URL
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

APIFY_KEY_PATH = os.path.expanduser("~/.claude/secrets/apify.key")
APIFY_ACTOR = "supreme_coder~youtube-transcript-scraper"

# ── Monitored Channels ──────────────────────────────────────────────
CHANNELS = {
    "pizzino": {
        "name": "Jason Pizzino",
        "url": "https://www.youtube.com/@JasonPizzinoOfficial/videos",
        "focus": "Technical analysis, macro cycles, swing trading signals (BTC, stocks, commodities)",
    },
    "cryptoverse": {
        "name": "Benjamin Cowen (Into The Cryptoverse)",
        "url": "https://www.youtube.com/@intothecryptoverse/videos",
        "focus": "Quantitative crypto analysis, risk metrics, BTC dominance, ETH ratios, cycle theory",
    },
}


def get_recent_videos(channel_url: str, max_videos: int = 5) -> list[dict]:
    """Fetch recent video metadata from a YouTube channel."""
    opts = {
        "quiet": True,
        "extract_flat": True,
        "playlist_items": f"1-{max_videos}",
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        entries = info.get("entries", [])
        return [
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "url": e.get("url"),
            }
            for e in entries
            if e
        ]


def get_upload_date(video_id: str) -> str | None:
    """Fetch actual upload date for a video."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        return info.get("upload_date")  # YYYYMMDD format


def get_transcript(video_id: str) -> str | None:
    """Fetch transcript via free API first, fall back to Apify if rate-limited."""
    # Try free API first
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id)
        return " ".join([s.text for s in transcript.snippets])
    except Exception as e:
        err_str = str(e).lower()
        if "ipblocked" in err_str or "blocked" in err_str or "429" in err_str:
            print(f"  Free API blocked, trying Apify fallback...", file=sys.stderr)
            return get_transcript_apify(video_id)
        return None


def get_transcript_apify(video_id: str) -> str | None:
    """Fetch transcript via Apify actor (paid fallback)."""
    if not os.path.exists(APIFY_KEY_PATH):
        print(f"  Apify key not found at {APIFY_KEY_PATH}", file=sys.stderr)
        return None
    with open(APIFY_KEY_PATH) as f:
        token = f.read().strip()
    if not token:
        return None

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    api_base = "https://api.apify.com/v2"
    body = json.dumps({"urls": [{"url": video_url}]}).encode()

    try:
        # Start run
        req = urllib.request.Request(
            f"{api_base}/acts/{APIFY_ACTOR}/runs?token={token}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        run_data = result.get("data", result)
        run_id = run_data["id"]
        ds_id = run_data["defaultDatasetId"]
        status = run_data.get("status", "")

        # Poll for completion
        start = time.time()
        while status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            if time.time() - start > 180:
                print(f"  Apify timed out after 180s", file=sys.stderr)
                return None
            time.sleep(10)
            poll_req = urllib.request.Request(f"{api_base}/actor-runs/{run_id}?token={token}")
            poll_resp = urllib.request.urlopen(poll_req, timeout=30)
            poll_data = json.loads(poll_resp.read().decode())
            status = poll_data.get("data", poll_data).get("status", "")

        if status != "SUCCEEDED":
            print(f"  Apify run {status}", file=sys.stderr)
            return None

        # Fetch dataset
        items_req = urllib.request.Request(f"{api_base}/datasets/{ds_id}/items?token={token}")
        items_resp = urllib.request.urlopen(items_req, timeout=60)
        items = json.loads(items_resp.read().decode())

        for item in items:
            raw = item.get("transcript", item.get("transcript_llm", item.get("text", "")))
            if isinstance(raw, list):
                return " ".join([seg.get("text", "") for seg in raw])
            return str(raw) if raw else None

    except Exception as e:
        print(f"  Apify error: {e}", file=sys.stderr)
        return None


def filter_recent(videos: list[dict], hours: int) -> list[dict]:
    """Filter videos to only those uploaded within the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    cutoff_str = cutoff.strftime("%Y%m%d")
    recent = []
    for v in videos:
        upload_date = get_upload_date(v["id"])
        if upload_date and upload_date >= cutoff_str:
            v["upload_date"] = upload_date
            recent.append(v)
    return recent


def run(hours: int = 24, max_videos: int = 5, channel_alias: str | None = None):
    """Main entry point. Returns structured dict of channel data."""
    channels = CHANNELS
    if channel_alias:
        if channel_alias not in CHANNELS:
            print(f"Unknown channel alias: {channel_alias}", file=sys.stderr)
            print(f"Available: {', '.join(CHANNELS.keys())}", file=sys.stderr)
            sys.exit(1)
        channels = {channel_alias: CHANNELS[channel_alias]}

    results = {}
    for alias, ch in channels.items():
        print(f"Checking {ch['name']}...", file=sys.stderr)
        videos = get_recent_videos(ch["url"], max_videos)
        recent = filter_recent(videos, hours)

        channel_data = {
            "name": ch["name"],
            "focus": ch["focus"],
            "videos_checked": len(videos),
            "new_videos": [],
        }

        for v in recent:
            print(f"  Fetching transcript: {v['title']}", file=sys.stderr)
            transcript = get_transcript(v["id"])
            channel_data["new_videos"].append(
                {
                    "title": v["title"],
                    "url": v["url"],
                    "upload_date": v.get("upload_date"),
                    "transcript": transcript,
                    "has_transcript": transcript is not None,
                }
            )

        results[alias] = channel_data

    return results


def run_single_video(video_url: str):
    """Fetch transcript for a single video URL."""
    # Extract video ID
    video_id = video_url.split("v=")[-1].split("&")[0]

    # Get metadata
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

    print(f"Fetching transcript: {info.get('title', 'Unknown')}", file=sys.stderr)
    transcript = get_transcript(video_id)

    return {
        "single_video": {
            "title": info.get("title"),
            "channel": info.get("channel"),
            "upload_date": info.get("upload_date"),
            "url": video_url,
            "transcript": transcript,
            "has_transcript": transcript is not None,
        }
    }


def main():
    parser = argparse.ArgumentParser(description="YouTube Investment Intelligence")
    parser.add_argument("--hours", type=int, default=24, help="Look back window in hours (default: 24)")
    parser.add_argument("--max-videos", type=int, default=5, help="Max videos to check per channel (default: 5)")
    parser.add_argument("--channel", type=str, default=None, help="Single channel alias to check")
    parser.add_argument("--video", type=str, default=None, help="Single video URL to fetch transcript for")
    args = parser.parse_args()

    if args.video:
        results = run_single_video(args.video)
    else:
        results = run(hours=args.hours, max_videos=args.max_videos, channel_alias=args.channel)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
