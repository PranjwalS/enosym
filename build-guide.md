# Enosym — Full Build Guide

Windows-first. CPU + 32GB RAM. Free and local by default, Claude API as optional brain upgrade.
Follow this top to bottom. Each phase ends with a working thing you can actually test.

---

## Before you start — one-time setup

### Python environment
```bash
# Make sure you're on Python 3.11+ (not 3.12 yet, some audio libs are finicky)
python --version

# Create a venv for the whole project
python -m venv enosym-env
enosym-env\Scripts\activate

# You'll activate this every time you work on the project
```

### Project structure — create this now, fill it in as you go
```
enosym/
├── core/
│   ├── __init__.py
│   ├── llm.py
│   ├── rag.py
│   ├── tools.py
│   ├── memory.py
│   └── router.py
├── voice/
│   ├── __init__.py
│   ├── stt.py
│   ├── tts.py
│   └── wake.py
├── agents/
│   ├── __init__.py
│   ├── browser.py
│   ├── email_agent.py
│   ├── github_agent.py
│   └── calendar_agent.py
├── ui/
│   ├── __init__.py
│   ├── tray.py
│   └── chat_window.py
├── data/
│   ├── chroma/          # vector DB lives here
│   ├── memory.db        # SQLite memory
│   └── logs/            # activity logs
├── config/
│   ├── settings.yaml    # all config in one place
│   └── credentials/     # gitignored, API keys etc
├── cli.py               # text entry point
├── voice_cli.py         # voice entry point  
├── main.py              # full system entry point
└── requirements.txt
```

```bash
# Create it all at once
mkdir enosym && cd enosym
mkdir core voice agents ui data\chroma data\logs config\credentials
type nul > core\__init__.py voice\__init__.py agents\__init__.py ui\__init__.py
type nul > cli.py voice_cli.py main.py
```

### Install Ollama
Download from https://ollama.com — just runs as a Windows service after install.
Then pull your model:
```bash
# 7B is your sweet spot with 32GB RAM — actually smart, decent speed
ollama pull qwen2.5:7b

# Verify it's working
ollama run qwen2.5:7b "say hello in one sentence"
```

---

## Phase 1 — Core LLM loop

**What you're building:** A Python wrapper around Ollama that handles conversations, keeps context, and will serve as the brain for everything else.

**When it's done:** You can have a multi-turn conversation with it from the terminal that feels coherent.

### Install dependencies
```bash
pip install ollama pyyaml rich
```

### config/settings.yaml
```yaml
llm:
  model: "qwen2.5:7b"
  temperature: 0.7
  context_window: 8192
  system_prompt: |
    You are Enosym, a local AI lab partner running entirely on the user's machine.
    You have access to their files, projects, browser, email, and GitHub.
    You are direct, technical, and treat the user as a peer — not a customer.
    When you need to take an action, say exactly what you're going to do before doing it.
    When something is irreversible, always confirm before proceeding.

paths:
  chroma_db: "data/chroma"
  memory_db: "data/memory.db"
  logs: "data/logs"
  watched_folders:
    - "C:/Users/YOUR_USERNAME/Documents"
    - "C:/Users/YOUR_USERNAME/Desktop"
    # add your projects folder here
```

### core/llm.py
```python
import ollama
import yaml
from pathlib import Path
from datetime import datetime

def load_config():
    with open("config/settings.yaml") as f:
        return yaml.safe_load(f)

config = load_config()

class LLM:
    def __init__(self):
        self.model = config["llm"]["model"]
        self.system_prompt = config["llm"]["system_prompt"]
        self.history = []

    def chat(self, user_message: str, context: str = "") -> str:
        # inject any RAG context or tool results into the message
        full_message = user_message
        if context:
            full_message = f"Context:\n{context}\n\nUser: {user_message}"

        self.history.append({"role": "user", "content": full_message})

        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                *self.history
            ]
        )

        reply = response["message"]["content"]
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def clear_history(self):
        self.history = []

    def one_shot(self, prompt: str) -> str:
        # no history, single question — used internally by other modules
        response = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        return response["message"]["content"]
```

### cli.py
```python
from core.llm import LLM
from rich.console import Console
from rich.markdown import Markdown

console = Console()
llm = LLM()

console.print("[bold cyan]Enosym[/] — type 'exit' to quit, 'clear' to reset context\n")

while True:
    try:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "clear":
            llm.clear_history()
            console.print("[dim]context cleared[/dim]\n")
            continue

        response = llm.chat(user_input)
        console.print(Markdown(f"**enosym:** {response}\n"))

    except KeyboardInterrupt:
        break
```

