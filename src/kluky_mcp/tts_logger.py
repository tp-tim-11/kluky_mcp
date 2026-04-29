"""TTS logger — zapisuje udalosti do kluky.log."""

from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path(__file__).parent.parent.parent / "logs" / "kluky.log"


def log(typ: str, text: str) -> None:
    """Zapíše jeden riadok: Timestamp | TYP | text."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{ts} | {typ} | {text}\n")
