import pvporcupine
import sounddevice as sd
import numpy as np

class WakeWord:
    def __init__(self, access_key: str, keyword="hey enosym"):
        # Get a free access key at picovoice.com — needed for Porcupine
        # Free tier allows local usage
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["hey siri"]  # use built-in keyword as placeholder
            # for custom "hey enosym" you need a paid Picovoice account
            # alternatively use "computer" or "jarvis" from the free built-ins
        )
        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length

    def wait_for_wake_word(self):
        """Block until wake word is detected."""
        print("Listening for wake word...")
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_length
        ) as stream:
            while True:
                data, _ = stream.read(self.frame_length)
                pcm = data.flatten().tolist()
                result = self.porcupine.process(pcm)
                if result >= 0:
                    print("Wake word detected!")
                    return

    def __del__(self):
        if hasattr(self, 'porcupine'):
            self.porcupine.delete()