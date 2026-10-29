"""One-shot private synthetic cohort bootstrap; no credentials in shared output."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from time import time

from taximobile_api.core.config import Settings
from taximobile_api.operations.alpha_seed_target import AlphaSeedRefused, RailwayAlphaTarget
from taximobile_api.operations.ux_demo_seed import DemoProfile, seed_demo


async def enroll_alpha_mfa(settings, target: RailwayAlphaTarget, secret: str, recovery_codes: list[str]) -> None:
    from taximobile_api.cli.enroll_operations_mfa import preflight, persist_enrollment
    from taximobile_api.domains.administration.operations_mfa import totp_code, normalize_recovery_code

    if (not re.fullmatch(r"[A-Z2-7]{32}", secret) or len(recovery_codes) != 10
            or len(set(recovery_codes)) != 10
            or any(not re.fullmatch(r"[23456789ABCDEFGHJKLMNPQRSTUVWXYZ]{20}", normalize_recovery_code(code))
                   for code in recovery_codes)):
        raise AlphaSeedRefused("Private TOTP and ten distinct recovery codes are required.")
    email = f"ux-operations-{target.suffix}@example.test"
    enrollment = await preflight(settings, email, replace_existing=False)
    await persist_enrollment(settings, enrollment, secret, totp_code(secret, int(time() // 30)), recovery_codes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the named synthetic Railway alpha once.")
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--mode", choices=["cohort", "mfa"], default="cohort")
    arguments = parser.parse_args()
    target = RailwayAlphaTarget(
        project_id=os.environ.get("RAILWAY_PROJECT_ID", ""),
        environment_id=os.environ.get("RAILWAY_ENVIRONMENT_ID", ""),
        suffix=os.environ.pop("TAXIMOBILE_ALPHA_SEED_SUFFIX", ""),
        password=os.environ.pop("TAXIMOBILE_ALPHA_SEED_PASSWORD", ""),
    )
    secret = os.environ.pop("TAXIMOBILE_ALPHA_MFA_SECRET", "")
    recovery_text = os.environ.pop("TAXIMOBILE_ALPHA_MFA_RECOVERY_CODES", "[]")
    try:
        settings = Settings.from_environment()
        target.validate(environment=settings.environment, database_url=settings.database_url,
                        confirmation=arguments.confirm)
        if arguments.mode == "cohort":
            asyncio.run(seed_demo(settings, confirmation=arguments.confirm,
                                  profile=DemoProfile.UNION_LIVE, railway_target=target))
        else:
            asyncio.run(enroll_alpha_mfa(settings, target, secret, json.loads(recovery_text)))
    except Exception as error:
        # DB exception bodies can contain SQL values. Expose the error class,
        # never the password, email cohort, DSN or underlying parameter strings.
        print(f"Synthetic alpha {arguments.mode} bootstrap refused ({type(error).__name__}); "
              "verify the private target and existing cohort/factor; nothing is replaced.", file=sys.stderr)
        return 2
    print("Synthetic alpha cohort created: five accounts; union_live; no reset performed."
          if arguments.mode == "cohort" else "Synthetic alpha scoped reviewer MFA enrolled; no factor replaced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
