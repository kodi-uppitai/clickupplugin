# Reference: ClickUp Integration

> ClickUp is the team task management system for Uppit AI. This reference covers how to query, update, and interpret tasks programmatically.

---

## Central Repository

- **Space:** Operations (ID: `901311761647`)
- **List:** Weekly Commitment (ID: see `config.json → workspace.central_list_id`)

This list contains tasks for the **entire team**. Single source of truth for weekly commitments.

---

## Statuses

| Status | Type | Meaning |
|--------|------|---------|
| **to do** | Open | Backlog — not committed for this week |
| **in progress** | Custom | **Weekly commitment** — committed for this week |
| **for review** | Custom | Done but needs review/approval |
| **complete** | Closed | Done and verified |

**Key rule:** "In Progress" = committed for the week.

---

## Workspace Structure

- **Workspace:** Uppit AI (Team ID: see `config.json → workspace.team_id`)
- **User IDs:** see `config.json → user.clickup_user_id` for the current user

### Key Spaces and Lists

| Space | List | ID | Notes |
|-------|------|----|-------|
| Operations | Weekly Commitment | `901324006043` | Central task repo |
| Operations | Business Ops | `901322270433` | General business ops |
| Operations | High Ticket | `901322420808` | High ticket ops |
| Marketing | Weekly Email Newsletter | `901317048477` | Newsletter tasks |
| Marketing | Google ads | `901317043550` | Ad campaigns |
| Content Team | Your First AI Agent | `901323992928` | YFAI course tasks |
| High Ticket | Business Curriculum | `901323312493` | HTA course content |

---

## API Access

- **Base URL:** `https://api.clickup.com/api/v2`
- **Auth:** Header `Authorization: <key from config.json → secrets.clickup_api_key_path>`
- **Method:** Use Python `urllib` — NOT curl piping (broken on Windows)

### Loading the API key

```python
import os, json

def load_clickup_config():
    """Load config and API key for ClickUp access."""
    # Load plugin config
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
    with open(config_path) as f:
        config = json.load(f)

    # Load API key from secrets file
    key_path = os.path.expanduser(config['secrets']['clickup_api_key_path'])
    with open(key_path) as f:
        api_key = f.read().strip()

    return config, api_key
```

---

## Query Patterns

### Always filter by status

Unfiltered queries return 50+ tasks. Always include `statuses[]=` in the query string.

### Get weekly commitments (in progress)

```python
import urllib.request, json

config, API_KEY = load_clickup_config()
TEAM_ID = config['workspace']['team_id']
USER_ID = config['user']['clickup_user_id']

url = f'https://api.clickup.com/api/v2/team/{TEAM_ID}/task?statuses[]=in+progress&assignees[]={USER_ID}&subtasks=true&include_closed=false'
req = urllib.request.Request(url, headers={'Authorization': API_KEY})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
for t in data['tasks']:
    print(f'{t["id"]} | {t["name"]}')
```

### Update a task's status

```python
task_id = '86af1kjjn'
body = json.dumps({'status': 'in progress'}).encode()
req = urllib.request.Request(
    f'https://api.clickup.com/api/v2/task/{task_id}',
    data=body, method='PUT',
    headers={'Authorization': API_KEY, 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f'{result["name"]}: -> {result["status"]["status"]}')
```

### Common query filters

| Filter | Example | Notes |
|--------|---------|-------|
| By assignee | `assignees[]={USER_ID}` | Current user's tasks |
| By status | `statuses[]=in+progress` | **Always use this** |
| Include subtasks | `subtasks=true` | Many tasks are nested |
| Exclude closed | `include_closed=false` | Skip completed tasks |
| By list | Use `/list/{list_id}/task` endpoint | For list-specific queries |

---

## Weekly Commitment Board Structure

The Weekly Commitment list is **OTAs only**. Every top-level task is an OTA (parent task). Every milestone is a subtask under its OTA parent.

**Rules:**
- **Only OTA parent tasks at the top level.** No loose tasks, no personal items, no admin one-offs.
- **All milestones are subtasks** nested under their OTA parent.
- **Personal tasks are NEVER on ClickUp** — those live only in Life OS (`tasks/current-week.md`).
- **Admin/one-off tasks** belong only in Life OS, not ClickUp.
- When creating new OTA tasks, create the parent first, then add milestones as subtasks.

---

## Chat / DM Check (Daily Planning)

Check ClickUp DMs for messages in the last 24 hours. Surfaces requests that came via chat rather than the task system.

### API pattern (v3)

```python
import urllib.request, json, time

config, API_KEY = load_clickup_config()
TEAM_ID = config['workspace']['team_id']
MY_USER_ID = config['user']['clickup_user_id']

# Step 1: Get all channels, filter to DMs with recent activity
url = f'https://api.clickup.com/api/v3/workspaces/{TEAM_ID}/chat/channels?limit=100'
req = urllib.request.Request(url, headers={'Authorization': API_KEY})
resp = urllib.request.urlopen(req)
channels = json.loads(resp.read())['data']

cutoff = (time.time() - 86400) * 1000  # 24h ago in ms
recent_dms = [c for c in channels if c.get('type') == 'DM' and c.get('latest_comment_at', 0) > cutoff]

# Step 2: For each recent DM, get members and messages
for dm in recent_dms:
    mem_url = f'https://api.clickup.com/api/v3/workspaces/{TEAM_ID}/chat/channels/{dm["id"]}/members'
    mem_req = urllib.request.Request(mem_url, headers={'Authorization': API_KEY})
    members = json.loads(urllib.request.urlopen(mem_req).read())['data']
    other = [m for m in members if m['id'] != MY_USER_ID]

    msg_url = f'https://api.clickup.com/api/v3/workspaces/{TEAM_ID}/chat/channels/{dm["id"]}/messages?limit=50'
    msg_req = urllib.request.Request(msg_url, headers={'Authorization': API_KEY})
    messages = json.loads(urllib.request.urlopen(msg_req).read())['data']

    recent_from_others = [m for m in messages if m['date'] > cutoff and m['user_id'] != MY_USER_ID]
```

### Output format

- "**[Name]** — [N] messages in the last 24h"
- Numbered list of action items / requests / questions
- If no action items, say so briefly

---

## Gotchas

- **Never use curl piping on Windows** — stdout buffering breaks JSON parsing. Always use Python `urllib`.
- **Never query without a status filter** — unfiltered returns 50+ tasks.
- **Task IDs are alphanumeric strings**, not integers (e.g., `86af1kjjn`).
- **Recurring event IDs** differ from single-instance IDs. Always use the specific instance ID.
- **Never add urgent/priority tags to task names** — use the priority field instead (1=urgent, 2=high, 3=normal, 4=low).
- **Python path on Windows:** use the full path to python.exe if `python3` is not on PATH.
