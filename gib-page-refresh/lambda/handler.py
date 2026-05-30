"""Daily Gib page refresh → GitLab commit on davidduncan.org.

Triggered by EventBridge Scheduler each morning. Reads three TELOS data
files from S3 (synced via the existing PAI backup pipeline), regenerates
three marked sections of content/pages/gib.md, and commits the updated
file to the GitLab repo via the Files API. GitLab CI takes over from
there and runs the existing pelican deploy job.

Marked sections in gib.md:
    <!-- gib:state:start -->     ... State bullets ...     <!-- gib:state:end -->
    <!-- gib:projects:start -->  ... Active Projects ...   <!-- gib:projects:end -->
    <!-- gib:updates:start -->   ... Recent Updates ...    <!-- gib:updates:end -->

Static sections (Mission, Current Focus, Goals, Learning, Daily Habits,
TELOS) are left untouched.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

LOG = logging.getLogger()
LOG.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITLAB_TOKEN = os.environ["GITLAB_TOKEN"]
GITLAB_HOST = os.environ.get("GITLAB_HOST", "gitlab.com")
GITLAB_PROJECT_PATH = os.environ["GITLAB_PROJECT_PATH"]  # e.g. rubackedup-com/davidduncan.org
GITLAB_BRANCH = os.environ.get("GITLAB_BRANCH", "main")
GIB_PAGE_PATH = os.environ.get("GIB_PAGE_PATH", "content/pages/gib.md")

S3_BUCKET = os.environ["S3_BUCKET"]
S3_TELOS_PREFIX = os.environ.get("S3_TELOS_PREFIX", "claude/PAI/USER/TELOS/")

GITLAB_PROJECT_ID = urllib.parse.quote(GITLAB_PROJECT_PATH, safe="")


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------


def http_request(method: str, url: str, *, headers: dict | None = None, body: bytes | None = None,
                 timeout: int = 15) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, data=body, method=method,
                                  headers={"User-Agent": "pai-gib-page-refresh/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        LOG.warning("HTTP %s %s → %s: %s", method, url, exc.code, raw[:300])
        return exc.code, raw


# ---------------------------------------------------------------------------
# S3 read (using IAM role via SigV4 — handled by boto3)
# ---------------------------------------------------------------------------


def s3_get_text(key: str) -> str:
    """Return UTF-8 text of an S3 object."""
    import boto3  # lazy import — boto3 ships with the python runtime
    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=S3_BUCKET, Key=key)
    return obj["Body"].read().decode("utf-8")


# ---------------------------------------------------------------------------
# Section generators — parse TELOS files into rendered markdown
# ---------------------------------------------------------------------------


def render_state() -> str:
    """Return the State bullets from STATE.md."""
    raw = s3_get_text(f"{S3_TELOS_PREFIX}STATE.md")
    fields = {}
    for line in raw.splitlines():
        m = re.match(r"^\s*-\s*\*\*([^:*]+):\*\*\s*(.+)$", line)
        if m:
            fields[m.group(1).strip()] = m.group(2).strip()

    parts = []
    for label in ("Energy", "Mode", "Location"):
        val = fields.get(label, "—")
        parts.append(f"- **{label}:** {val}")
    return "\n".join(parts)


def render_projects() -> str:
    """Return the Active Projects markdown table from PROJECTS_STATUS.md."""
    raw = s3_get_text(f"{S3_TELOS_PREFIX}PROJECTS_STATUS.md")
    rows: list[tuple[str, str, str, str]] = []
    # Allowed statuses — anything else is treated as a format-doc line and skipped.
    valid_statuses = {"active", "planning", "paused", "done", "archived"}
    for line in raw.splitlines():
        # Format: - **Name** | status | (http(s)://...|none) | description
        m = re.match(
            r"^\s*-\s*\*\*([^*]+)\*\*\s*\|\s*(\S+)\s*\|\s*(https?://\S+|none)\s*\|\s*(.+)$",
            line,
        )
        if not m:
            continue
        name, status, url, desc = (g.strip() for g in m.groups())
        if status not in valid_statuses:
            continue
        rows.append((name, status, url, desc))

    lines = ["| Project | Status | Description |", "|---|---|---|"]
    for name, status, url, desc in rows:
        cell_name = f"**[{name}]({url})**" if url != "none" else f"**{name}**"
        lines.append(f"| {cell_name} | {status} | {desc} |")
    return "\n".join(lines)


def render_updates(limit: int = 7) -> str:
    """Return the last N changelog descriptions from Updates.md, newest first."""
    raw = s3_get_text(f"{S3_TELOS_PREFIX}Updates.md")
    # Each entry block starts with "## <timestamp>" and includes a
    # "- **Description**: ..." line. Pull description lines in source order.
    descriptions: list[str] = []
    current_desc = None
    for line in raw.splitlines():
        if line.startswith("## "):
            current_desc = None  # new block
        m = re.match(r"^\s*-\s*\*\*Description\*\*:\s*(.+)$", line)
        if m:
            current_desc = m.group(1).strip()
            descriptions.append(current_desc)

    # Newest first; Updates.md appends to end, so reverse-slice the tail.
    recent = list(reversed(descriptions[-limit:]))
    return "\n".join(f"- {d}" for d in recent) or "- (no recent changelog entries available)"


# ---------------------------------------------------------------------------
# Marker-based substitution
# ---------------------------------------------------------------------------


MARKER_PATTERN = re.compile(
    r"(<!--\s*gib:(?P<name>[a-z]+):start\s*-->\n)"
    r"(.*?)"
    r"(\n<!--\s*gib:(?P=name):end\s*-->)",
    re.DOTALL,
)


@dataclass
class SectionUpdate:
    name: str       # marker name (state | projects | updates)
    content: str    # rendered markdown to insert between markers


def apply_updates(markdown: str, updates: list[SectionUpdate]) -> str:
    by_name = {u.name: u.content for u in updates}

    def repl(m: re.Match[str]) -> str:
        name = m.group("name")
        if name not in by_name:
            return m.group(0)
        return m.group(1) + by_name[name] + m.group(4)

    return MARKER_PATTERN.sub(repl, markdown)


# ---------------------------------------------------------------------------
# GitLab Files API
# ---------------------------------------------------------------------------


def gitlab_get_file() -> tuple[str, str]:
    """Return (content, last_commit_id) of the gib.md file on the branch."""
    path = urllib.parse.quote(GIB_PAGE_PATH, safe="")
    url = (f"https://{GITLAB_HOST}/api/v4/projects/{GITLAB_PROJECT_ID}/repository/files/"
           f"{path}?ref={GITLAB_BRANCH}")
    status, body = http_request("GET", url, headers={"PRIVATE-TOKEN": GITLAB_TOKEN})
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"GET file failed: {status} {str(body)[:200]}")
    content = base64.b64decode(body["content"]).decode("utf-8")
    return content, body.get("last_commit_id", "")


def gitlab_put_file(new_content: str, commit_message: str) -> dict:
    path = urllib.parse.quote(GIB_PAGE_PATH, safe="")
    url = (f"https://{GITLAB_HOST}/api/v4/projects/{GITLAB_PROJECT_ID}/repository/files/{path}")
    payload = json.dumps({
        "branch": GITLAB_BRANCH,
        "content": new_content,
        "commit_message": commit_message,
        "author_email": "gib-page-refresh@bot.davidduncan.org",
        "author_name": "gib-page-refresh (bot)",
    }).encode("utf-8")
    status, body = http_request("PUT", url,
                                 headers={"PRIVATE-TOKEN": GITLAB_TOKEN,
                                          "Content-Type": "application/json"},
                                 body=payload)
    if status not in (200, 201):
        raise RuntimeError(f"PUT file failed: {status} {str(body)[:300]}")
    return body if isinstance(body, dict) else {"raw": body}


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------


def handler(event, context):
    LOG.info("gib-page-refresh starting; event=%s", json.dumps(event or {})[:200])

    # Render the three dynamic sections from TELOS data in S3
    sections = [
        SectionUpdate("state", render_state()),
        SectionUpdate("projects", render_projects()),
        SectionUpdate("updates", render_updates(limit=7)),
    ]
    LOG.info("rendered sections: state=%d, projects=%d, updates=%d",
             len(sections[0].content), len(sections[1].content), len(sections[2].content))

    # Pull current gib.md from GitLab, apply substitutions
    current_md, _ = gitlab_get_file()
    new_md = apply_updates(current_md, sections)

    if new_md == current_md:
        LOG.info("no changes detected; skipping commit")
        return {"ok": True, "changed": False}

    # Commit + push back via Files API
    today = re.sub(r"[^\d-]", "", os.environ.get("AWS_LAMBDA_LOG_STREAM_NAME", "")[:10])
    msg = f"Daily gib page refresh ({today or 'auto'})"
    result = gitlab_put_file(new_md, msg)
    LOG.info("committed; file_path=%s branch=%s", result.get("file_path"), result.get("branch"))

    return {
        "ok": True,
        "changed": True,
        "commit_message": msg,
        "file_path": result.get("file_path"),
        "branch": result.get("branch"),
    }
