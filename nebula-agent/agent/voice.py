"""Local text-to-speech via pyttsx3 (optional).

Used by the CLI when `--voice` is on. The web UI has its own browser-side
TTS (SpeechSynthesis) and doesn't need this module.
"""
from __future__ import annotations


class Speaker:
    def __init__(self, rate: int = 190) -> None:
        try:
            import pyttsx3  # type: ignore
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", rate)
            self.available = True
        except Exception:
            self._engine = None
            self.available = False

    def say(self, text: str) -> None:
        if not self.available or not text.strip():
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass

    def stop(self) -> None:
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
