---
description: "Daily planning scan — pulls meeting transcripts, ClickUp DMs, surfaces discussion items, and identifies today's one thing. 5-10 min max."
---

# Daily Planning Scan

You are running Jon Morrow's daily planning scan. This is a lightweight check-in — not a session. 5-10 minutes max.

## Context

- Jon has SMA type II. Max 2 deep work blocks/day. If health is mentioned, triage to essentials only.
- Timezone, user ID, and paths: loaded from `config.json`
- Task file: `tasks/current-week.md` in the Life OS repo
- Discussion items: `tasks/discussion-items.md`
- Progress log: `progress/` directory (current month file)
- Active OTAs: `business/OTA-*.md` and `personal/OTA-*.md`

## Step 1: Anchor to the Week (~1 min)

Read `tasks/current-week.md`. Review:
- What's already done (check off any completed items Jon mentioned)
- What's left
- What has a deadline today or tomorrow

## Step 2: Review Fireflies Transcripts (~2 min)

Pull transcripts from the previous day's meetings via Fireflies GraphQL API.

@reference/fireflies.md

Query recent transcripts, filter to last 24 hours by checking the `date` field (epoch ms). Use `limit: 15` to ensure full coverage on days with multiple meetings.

For each transcript:
- Read `summary.action_items` for anything assigned to Jon or waiting on Jon
- Read `summary.overview` for key decisions or status changes
- Cross-reference against `tasks/current-week.md` and active OTAs
- Surface anything Jon needs to follow up on today

**Report every transcript within the 24h window — do not stop after the first one.**

## Step 3: Check ClickUp DMs (~1-2 min)

Scan ClickUp direct messages from the last 24 hours for anything Jon needs to act on.

@reference/clickup.md

Steps:
1. Fetch all channels, filter to DMs with recent activity (last 24h by `latest_comment_at`)
2. For each recent DM, get members and messages
3. Filter to messages from others (not the current user's ID from config)
4. Interpret: did anyone ask Jon to do something, or did Jon agree to do something?

Present findings as:
- "**[Name]** — [N] messages in the last 24h"
- Numbered list of action items / requests / questions
- If no action items in a DM, say so briefly and move on

## Step 4: Surface Discussion Items (~1 min)

Check today's calendar for meetings (use Google Calendar MCP `list-events` for today). For each meeting, look up the attendee in `tasks/discussion-items.md`. If there are open discussion items for that person, surface them:
- "You have a call with [person] at [time]. Open discussion items: [list]"

If no items exist for any of today's meeting attendees, skip this step.

## Step 5: Identify Today's One Thing (~1 min)

From the remaining tasks, name the single most important thing to accomplish today:
- If anything has a same-day or next-day deadline → that's the one thing
- If nothing is urgent → pick from the most-behind OTA
- If Jon is low-energy → pick the smallest completable task that still moves something forward
- Deep work tasks go to morning. Delegation and communication go to afternoon.

## Step 6: Surface Flags (~1 min)

Check if anything:
- Hits a deadline in the next 3 days
- Is waiting on someone else and hasn't moved in 48+ hours
- Jon said he'd do yesterday and didn't mention

If yes → name it. One sentence. Don't bury it.

## Step 7: Handle Quick Tasks (~1 min)

Check the **Quick Tasks** section in `tasks/current-week.md`:
- If something was completed → check it off
- If Jon mentions a new small task (<15 min) → add it there, not to the main priorities
- If a quick task has been sitting there 3+ days → either do it today or delete it

## Step 8: Confirm and Move (~1 min)

Output to Jon:
1. Discussion items for today's meetings (if any)
2. Today's one thing (with time block suggestion if useful)
3. Any flags (optional — only if they exist)
4. Anything he should delegate or batch-send today

## Energy Rules

- Never assign more than 1 deep work block per day unless Jon explicitly asks
- If Jon mentions fatigue, pain, or a rough health morning → skip everything except the one most critical item
- Nurse schedule and appointments take priority over any task

## File Updates

Only update files if:
- A task was completed → check it off in `tasks/current-week.md`
- A priority shifted → update `tasks/current-week.md`
- A deadline was confirmed or changed → update the relevant OTA
- Jon reported progress → note it in `progress/{current-month}.md`
