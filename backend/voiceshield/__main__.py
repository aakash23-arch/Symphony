"""VoiceShield unified role entrypoint dispatcher (§3.2).

Usage:
    python -m voiceshield api
    python -m voiceshield analysis-worker
    python -m voiceshield decision-worker
    python -m voiceshield all-in-one
"""

import sys
import uvicorn
from voiceshield.config import settings, AppRole
from voiceshield.obs.logging import get_logger, setup_logging


def main() -> None:
    role_arg = sys.argv[1] if len(sys.argv) > 1 else settings.role.value
    valid_roles = [r.value for r in AppRole]

    if role_arg not in valid_roles:
        print(f"Error: Invalid role '{role_arg}'. Must be one of: {', '.join(valid_roles)}")
        sys.exit(1)

    logger = setup_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        role=role_arg,
    )
    logger.info(f"Starting VoiceShield process in role: {role_arg}")

    if role_arg in [AppRole.API.value, AppRole.ALL_IN_ONE.value]:
        uvicorn.run(
            "voiceshield.api.app:app",
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            log_level=settings.log_level.lower(),
        )
    elif role_arg == AppRole.ANALYSIS_WORKER.value:
        logger.info("Analysis worker process initialized. Waiting for task loop implementation.")
        # Worker loop will be implemented in subsequent phases
    elif role_arg == AppRole.DECISION_WORKER.value:
        logger.info("Decision worker process initialized. Waiting for task loop implementation.")
        # Worker loop will be implemented in subsequent phases


if __name__ == "__main__":
    main()
