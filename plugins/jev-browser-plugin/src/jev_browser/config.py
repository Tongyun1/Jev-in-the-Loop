import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "jev-1.13.0"
    timeout_seconds: float = 25.0
    configuration_error: bool = False

    @classmethod
    def load(cls):
        # Never search cwd/parents for .env; the installed plugin runs in arbitrary tasks.
        values = {}
        error = False
        env_file = os.environ.get("JEV_ENV_FILE", "").strip()
        if not env_file:
            default_file = Path.home() / ".config/jev-browser/config.env"
            if default_file.is_file():
                env_file = str(default_file)
        if env_file:
            try:
                path = Path(env_file).expanduser()
                if not path.is_absolute() or not path.is_file():
                    raise ValueError("Explicit absolute env file required")
                values = dotenv_values(path, interpolate=False)
            except (OSError, ValueError, UnicodeError):
                error = True
        key = os.environ.get("TYPESAFE_API_KEY", "").strip()
        key = key or (values.get("TYPESAFE_API_KEY") or "").strip()
        model = os.environ.get("TYPESAFE_MODEL", "").strip()
        model = model or (values.get("TYPESAFE_MODEL") or "").strip() or "jev-1.13.0"
        return cls(api_key=key, model=model, configuration_error=error and not bool(key))
