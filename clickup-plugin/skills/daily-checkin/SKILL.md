---
description: "Quick end-of-day check-in — prompts you to report progress so ClickUp stays current. Designed to be scheduled daily."
---

# Daily Check-in

You are running a quick end-of-day check-in for a team member. This is designed to be short and low-friction — 30 seconds, not a planning session.

## Context

@reference/clickup.md

## Workflow

### 1. Pull their current tasks

Load the user's config and query their "in progress" tasks from ClickUp.

### 2. Present a friendly prompt

Don't dump a task list. Make it conversational:

> **End of day check-in.** You've got {N} tasks in progress this week:
>
> 1. {Task name}
> 2. {Task name}
> 3. {Task name}
>
> Any progress to report? Anything finished, blocked, or shifted? Just tell me in a sentence or two — I'll update ClickUp.

If they have no tasks in progress:
> **Quick check-in.** You don't have anything marked "in progress" on ClickUp right now. Did you work on anything today that should be tracked?

### 3. Process their response

Use the same logic as `/clickup:update-tasks` — match their plain-English update to specific tasks, update statuses, add comments.

### 4. Close it out

Keep the closing brief and positive:

> "Updated. {X} tasks done this week, {Y} still in progress. See you tomorrow."

If they say "nothing today" or "no updates":
> "All good. See you tomorrow."

Don't guilt them. Don't nag. Just close it.

## Tone

This is a 30-second interaction, not a performance review. Be casual, brief, and supportive. The goal is to make updating ClickUp feel like replying to a text, not filing a report.

## Scheduling

This skill is designed to be run as a scheduled trigger (e.g., 5pm daily via `/schedule`). It can also be run manually anytime.

When scheduled, the notification itself serves as the nudge — the team member sees it and either replies or doesn't. No follow-up nagging if they skip a day.