**Test it:**
```bash
python cli.py
```
You should have a working multi-turn conversation. Ask it something, ask a follow-up, make sure it remembers the context.

---
...
## Phase 2 — RAG over your files

**What you're building:** Enosym can read and understand your files. Ask it "what's in my projects folder" or "what does the scoring function in JobScout do" and it actually knows.

**When it's done:** You point it at a folder and ask questions about the contents and get real answers.

### Install dependencies
```bash
pip install chromadb sentence-transformers watchdog
```

Note: sentence-transformers will download a ~90MB embedding model on first run. That's fine, it's a one-time thing.

### core/rag.py
```python
import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path
import hashlib
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

SUPPORTED_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".md", ".txt", ".yaml", ".yml", ".json", ".html", ".css", ".env.example", ".toml", ".rs", ".go", ".c", ".cpp", ".java"}

class RAG:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=config["paths"]["chroma_db"])
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"  # 90MB, fast, good enough
        )
        self.collection = self.client.get_or_create_collection(
            name="enosym_files",
            embedding_function=self.embed_fn
        )

    def index_file(self, filepath: Path) -> int:
        """Chunk and embed a single file. Returns number of chunks added."""
        if filepath.suffix not in SUPPORTED_EXTENSIONS:
            return 0
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return 0

        if not content.strip():
            return 0

        chunks = self._chunk(content, filepath)
        if not chunks:
            return 0

        ids = [self._chunk_id(filepath, i) for i in range(len(chunks))]
        metas = [{"filepath": str(filepath), "chunk_index": i} for i in range(len(chunks))]

        # upsert so re-indexing is safe
        self.collection.upsert(documents=chunks, ids=ids, metadatas=metas)
        return len(chunks)

    def index_folder(self, folder: str):
        """Walk a folder and index everything supported."""
        folder_path = Path(folder)
        total = 0
        files = list(folder_path.rglob("*"))
        for f in files:
            if f.is_file() and ".git" not in f.parts and "node_modules" not in f.parts and "__pycache__" not in f.parts:
                total += self.index_file(f)
        print(f"Indexed {total} chunks from {folder}")

    def query(self, question: str, n_results: int = 5) -> str:
        """Return relevant file chunks as a single context string."""
        results = self.collection.query(query_texts=[question], n_results=n_results)
        if not results["documents"][0]:
            return ""

        context_parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_parts.append(f"--- {meta['filepath']} ---\n{doc}")

        return "\n\n".join(context_parts)

    def _chunk(self, content: str, filepath: Path, size: int = 800, overlap: int = 100) -> list[str]:
        lines = content.splitlines()
        chunks = []
        current = []
        current_len = 0

        for line in lines:
            current.append(line)
            current_len += len(line)
            if current_len >= size:
                chunks.append(f"File: {filepath}\n" + "\n".join(current))
                current = current[-overlap:]
                current_len = sum(len(l) for l in current)

        if current:
            chunks.append(f"File: {filepath}\n" + "\n".join(current))

        return chunks

    def _chunk_id(self, filepath: Path, index: int) -> str:
        return hashlib.md5(f"{filepath}:{index}".encode()).hexdigest()
```

### Wire RAG into cli.py
```python
from core.llm import LLM
from core.rag import RAG
from rich.console import Console
from rich.markdown import Markdown
import yaml

console = Console()
llm = LLM()
rag = RAG()

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

# index watched folders on startup
console.print("[dim]indexing files...[/dim]")
for folder in config["paths"]["watched_folders"]:
    rag.index_folder(folder)
console.print("[dim]ready[/dim]\n")

console.print("[bold cyan]Enosym[/] — type 'exit' to quit, 'clear' to reset\n")

while True:
    try:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "clear":
            llm.clear_history()
            console.print("[dim]context cleared[/dim]\n")
            continue

        # pull relevant file context before every message
        context = rag.query(user_input)
        response = llm.chat(user_input, context=context)
        console.print(Markdown(f"**enosym:** {response}\n"))

    except KeyboardInterrupt:
        break
```

**Test it:**
Point the watched_folders at your projects directory in settings.yaml, run `python cli.py`, and ask it something specific about one of your files. It should actually know.

---

## Phase 3 — Tool calling (file ops + shell)

**What you're building:** Enosym can now *do* things, not just answer questions. Create files, edit files, run shell commands, list directories.

