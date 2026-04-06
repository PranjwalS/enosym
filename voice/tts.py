from kokoro_onnx import Kokoro
import sounddevice as sd
import numpy as np

class TTS:
    def __init__(self, voice="am_puck"):
        print("Loading Kokoro TTS...")
        self.kokoro = Kokoro("kokoro-v0_19.onnx", "voices.bin")
        self.voice = voice
        # available voices: am_puck, af_sky, am_adam, af_bella
        # am_ = American male, af_ = American female

    def speak(self, text: str, speed: float = 1.0):
        if not text.strip():
            return
        # split long text into sentences to start playing faster
        sentences = self._split_sentences(text)
        for sentence in sentences:
            if sentence.strip():
                samples, sample_rate = self.kokoro.create(
                    sentence, voice=self.voice, speed=speed, lang="en-us"
                )
                sd.play(samples, samplerate=sample_rate)
                sd.wait()

    def _split_sentences(self, text: str) -> list[str]:
        import re
        return re.split(r'(?<=[.!?])\s+', text)