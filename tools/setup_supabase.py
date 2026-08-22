"""Print the feedback table DDL, and verify connectivity with a test insert.

    python tools/setup_supabase.py            # show SQL to run in the Supabase editor
    python tools/setup_supabase.py --test     # attempt a real insert, then report
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from rag.feedback import SCHEMA_SQL, is_configured, submit


def main() -> None:
    print(f"configured: {is_configured()}")

    if "--test" not in sys.argv:
        print("\nRun this in the Supabase SQL editor, then re-run with --test:\n")
        print(SCHEMA_SQL)
        return

    ok, err = submit(
        session_id=str(uuid.uuid4()),
        question="[connectivity test] please ignore",
        answer="test",
        rating=1,
        comment="inserted by tools/setup_supabase.py",
        citations=[{"citation": "test", "doc_id": "test"}],
        retrieval={"mode": "test"},
    )
    print(f"insert ok : {ok}")
    if err:
        print(f"error     : {err}")
        print("\nIf this is a 404, the table does not exist yet - run the SQL above.")
        print("If this is a 401/403, check SUPABASE_ANON_KEY and the RLS insert policy.")


if __name__ == "__main__":
    main()
