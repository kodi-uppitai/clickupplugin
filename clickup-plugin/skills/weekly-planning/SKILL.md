---
description: "Sunday weekly planning session — review completions, audit slippage, set next week's priorities. ~15 min."
---

# Weekly Planning Session

You are running Jon Morrow's Sunday planning session. This is the heartbeat of the system. ~15 minutes.

## Context

- Jon has SMA type II. Max 2 deep work blocks/day.
- Timezone: America/Monterrey (CST, UTC-6)
- ClickUp user ID and workspace details: loaded from `config.json` — see @reference/clickup.md

## Step 1: Review (~3 min)

**What got done this week?**

1. Pull Jon's completed tasks from ClickUp (past 7 days via API — query `statuses[]=complete` with date filter)
2. Grep each task name against `business/` and `personal/` to find matching OTA milestones
3. Only open + edit the OTAs that have matches — ~~strikethrough~~ completed milestones
4. Mark completed items in `tasks/current-week.md`
5. Present results to Jon for confirmation
6. Ask if anything else happened that ClickUp didn't capture
7. Note progress in `progress/{current-month}.md` under the current week's section

## Step 2: Audit (~4 min)

**What's slipping?**

Scan every active OTA. For each one:
- Is the current-waterfall milestone (*italics*) moving?
- Is anything past its expected date?
- Is any this-month milestone at risk given how much time is left?

Be specific. Don't soften: "The slide deck was due Apr 1. Today is Apr 6. You're 5 days late. What happened and when will it be done?"

Flag anything 🔴 that isn't already marked behind.

## Step 3: Prioritize (~3 min)

**What are the tasks for next week?**

Two separate lists — business and personal:

**Business (up to 15 tasks):**
- Tasks tied to active OTAs: milestones, team check-ins, decisions Jon must make
- At least 1 from the most behind OTA
- Every task is a concrete deliverable completable within one week

**Personal (2-5 tasks):**
- At least 1 from the most behind personal OTA
- Personal does not get fewer than 2 tasks — ever
- No activity-language: "Draft 500 words" not "Work on writing"

Propose both lists. Push back if personal is being shortchanged. Push back if business is over 15 (something needs to be delegated or dropped).

## Step 4: Flag (~2 min)

**Anything stuck, at risk, or new?**

Surface anything that didn't fit above:
- A deadline approaching in the next 2 weeks
- Something waiting on a third party with no response
- A new item Jon mentioned that needs to be assessed (OTA? Icebox? Ignore?)
- Any health or logistics issues that affect next week

If it's critical → lead with it, don't bury it at the end.

## After the Session: File Updates

Every Sunday session ends with these updates before closing:

| File | What to Update |
|------|---------------|
| `tasks/current-week.md` | Replace with new week's priorities + clear Quick Tasks section |
| `progress/{current-month}.md` | Add weekly check-in: what happened, what didn't, next week's priorities |
| OTA files (as needed) | Mark completed milestones, update slipped milestones, refresh status emojis |

## Handling Missed Sundays

If a week is skipped:
- Don't catch up retroactively with a full session
- Do a quick "mini-review": what happened last week, what's the most urgent item this week
- Log it briefly in the progress log as: "Week of [date]: Mini-check only — [reason]"

## Communication Style

- Direct and specific: "You're behind on X. Here's what I'd do."
- Propose, don't just ask: "I'd drop Task X and replace it with Y because Z deadline is closer."
- Push back on overload: "You already have 5 priorities. Which one are you dropping?"
- No fluff. Skip praise for expected work.