**When it's done:** You can say "create a file called notes.txt with a summary of what we just discussed" and it does it.

### core/tools.py
```python
import subprocess
import os
from pathlib import Path
from datetime import datetime
import json

# Every tool returns a dict: {"success": bool, "result": str}

def read_file(path: str) -> dict:
    try:
        content = Path(path).read_text(encoding="utf-8")
        return {"success": True, "result": content}
    except Exception as e:
        return {"success": False, "result": str(e)}

def write_file(path: str, content: str) -> dict:
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        return {"success": True, "result": f"Written to {path}"}
    except Exception as e:
        return {"success": False, "result": str(e)}

def append_file(path: str, content: str) -> dict:
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "result": f"Appended to {path}"}
    except Exception as e:
        return {"success": False, "result": str(e)}

def delete_file(path: str) -> dict:
    # ALWAYS called with confirmation gate before reaching here
    try:
        Path(path).unlink()
        return {"success": True, "result": f"Deleted {path}"}
    except Exception as e:
        return {"success": False, "result": str(e)}

def list_dir(path: str) -> dict:
    try:
        entries = list(Path(path).iterdir())
        formatted = "\n".join(
            f"{'[DIR]' if e.is_dir() else '[FILE]'} {e.name}" for e in sorted(entries)
        )
        return {"success": True, "result": formatted}
    except Exception as e:
        return {"success": False, "result": str(e)}

def run_command(command: str, cwd: str = None) -> dict:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        output = result.stdout + result.stderr
        return {"success": result.returncode == 0, "result": output or "(no output)"}
    except subprocess.TimeoutExpired:
        return {"success": False, "result": "Command timed out after 30s"}
    except Exception as e:
        return {"success": False, "result": str(e)}

def search_files(folder: str, query: str) -> dict:
    """Simple grep-style search across files."""
    try:
        matches = []
        for f in Path(folder).rglob("*"):
            if f.is_file() and ".git" not in f.parts:
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if query.lower() in content.lower():
                        matches.append(str(f))
                except Exception:
                    continue
        return {"success": True, "result": "\n".join(matches) if matches else "No matches found"}
    except Exception as e:
        return {"success": False, "result": str(e)}

# Tool registry — LLM gets this as its available toolset
TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "append_file": append_file,
    "delete_file": delete_file,
    "list_dir": list_dir,
    "run_command": run_command,
    "search_files": search_files,
}

# Actions that require user confirmation before running
IRREVERSIBLE = {"delete_file", "run_command", "write_file"}

TOOL_DESCRIPTIONS = """
You have access to these tools. To use one, respond with a JSON block like:
{"tool": "tool_name", "args": {"arg1": "value1"}}

Available tools:
- read_file(path): Read contents of a file
- write_file(path, content): Create or overwrite a file
- append_file(path, content): Add content to end of file
- delete_file(path): Permanently delete a file — will ask user to confirm
- list_dir(path): List contents of a directory
- run_command(command, cwd?): Run a shell command — will ask user to confirm
- search_files(folder, query): Search for a string across all files in a folder

Only use a tool when it's actually needed to answer the question.
If using a tool, respond with ONLY the JSON block, nothing else.
"""
```

### core/router.py
```python
import json
import re
from core.tools import TOOLS, IRREVERSIBLE, TOOL_DESCRIPTIONS
from core.llm import LLM

class Router:
    """Intercepts LLM responses, detects tool calls, executes them, feeds results back."""

    def __init__(self, llm: LLM):
        self.llm = llm

    def run(self, user_message: str, context: str = "") -> str:
        # tell the LLM about its tools
        augmented_message = f"{TOOL_DESCRIPTIONS}\n\nUser request: {user_message}"
        response = self.llm.chat(augmented_message, context=context)

        # check if it wants to use a tool
        tool_call = self._extract_tool_call(response)
        if not tool_call:
            return response

        tool_name = tool_call.get("tool")
        args = tool_call.get("args", {})

        if tool_name not in TOOLS:
            return f"Unknown tool: {tool_name}"

        # confirmation gate for irreversible actions
        if tool_name in IRREVERSIBLE:
            confirmed = self._confirm(tool_name, args)
            if not confirmed:
                return "Okay, cancelled."

        result = TOOLS[tool_name](**args)
        result_text = result["result"]

        # feed the tool result back to the LLM to get a proper response
        followup = self.llm.chat(
            f"Tool '{tool_name}' returned:\n{result_text}\n\nNow respond to the user based on this result."
        )
        return followup

    def _extract_tool_call(self, text: str) -> dict | None:
        try:
            match = re.search(r'\{[^{}]*"tool"[^{}]*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return None

    def _confirm(self, tool_name: str, args: dict) -> bool:
        print(f"\n[confirm] About to run '{tool_name}' with args: {args}")
        response = input("Confirm? (yes/no): ").strip().lower()
        return response in {"yes", "y"}
```

