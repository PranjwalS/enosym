from faster_whisper import WhisperModel
import sounddevice as sd
import numpy as np
import tempfile
import soundfile as sf

class STT:
    def __init__(self, model_size="base.en"):
        # base.en is ~150MB, fast on CPU, English only
        # use "small.en" (~500MB) for better accuracy if you want
        print("Loading Whisper...")
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self.sample_rate = 16000

    def record(self, duration: int = 5) -> np.ndarray:
        """Record audio for a fixed duration."""
        print(f"Recording for {duration}s...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32"
        )
        sd.wait()
        return audio.flatten()

    def record_until_silence(self, silence_threshold=0.01, min_duration=1, max_duration=30) -> np.ndarray:
        """Record until the user stops talking."""
        chunks = []
        silent_chunks = 0
        chunk_duration = 0.5  # seconds per chunk
        chunk_samples = int(self.sample_rate * chunk_duration)
        total_duration = 0

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            while total_duration < max_duration:
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                chunks.append(chunk)
                total_duration += chunk_duration

                rms = np.sqrt(np.mean(chunk**2))
                if rms < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0

                # stop after 1.5s of silence, minimum 1s recorded
                if silent_chunks >= 3 and total_duration >= min_duration:
                    break

        return np.concatenate(chunks)

    def transcribe(self, audio: np.ndarray) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, self.sample_rate)
            segments, _ = self.model.transcribe(f.name, language="en", vad_filter=True)
            return " ".join(s.text for s in segments).strip()

    def listen(self) -> str:
        """Record until silence then transcribe. Returns text."""
        audio = self.record_until_silence()
        return self.transcribe(audio)