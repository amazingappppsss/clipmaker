"""Startup self-check: `python -m clipmaker.preflight`.

Run by start-single-node.sh before anything else. Prints a plain-English checklist so a
misconfigured deployment says exactly what to fix (instead of a long stack trace), then exits
non-zero on a blocking problem. Never prints secret values.
"""

from __future__ import annotations

import sys
from pathlib import Path

OK, WARN, FAIL = "  [OK]  ", "  [WARN]", "  [FAIL]"


def main() -> int:
    print("Clip2Easy startup check")
    problems = 0

    try:
        from pydantic import ValidationError

        from clipmaker.core.config import get_settings

        settings = get_settings()
        print(f"{OK} settings loaded (APP_ENV={settings.app_env.value})")
    except ValidationError as exc:
        for err in exc.errors():
            field = ".".join(str(p) for p in err.get("loc", ())).upper() or "SETTINGS"
            print(f"{FAIL} {field}: {err.get('msg')}")
        print("Fix the variables above in your hosting dashboard, then redeploy.")
        return 1

    # Database
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"{OK} database reachable")
    except Exception as exc:  # report any connection failure plainly
        problems += 1
        host = settings.database_url.split("@")[-1].split("/")[0]
        print(f"{FAIL} database not reachable at {host}: {type(exc).__name__}")
        print("        Set DATABASE_URL to ${{Postgres.DATABASE_URL}} (your Postgres service).")

    # Redis
    try:
        import redis

        redis.Redis.from_url(settings.redis_url, socket_timeout=3).ping()
        print(f"{OK} redis reachable")
    except Exception as exc:
        problems += 1
        print(f"{FAIL} redis not reachable: {type(exc).__name__}")
        print("        Set REDIS_URL to ${{Redis.REDIS_URL}} (your Redis service).")

    # Storage
    if settings.storage_backend.value == "local":
        for label, raw in (("storage", settings.local_storage_dir), ("work", settings.work_dir)):
            path = Path(raw)
            try:
                path.mkdir(parents=True, exist_ok=True)
                probe = path / ".write-test"
                probe.write_text("ok")
                probe.unlink()
                print(f"{OK} {label} folder writable ({path})")
            except OSError as exc:
                problems += 1
                print(f"{FAIL} {label} folder {path} not writable: {exc.strerror}")
                print("        Attach a volume mounted at /data and set RAILWAY_RUN_UID=0.")

    # API keys (missing keys don't stop the server, but processing will fail)
    for name, value in (
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
        ("ASSEMBLYAI_API_KEY", settings.assemblyai_api_key),
    ):
        if value and value.get_secret_value():
            print(f"{OK} {name} is set")
        else:
            print(f"{WARN} {name} is missing: video processing will fail until it is set")

    if settings.app_env.value == "production" and not settings.supabase_url:
        print(
            f"{WARN} SUPABASE_URL is not set: sign-ins with Supabase signing keys will be refused"
        )
    if settings.app_env.value == "production":
        print(f"{OK} Upload links use the address the browser calls")

    if problems:
        print(f"{problems} blocking problem(s). Fix them and redeploy.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