### Update cli.py to use Router
```python
from core.llm import LLM
from core.rag import RAG
from core.router import Router
from rich.console import Console
from rich.markdown import Markdown
import yaml

console = Console()
llm = LLM()
rag = RAG()
router = Router(llm)

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

console.print("[dim]indexing files...[/dim]")
for folder in config["paths"]["watched_folders"]:
    rag.index_folder(folder)
console.print("[bold cyan]Enosym[/] ready\n")

while True:
    try:
        user_input = input("you: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        if user_input.lower() == "clear":
            llm.clear_history()
            console.print("[dim]context cleared[/dim]\n")
            continue

        context = rag.query(user_input)
        response = router.run(user_input, context=context)
        console.print(Markdown(f"**enosym:** {response}\n"))

    except KeyboardInterrupt:
        break
```

**Test it:**
Ask it to list a directory, read a specific file, create a test file. It should do all of these. For anything irreversible it should ask you to confirm.

---

## Phase 4 — Voice I/O

**What you're building:** Full voice loop. Say something → Enosym hears it → thinks → responds out loud. Plus a wake word so it's always passively listening.

**When it's done:** You can have a voice conversation with it hands-free.

### Install dependencies
```bash
pip install faster-whisper sounddevice soundfile numpy
pip install kokoro-onnx
pip install pvporcupine  # wake word — free tier available at picovoice.com
```

For Kokoro, download the ONNX model files:
```bash
# Run this once to download
python -c "from kokoro_onnx import Kokoro; k = Kokoro('kokoro-v0_19.onnx', 'voices.bin')"
# If that fails, manually download from:
# https://github.com/thewh1teagle/kokoro-onnx/releases
```

### voice/stt.py
```python
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
```

### voice/tts.py
```python
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
```

### voice/wake.py
```python
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
```

### voice_cli.py
```python
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
```

**Test it:**
```bash
python voice_cli.py
```
Press Enter, speak, hear the response. This is where it starts feeling real.

---

## Phase 5 — Browser automation

**What you're building:** Enosym can open a browser, navigate to pages, click things, fill forms, and scrape content — including pages you're logged into.

**When it's done:** You can say "go to my GitHub and summarize my open PRs" and it does it.

### Install dependencies
```bash
pip install playwright beautifulsoup4 requests
playwright install chromium
```

### agents/browser.py
```python
from playwright.sync_api import sync_playwright, Page
from bs4 import BeautifulSoup
import time

class Browser:
    def __init__(self, headless=False, use_profile=True):
        self.headless = headless
        self.use_profile = use_profile
        self._playwright = None
        self._browser = None
        self._page = None

    def start(self):
        self._playwright = sync_playwright().start()

        if self.use_profile:
            # use your actual Chrome profile — you're already logged into everything
            # find your profile path: chrome://version → Profile Path
            self._browser = self._playwright.chromium.launch_persistent_context(
                user_data_dir="C:/Users/YOUR_USERNAME/AppData/Local/Google/Chrome/User Data",
                channel="chrome",
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
        else:
            self._browser = self._playwright.chromium.launch(headless=self.headless)
            self._page = self._browser.new_page()

    def stop(self):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def navigate(self, url: str) -> str:
        self._page.goto(url, wait_until="domcontentloaded", timeout=15000)
        time.sleep(1)
        return self.get_page_text()

    def get_page_text(self) -> str:
        html = self._page.content()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:8000]  # cap at 8k chars

    def click(self, selector: str):
        self._page.click(selector)
        time.sleep(0.5)

    def fill(self, selector: str, value: str):
        self._page.fill(selector, value)

    def search_google(self, query: str) -> list[dict]:
        self._page.goto(f"https://www.google.com/search?q={query}")
        time.sleep(1)
        results = []
        links = self._page.query_selector_all("a[href]")
        for link in links[:10]:
            href = link.get_attribute("href")
            text = link.inner_text()
            if href and href.startswith("http") and "google" not in href:
                results.append({"url": href, "title": text})
        return results[:5]

    def deep_research(self, topic: str, pages: int = 3) -> str:
        """Search a topic, visit top results, synthesize content."""
        results = self.search_google(topic)
        all_content = []
        for result in results[:pages]:
            try:
                content = self.navigate(result["url"])
                all_content.append(f"Source: {result['url']}\n{content}")
            except Exception:
                continue
        return "\n\n---\n\n".join(all_content)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
```

