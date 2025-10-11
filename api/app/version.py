from pathlib import Path
import os

def get_version(default: str = "0.0.0-dev") -> str:
    # Prefer an explicit env var if present (useful in CI/CD)
    if v := os.getenv("APP_VERSION"):
        return v

    # Fallback to a VERSION file baked into the image
    candidates = [
        Path("/app/VERSION"),                                 # inside container
        Path(__file__).resolve().parents[1] / "VERSION",      # api/VERSION if present
        Path(__file__).resolve().parents[2] / "VERSION",      # repo root if built from root
    ]
    for p in candidates:
        try:
            return p.read_text().strip()
        except Exception:
            continue
    return default