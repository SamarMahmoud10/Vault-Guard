import os

import requests

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


def _format_violation(v: dict) -> str:
    if v["source"] == "hadolint":
        return f"**hadolint** (line {v.get('line')}) — `{v.get('code')}`: {v.get('message')}"
    return f"**trivy** — {v.get('vulnerability_id')} in `{v.get('package')}` ({v.get('severity')})"


def send_failure_alert(repo_name: str, commit_sha: str, violations: list):
    if not DISCORD_WEBHOOK_URL:
        return

    lines = [_format_violation(v) for v in violations[:15]]

    payload = {
        "embeds": [
            {
                "title": f"❌ Vault-Guard: Scan Failed — {repo_name}",
                "description": f"Commit: `{commit_sha[:8]}`\n\n" + "\n".join(lines),
                "color": 15158332,
            }
        ]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
    except requests.RequestException:
        pass