Wire the browser into your tools registry in core/tools.py:
```python
# Add to TOOLS dict in tools.py
def browse_url(url: str) -> dict:
    from agents.browser import Browser
    with Browser(headless=True) as b:
        content = b.navigate(url)
    return {"success": True, "result": content}

def research_topic(topic: str) -> dict:
    from agents.browser import Browser
    with Browser(headless=True) as b:
        content = b.deep_research(topic)
    return {"success": True, "result": content}

def google_search(query: str) -> dict:
    from agents.browser import Browser
    with Browser(headless=True) as b:
        results = b.search_google(query)
    formatted = "\n".join(f"{r['title']}: {r['url']}" for r in results)
    return {"success": True, "result": formatted}

TOOLS["browse_url"] = browse_url
TOOLS["research_topic"] = research_topic
TOOLS["google_search"] = google_search
```

---

## Phase 6 — Email + GitHub

**What you're building:** Enosym reads your Gmail and interacts with your GitHub repos.

### Gmail setup
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

Go to console.cloud.google.com → create a project → enable Gmail API → create OAuth2 credentials → download as `config/credentials/gmail_credentials.json`

### agents/email_agent.py
```python
import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
CREDS_FILE = "config/credentials/gmail_credentials.json"
TOKEN_FILE = "config/credentials/gmail_token.pickle"

class EmailAgent:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        return build("gmail", "v1", credentials=creds)

    def get_inbox(self, max_results=10) -> list[dict]:
        results = self.service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = results.get("messages", [])
        emails = []
        for msg in messages:
            detail = self.service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": detail.get("snippet", "")
            })
        return emails

    def get_email_body(self, message_id: str) -> str:
        msg = self.service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        payload = msg["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    return base64.urlsafe_b64decode(data).decode("utf-8")
        return msg.get("snippet", "")

    def send_email(self, to: str, subject: str, body: str) -> dict:
        # ALWAYS called with confirmation gate
        import email.mime.text
        import email.mime.multipart
        message = email.mime.multipart.MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(email.mime.text.MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        self.service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return {"success": True, "result": f"Email sent to {to}"}
```

### GitHub setup
```bash
pip install PyGithub
```

Get a personal access token from github.com/settings/tokens — give it repo scope.

### agents/github_agent.py
```python
from github import Github
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

class GitHubAgent:
    def __init__(self):
        token = config.get("github", {}).get("token", "")
        self.g = Github(token)
        self.user = self.g.get_user()

    def list_repos(self) -> list[dict]:
        repos = []
        for repo in self.user.get_repos():
            repos.append({
                "name": repo.name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "language": repo.language,
                "updated": str(repo.updated_at)
            })
        return repos

    def get_open_prs(self, repo_name: str) -> list[dict]:
        repo = self.g.get_repo(f"{self.user.login}/{repo_name}")
        prs = []
        for pr in repo.get_pulls(state="open"):
            prs.append({
                "title": pr.title,
                "number": pr.number,
                "author": pr.user.login,
                "created": str(pr.created_at),
                "url": pr.html_url
            })
        return prs

    def get_issues(self, repo_name: str) -> list[dict]:
        repo = self.g.get_repo(f"{self.user.login}/{repo_name}")
        issues = []
        for issue in repo.get_issues(state="open"):
            issues.append({
                "title": issue.title,
                "number": issue.number,
                "created": str(issue.created_at),
                "url": issue.html_url
            })
        return issues

    def create_issue(self, repo_name: str, title: str, body: str) -> dict:
        repo = self.g.get_repo(f"{self.user.login}/{repo_name}")
        issue = repo.create_issue(title=title, body=body)
        return {"url": issue.html_url, "number": issue.number}
```

Add GitHub token to settings.yaml:
```yaml
github:
  token: "your_github_pat_here"
```

---

## Phase 7 — Memory

**What you're building:** Enosym remembers things across sessions. Every conversation gets summarized and stored. Relevant past context gets injected automatically.

**When it's done:** Start a new session, reference something from a week ago, and it knows.

