"""Email the LBJ video to yourself via your AgentMail setup in /srv/agents/core.

Run it yourself:  uv run claude_vids/send_video.py   (from ~/code-videos)
It reads the API key from /srv/agents/core/.env and never prints it.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request

ENV_FILE = "/srv/agents/core/.env"
HERE = os.path.dirname(os.path.abspath(__file__))
VIDEO = os.path.join(HERE, "lbj_all_the_way_small.mp4")
TO = "hellojonathankeogh@gmail.com"
API = "https://api.agentmail.to/v0"


def load_env(path):
    env = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    return env


def call(method, path, key, body=None):
    req = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"AgentMail API error {e.code} on {method} {path}: {e.read().decode()[:500]}")


env = load_env(ENV_FILE)
key_names = [k for k in env if "AGENTMAIL" in k.upper() and "KEY" in k.upper()]
if not key_names:
    sys.exit(f"No AGENTMAIL...KEY variable found in {ENV_FILE}. Variables present: {', '.join(env)}")
key = env[key_names[0]]
print(f"Using API key from {key_names[0]}")

inbox_names = [k for k in env if "INBOX" in k.upper()]
if inbox_names:
    inbox = env[inbox_names[0]]
    print(f"Using inbox from {inbox_names[0]}: {inbox}")
else:
    inboxes = call("GET", "/inboxes", key).get("inboxes", [])
    if not inboxes:
        sys.exit("No AgentMail inboxes found on this account.")
    inbox = inboxes[0]["inbox_id"]
    print(f"Using first inbox on the account: {inbox}")

size_mb = os.path.getsize(VIDEO) / 1e6
print(f"Attaching {os.path.basename(VIDEO)} ({size_mb:.1f} MB)...")
content = base64.b64encode(open(VIDEO, "rb").read()).decode()

result = call(
    "POST",
    f"/inboxes/{inbox}/messages/send",
    key,
    {
        "to": [TO],
        "subject": "L-B-J (All the Way) — Clawd's LBJ music video",
        "text": (
            "Howdy! Here's the video: Clawd raps and sings through Lyndon B. Johnson's presidency "
            "(1963–1969), built with HyperFrames.\n\n"
            "Full-quality 1080p version: " + os.path.join(HERE, "lbj_all_the_way.mp4")
        ),
        "attachments": [
            {"filename": "lbj_all_the_way.mp4", "content_type": "video/mp4", "content": content}
        ],
    },
)
print("Sent!", json.dumps(result)[:300])
