from __future__ import annotations

import json
import os
from uuid import UUID

from app.db.session import SessionLocal
from app.services.release_bootstrap import seed_release_runtime_data


def _is_enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _parse_controller_user_id(value: str | None) -> UUID:
    if not value:
        raise ValueError("CONTROLLER_API_AUTH_TOKEN is required when RELEASE_BOOTSTRAP_DATA is enabled.")
    token = value.strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    return UUID(token)


def main() -> int:
    if not _is_enabled(os.getenv("RELEASE_BOOTSTRAP_DATA")):
        print("Release bootstrap skipped because RELEASE_BOOTSTRAP_DATA is not enabled.")
        return 0

    controller_user_id = _parse_controller_user_id(os.getenv("CONTROLLER_API_AUTH_TOKEN"))
    with SessionLocal() as session:
        manifest = seed_release_runtime_data(session, controller_user_id=controller_user_id)
    print(json.dumps({"status": "bootstrapped", "manifest": manifest}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