### Install dependencies
```bash
pip install sqlite-utils
```

### core/memory.py
```python
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

DB_PATH = config["paths"]["memory_db"]

class Memory:
    def __init__(self):
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                summary TEXT,
                full_log TEXT,
                importance REAL DEFAULT 0.5,
                tags TEXT DEFAULT '[]'
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                fact TEXT,
                source TEXT,
                importance REAL DEFAULT 0.5
            );
        """)
        self.conn.commit()

    def save_conversation(self, messages: list[dict], summary: str, importance: float = 0.5):
        self.conn.execute(
            "INSERT INTO conversations (timestamp, summary, full_log, importance) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), summary, json.dumps(messages), importance)
        )
        self.conn.commit()

    def save_fact(self, fact: str, source: str = "conversation", importance: float = 0.5):
        self.conn.execute(
            "INSERT INTO facts (timestamp, fact, source, importance) VALUES (?, ?, ?, ?)",
            (datetime.now().isoformat(), fact, source, importance)
        )
        self.conn.commit()

    def get_recent_conversations(self, limit: int = 5) -> list[dict]:
        cursor = self.conn.execute(
            "SELECT timestamp, summary, importance FROM conversations ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        return [{"timestamp": r[0], "summary": r[1], "importance": r[2]} for r in cursor.fetchall()]

    def get_relevant_context(self, query: str, limit: int = 3) -> str:
        # simple keyword search for now — upgrade to embedding search in a future pass
        words = query.lower().split()
        results = []

        cursor = self.conn.execute("SELECT timestamp, summary FROM conversations ORDER BY timestamp DESC LIMIT 50")
        for row in cursor.fetchall():
            if any(word in row[1].lower() for word in words):
                results.append(f"[{row[0][:10]}] {row[1]}")
                if len(results) >= limit:
                    break

        cursor = self.conn.execute("SELECT timestamp, fact FROM facts ORDER BY importance DESC LIMIT 20")
        for row in cursor.fetchall():
            if any(word in row[1].lower() for word in words):
                results.append(f"[fact] {row[1]}")

        return "\n".join(results) if results else ""

    def flush_old_low_importance(self, days: int = 30, threshold: float = 0.3):
        """Delete old conversations that weren't very important."""
        self.conn.execute("""
            DELETE FROM conversations
            WHERE importance < ?
            AND timestamp < datetime('now', ? || ' days')
        """, (threshold, f"-{days}"))
        self.conn.commit()

    def get_summary_for_session(self) -> str:
        recent = self.get_recent_conversations(limit=3)
        if not recent:
            return ""
        return "Recent context:\n" + "\n".join(f"- {c['summary']}" for c in recent)
```

---

## Phase 8 — Agent mode

**What you're building:** Give Enosym a multi-step task and it executes the whole thing — planning, using tools, confirming before irreversible steps, reporting back.

**When it's done:** "Research the top 3 alternatives to Supabase, summarize them, and create a markdown file with your findings" — and it does all of it.

### agents/agent.py
```python
from core.llm import LLM
from core.tools import TOOLS, IRREVERSIBLE
from core.rag import RAG
from core.memory import Memory
import json
import re

AGENT_SYSTEM = """
You are an autonomous agent. You have been given a task to complete.
Break it into steps. Execute each step using available tools.
After each tool result, decide what to do next.
When the task is complete, summarize what you did.

Available tools: read_file, write_file, append_file, delete_file, list_dir,
run_command, search_files, browse_url, research_topic, google_search

To use a tool: {"tool": "name", "args": {}}
To finish: {"done": true, "summary": "what I did"}
"""

class Agent:
    def __init__(self, llm: LLM, rag: RAG = None, memory: Memory = None):
        self.llm = llm
        self.rag = rag
        self.memory = memory
        self.max_steps = 15
        self.log = []

    def run(self, task: str) -> str:
        print(f"\n[agent] Starting task: {task}")
        self.log = []

        messages = [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user", "content": f"Task: {task}"}
        ]

        for step in range(self.max_steps):
            response = self.llm.llm_raw(messages)
            self.log.append({"step": step, "response": response})

            # check if done
            done = self._extract_done(response)
            if done:
                summary = done.get("summary", "Task complete.")
                print(f"[agent] Done: {summary}")
                if self.memory:
                    self.memory.save_conversation(
                        messages, summary=f"Agent task: {task[:100]}", importance=0.7
                    )
                return summary

            # check for tool call
            tool_call = self._extract_tool_call(response)
            if not tool_call:
                # no tool call, no done — just keep the response as is
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": "Continue. What's next?"})
                continue

            tool_name = tool_call.get("tool")
            args = tool_call.get("args", {})

            if tool_name not in TOOLS:
                result_text = f"Unknown tool: {tool_name}"
            elif tool_name in IRREVERSIBLE:
                confirmed = self._confirm(tool_name, args)
                if not confirmed:
                    result_text = "User cancelled this action."
                else:
                    result = TOOLS[tool_name](**args)
                    result_text = result["result"]
            else:
                result = TOOLS[tool_name](**args)
                result_text = result["result"]

            print(f"[agent] step {step+1}: {tool_name} → {result_text[:100]}...")

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Tool result: {result_text}\n\nContinue."})

        return "Agent hit max steps without completing task. Check the log."

    def _extract_tool_call(self, text: str) -> dict | None:
        try:
            match = re.search(r'\{[^{}]*"tool"[^{}]*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return None

    def _extract_done(self, text: str) -> dict | None:
        try:
            match = re.search(r'\{[^{}]*"done"[^{}]*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return None

    def _confirm(self, tool_name: str, args: dict) -> bool:
        print(f"\n[confirm] Agent wants to run '{tool_name}': {args}")
        return input("Allow? (yes/no): ").strip().lower() in {"yes", "y"}
```

