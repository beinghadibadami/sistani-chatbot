"""Anonymous feedback capture via Supabase REST.

Writes go through the backend rather than the browser so the key is never shipped to
clients, and so the retrieved citations can be recorded server-side. Storing the citations
alongside the rating is the whole point: "this answer was wrong" is not actionable, but
"this answer was wrong and these are the chunks that were retrieved" is.

Users are identified only by a client-generated UUID held in localStorage. No account, no
personal data.

Failures are swallowed: feedback is telemetry, and losing it must never surface as an error
in the chat.
"""

from __future__ import annotations

import json
import os
from typing import Any

TABLE = os.getenv("SUPABASE_FEEDBACK_TABLE", "feedback")
TIMEOUT = 8.0

_session = None


def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def _get_session():
    global _session
    if _session is None:
        import requests

        key = os.getenv("SUPABASE_ANON_KEY", "")
        _session = requests.Session()
        _session.headers.update(
            {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # Keeps the response body empty; nothing is read back.
                "Prefer": "return=minimal",
            }
        )
    return _session


def submit(
    *,
    session_id: str,
    question: str,
    answer: str | None,
    rating: int,
    comment: str | None = None,
    citations: list[dict[str, Any]] | None = None,
    retrieval: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    """Insert one feedback row. Returns (ok, error_message)."""
    if not is_configured():
        return False, "Supabase is not configured."

    url = os.getenv("SUPABASE_URL", "").rstrip("/") + f"/rest/v1/{TABLE}"
    payload = {
        "session_id": session_id,
        "question": question[:4000],
        "answer": (answer or "")[:20000] or None,
        "rating": 1 if rating > 0 else -1,
        "comment": (comment or "").strip()[:2000] or None,
        "citations": citations or [],
        "retrieval": retrieval or {},
    }

    try:
        resp = _get_session().post(url, data=json.dumps(payload), timeout=TIMEOUT)
        if resp.status_code >= 300:
            return False, f"supabase {resp.status_code}: {resp.text[:200]}"
        return True, None
    except Exception as exc:  # telemetry must not break the request path
        return False, f"{type(exc).__name__}: {exc}"


SCHEMA_SQL = """
-- Run once in the Supabase SQL editor.

create table if not exists public.feedback (
  id          bigserial primary key,
  created_at  timestamptz not null default now(),
  session_id  text        not null,       -- anonymous UUID from localStorage
  question    text        not null,
  answer      text,
  rating      smallint    not null check (rating in (-1, 1)),
  comment     text,
  citations   jsonb       not null default '[]'::jsonb,
  retrieval   jsonb       not null default '{}'::jsonb
);

create index if not exists feedback_created_at_idx on public.feedback (created_at desc);
create index if not exists feedback_rating_idx     on public.feedback (rating);
create index if not exists feedback_session_idx    on public.feedback (session_id);

alter table public.feedback enable row level security;

-- Insert-only for the anon role. Deliberately no select policy: the anon key must not be
-- able to read submitted feedback back out, since it is shipped in server config and could
-- otherwise expose every question users have asked.
drop policy if exists feedback_anon_insert on public.feedback;
create policy feedback_anon_insert
  on public.feedback for insert to anon
  with check (true);
"""
