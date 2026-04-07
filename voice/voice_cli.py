from core.llm import LLM
from core.rag import RAG
from core.router import Router
from voice.stt import STT
from voice.tts import TTS
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

print("Starting Enosym voice mode...")

llm = LLM()
rag = RAG()
router = Router(llm)
stt = STT()
tts = TTS()

# index files
for folder in config["paths"]["watched_folders"]:
    rag.index_folder(folder)

tts.speak("Enosym ready. Press Enter to speak, or type your message.")

while True:
    try:
        print("\n[press Enter to speak, or type message + Enter]")
        user_input = input().strip()

        if user_input.lower() == "exit":
            tts.speak("Goodbye.")
            break

        if not user_input:
            # user pressed enter without typing — use voice
            print("Listening...")
            user_input = stt.listen()
            if not user_input:
                continue
            print(f"you: {user_input}")

        context = rag.query(user_input)
        response = router.run(user_input, context=context)

        print(f"enosym: {response}")
        tts.speak(response)

    except KeyboardInterrupt:
        tts.speak("Goodbye.")
        break