Add `llm_raw` to core/llm.py:
```python
def llm_raw(self, messages: list[dict]) -> str:
    response = ollama.chat(model=self.model, messages=messages)
    return response["message"]["content"]
```

---

## Phase 9 — System tray UI

**What you're building:** A background process with a tray icon. Click to open a chat window. Everything else runs silently.

### Install dependencies
```bash
pip install pystray pillow PyQt6
```

### ui/tray.py
```python
import pystray
from PIL import Image, ImageDraw
import threading
import subprocess
import sys

def create_icon():
    img = Image.new("RGB", (64, 64), color=(18, 18, 18))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 56, 56], fill=(251, 191, 36))  # amber dot
    return img

def open_chat():
    subprocess.Popen([sys.executable, "ui/chat_window.py"])

def on_quit(icon, item):
    icon.stop()

def run_tray():
    icon = pystray.Icon(
        "enosym",
        create_icon(),
        "Enosym",
        menu=pystray.Menu(
            pystray.MenuItem("Open chat", lambda i, item: open_chat()),
            pystray.MenuItem("Quit", on_quit)
        )
    )
    icon.run()
```

### ui/chat_window.py
```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton
from PyQt6.QtCore import QThread, pyqtSignal
from core.llm import LLM
from core.rag import RAG
from core.router import Router
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

class WorkerThread(QThread):
    result_ready = pyqtSignal(str)

    def __init__(self, router, user_input, context):
        super().__init__()
        self.router = router
        self.user_input = user_input
        self.context = context

    def run(self):
        response = self.router.run(self.user_input, context=self.context)
        self.result_ready.emit(response)

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Enosym")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("background-color: #0f0f0f; color: #e5e5e5;")

        self.llm = LLM()
        self.rag = RAG()
        self.router = Router(self.llm)

        central = QWidget()
        layout = QVBoxLayout(central)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background: #1a1a1a; border: none; padding: 12px; font-size: 14px;")

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask Enosym anything...")
        self.input_field.setStyleSheet("background: #262626; border: 1px solid #333; padding: 10px; font-size: 14px; border-radius: 6px;")
        self.input_field.returnPressed.connect(self.send_message)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet("background: #f59e0b; color: #000; padding: 10px 20px; border: none; border-radius: 6px; font-weight: bold;")
        send_btn.clicked.connect(self.send_message)

        layout.addWidget(self.chat_display)
        layout.addWidget(self.input_field)
        layout.addWidget(send_btn)
        self.setCentralWidget(central)

    def send_message(self):
        user_input = self.input_field.text().strip()
        if not user_input:
            return
        self.input_field.clear()
        self.append_message("You", user_input)

        context = self.rag.query(user_input)
        self.worker = WorkerThread(self.router, user_input, context)
        self.worker.result_ready.connect(lambda r: self.append_message("Enosym", r))
        self.worker.start()

    def append_message(self, sender, message):
        color = "#f59e0b" if sender == "Enosym" else "#888"
        self.chat_display.append(f'<span style="color:{color};font-weight:bold">{sender}:</span> {message}<br>')

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
```

