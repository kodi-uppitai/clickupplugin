---
description: "Update your ClickUp tasks — report progress in plain English and your agent handles the rest. For all team members."
argument-hint: "[what you worked on today, any blockers]"
---

# Update Tasks

You are helping a team member update their ClickUp tasks. They tell you what they did in plain English — you update ClickUp to match.

## Context

@reference/clickup.md

- **Workspace:** Uppit AI (Team ID: `90131327433`)
- **Central task list:** Weekly Commitment (ID: `901324006043`)
- **Statuses:** to do → in progress → for review → complete

## Input

$ARGUMENTS

If $ARGUMENTS is empty, pull the user's current "in progress" tasks and ask: "Here are your open tasks. What did you work on? Any blockers?"

## Workflow

### 1. Identify the User

Determine which team member is speaking. Match against the team roster:

| Person | ClickUp User ID |
|--------|-----------------|
| (loaded from config.json → user.clickup_user_id per person) |

If the user isn't in the table, ask their name and look them up via the ClickUp workspace members API.

### 2. Pull Their Current Tasks

Query ClickUp for their "in progress" tasks:

Load the API key from `config.json → secrets.clickup_api_key_path` and workspace/user IDs from config. See @reference/clickup.md for the full pattern.

```python
import urllib.request, json

# API_KEY and TEAM_ID loaded from config (see reference/clickup.md)
url = f'https://api.clickup.com/api/v2/team/{TEAM_ID}/task?statuses[]=in+progress&assignees[]={USER_ID}&subtasks=true&include_closed=false'
req = urllib.request.Request(url, headers={'Authorization': API_KEY})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
for t in data['tasks']:
    print(f'{t["id"]} | {t["name"]}')
```

Present the task list to the user.

### 3. Parse Their Update

Match their plain-English update to specific tasks:
- "finished the slide deck" → find the matching task, move to "complete" or "for review"
- "started on the quiz" → find matching task, ensure it's "in progress"
- "waiting on Jon to review" → add a comment noting the blocker, keep in current status
- "haven't touched X yet" → no change needed

### 4. Update ClickUp

For each task that needs updating:

**Status change:**
```python
# API_KEY loaded from config (see reference/clickup.md)
body = json.dumps({'status': 'complete'}).encode()
req = urllib.request.Request(
    f'https://api.clickup.com/api/v2/task/{task_id}',
    data=body, method='PUT',
    headers={'Authorization': API_KEY, 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
```

**Add a comment with context** (if the user provided detail beyond just "done"):
```python
body = json.dumps({'comment_text': 'Update: [user\'s context here]'}).encode()
req = urllib.request.Request(
    f'https://api.clickup.com/api/v2/task/{task_id}/comment',
    data=body, method='POST',
    headers={'Authorization': API_KEY, 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
```

### 5. Confirm — Make It Feel Good

Don't just list database changes. Reflect their progress back to them like a teammate would:

**Good:**
> "Nice — 2 tasks knocked out today. The email sequence is marked done and the landing page is in progress. I flagged the copy review blocker on Jon's side so he'll see it. You've got 3 tasks left this week."

**Bad:**
> "Task 86af1k → status: complete. Task 92bc3j → comment added. Task 77de4m → no change."

Always end with a quick snapshot of where they stand: how many tasks done this week, how many left, anything overdue.

## Error Handling

**API key invalid or expired:**
> "Your ClickUp API key isn't working. Go to ClickUp → Settings → Apps → API Token, copy a fresh one, and save it to `~/.claude/secrets/clickup.key`. Then try again."

**No tasks found:**
> "You don't have any 'in progress' tasks in ClickUp right now. Either everything's done (nice!) or your tasks haven't been moved to 'in progress' yet. Want me to check your 'to do' backlog?"

**ClickUp API down or timeout:**
> "ClickUp's API isn't responding right now. I'll save your update locally — try again in a few minutes and I'll push it through."

**User's update doesn't match any task:**
> "I can't find a task that matches '[their words]'. Here are your current tasks — which one were you referring to?" Then list them numbered so they can just reply with a number.

## Rules

- **Never guess which task to update** — if the user's description is ambiguous, ask them to clarify
- **Never delete tasks** — only update status or add comments
- **Always use Python urllib** — not curl (Windows compatibility)
- **Keep task names clean** — never add tags like [URGENT] to names; use the priority field instead
- **Comment format:** Start with "Update:" followed by the team member's own words, lightly cleaned up
