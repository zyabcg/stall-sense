"""
Scrub personal details out of Entire's session checkpoints before they are
pushed to the public repo.

Entire stores each agent session as a git ref under refs/entire/. This
rewrites every such ref with personal email addresses (and any extra terms
listed in .env as REDACT_TERMS, comma separated) replaced by [redacted],
then verifies nothing is left.

Run before pushing:  uv run python scripts/redact_checkpoints.py
"""

import os
import re
import subprocess
import tempfile

from dotenv import load_dotenv

load_dotenv()
EXTRA = [t.strip() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
# Any email address, except harmless public no-reply / org addresses.
EMAIL = re.compile(rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KEEP = (b"users.noreply.github.com", b"noreply@anthropic.com", b"mlh.io", b"priorlabs.ai")


def git(*args, input=None, env=None) -> bytes:
    return subprocess.run(["git", *args], input=input, env=env, check=True,
                          capture_output=True).stdout


def scrub(data: bytes) -> bytes:
    data = EMAIL.sub(lambda m: m.group(0) if m.group(0).endswith(KEEP) else b"[redacted]", data)
    for term in EXTRA:
        data = data.replace(term.encode(), b"[redacted]")
    return data


def dirty(data: bytes) -> bool:
    return scrub(data) != data


refs = git("for-each-ref", "refs/entire", "--format=%(refname)").decode().split()
changed = 0
for ref in refs:
    files = [line.split(b"\t") for line in git("ls-tree", "-r", ref).splitlines()]
    blobs = {path: meta.split()[2] for meta, path in files}
    if not any(dirty(git("cat-file", "blob", sha)) for sha in blobs.values()):
        continue
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
        git("read-tree", ref, env=env)
        for path, sha in blobs.items():
            data = git("cat-file", "blob", sha)
            if dirty(data):
                new_sha = git("hash-object", "-w", "--stdin", input=scrub(data)).strip()
                git("update-index", "--cacheinfo", f"100644,{new_sha.decode()},{path.decode()}", env=env)
        tree = git("write-tree", env=env).strip().decode()
    # Keep the original author, dates and message; only the content changes.
    fmt = git("log", "-1", "--format=%an%x00%ae%x00%aD%x00%cn%x00%ce%x00%cD", ref).decode().strip().split("\0")
    msg = git("log", "-1", "--format=%B", ref)
    env = {**os.environ, "GIT_AUTHOR_NAME": fmt[0], "GIT_AUTHOR_EMAIL": fmt[1], "GIT_AUTHOR_DATE": fmt[2],
           "GIT_COMMITTER_NAME": fmt[3], "GIT_COMMITTER_EMAIL": fmt[4], "GIT_COMMITTER_DATE": fmt[5]}
    commit = git("commit-tree", tree, input=msg, env=env).strip().decode()
    git("update-ref", ref, commit)
    changed += 1

# Verify: nothing personal left in any checkpoint.
left = sum(dirty(git("cat-file", "blob", meta.split()[2]))
           for ref in refs for meta, _ in (l.split(b"\t") for l in git("ls-tree", "-r", ref).splitlines()))
print(f"{len(refs)} checkpoints, {changed} rewritten, {left} files still containing personal data")
raise SystemExit(1 if left else 0)