### main.py — ties everything together
```python
import threading
from ui.tray import run_tray
from voice.wake import WakeWord
from voice.stt import STT
from voice.tts import TTS
from core.llm import LLM
from core.rag import RAG
from core.router import Router
from core.memory import Memory
import yaml

with open("config/settings.yaml") as f:
    config = yaml.safe_load(f)

def run_voice_loop(router, rag, stt, tts, memory):
    wake = WakeWord(access_key=config["picovoice"]["access_key"])
    while True:
        wake.wait_for_wake_word()
        tts.speak("Yeah?")
        user_input = stt.listen()
        if not user_input:
            continue
        print(f"you: {user_input}")
        context = rag.query(user_input)
        mem_context = memory.get_relevant_context(user_input)
        full_context = f"{mem_context}\n\n{context}".strip()
        response = router.run(user_input, context=full_context)
        print(f"enosym: {response}")
        tts.speak(response)

if __name__ == "__main__":
    llm = LLM()
    rag = RAG()
    router = Router(llm)
    memory = Memory()
    stt = STT()
    tts = TTS()

    for folder in config["paths"]["watched_folders"]:
        rag.index_folder(folder)

    voice_thread = threading.Thread(
        target=run_voice_loop,
        args=(router, rag, stt, tts, memory),
        daemon=True
    )
    voice_thread.start()

    run_tray()  # blocks — tray runs on main thread
```

Add picovoice key to settings.yaml:
```yaml
picovoice:
  access_key: "your_key_here"
```

---

## Phase 10 — Calendar

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

Same OAuth2 flow as Gmail but enable Google Calendar API instead. Then:

### agents/calendar_agent.py
```python
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
import pickle, os

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "config/credentials/calendar_token.pickle"
CREDS_FILE = "config/credentials/calendar_credentials.json"

class CalendarAgent:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                creds = pickle.load(f)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, "wb") as f:
                pickle.dump(creds, f)
        return build("calendar", "v3", credentials=creds)

    def get_upcoming(self, days: int = 7) -> list[dict]:
        now = datetime.utcnow().isoformat() + "Z"
        end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        events_result = self.service.events().list(
            calendarId="primary", timeMin=now, timeMax=end,
            singleEvents=True, orderBy="startTime"
        ).execute()
        events = []
        for e in events_result.get("items", []):
            start = e["start"].get("dateTime", e["start"].get("date"))
            events.append({"title": e.get("summary", ""), "start": start, "id": e["id"]})
        return events

    def create_event(self, title: str, start: str, end: str, description: str = "") -> dict:
        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start, "timeZone": "America/Toronto"},
            "end": {"dateTime": end, "timeZone": "America/Toronto"},
        }
        created = self.service.events().insert(calendarId="primary", body=event).execute()
        return {"url": created.get("htmlLink"), "id": created["id"]}
```

---

## requirements.txt

```
ollama
pyyaml
rich
chromadb
sentence-transformers
watchdog
faster-whisper
sounddevice
soundfile
numpy
kokoro-onnx
pvporcupine
playwright
beautifulsoup4
requests
google-auth
google-auth-oauthlib
google-api-python-client
PyGithub
sqlite-utils
pystray
pillow
PyQt6
```

---

## Gotchas and known issues on Windows

- `sounddevice` needs Microsoft C++ Build Tools if it fails to install — get it from visualstudio.microsoft.com/visual-cpp-build-tools
- Playwright on Windows needs `playwright install chromium` run separately
- If Chrome profile path doesn't work for browser agent, start without `use_profile=True` first and log in manually during the session
- Whisper on first run downloads the model — takes a minute, normal
- Kokoro ONNX files need to be in the root directory unless you adjust the paths
- pvporcupine free tier limits you to built-in wake words ("jarvis", "computer", "hey siri" etc) — custom "hey enosym" needs a paid account or you swap to a different wake word library like `openwakeword` which is fully free

## Alternative free wake word — openwakeword
```bash
pip install openwakeword
```
Fully free, no account needed, trains custom wake words. Swap out wake.py to use this instead of pvporcupine if you don't want to sign up for Picovoice.

---

## What you'll have by the end

- A voice assistant running on your machine
- Knows your entire codebase and file system
- Can browse the web with your logged-in sessions
- Reads and sends your email
- Interacts with your GitHub
- Reads your calendar
- Remembers everything across sessions
- Runs as a background tray app
- Costs nothing after setup
- Never sends your data anywhere