# Enosym

A fully local, free, autonomous AI lab partner. Voice-first. Runs on your machine. Has access to everything you have. Acts on your behalf. Never phones home, never costs a cent after setup.

This isn't a chatbot. It's a second brain that knows your files, your code, your email, your browser, and your calendar — and can do things with all of it, autonomously, while you work on something else.

---

## What this should become — full scope

This document is the north star. Everything listed here is the target. Build order is separate. This is just what we're building toward.

---

## Perception — what Enosym can see

- [ ] Full file system indexing — reads and watches all your files, projects, notes, documents
- [ ] Screen awareness — knows what app is in focus, what file is open, what code you're looking at
- [ ] Microphone — always listening for wake word ("hey Enosym"), then live voice input
- [ ] Browser — current tab URL, page content, logged-in session access
- [ ] Email — reads full inbox and threads, understands context across conversations
- [ ] GitHub — repos, issues, PRs, commit history, CI status
- [ ] Calendar — current events, upcoming deadlines, free blocks
- [ ] Terminal history — what commands you've been running and what they returned
- [ ] Clipboard — whatever you just copied is available as context
- [ ] System state — what processes are running, resource usage, service health

---

## Knowledge — what Enosym knows

- [ ] RAG over your entire file system — ask it anything about any file or project and it knows
- [ ] Understands your active projects end to end — not just individual files, the whole architecture
- [ ] Persistent memory across all sessions — nothing you tell it is forgotten unless it decides it's irrelevant
- [ ] Builds a model of you over time — your goals, your working style, your preferences, your current priority stack
- [ ] Surfaces relevant past context automatically without you asking — "last time you worked on this you got stuck on X"
- [ ] Knows what you're trying to accomplish this week, this month, long term
- [ ] Self-manages memory — flushes low-importance old entries, keeps important ones indefinitely, summarizes old conversations rather than storing them raw

---

## Actions — what Enosym can do

### Files and code
- [ ] Read, create, edit, delete files anywhere on your system
- [ ] Understand your codebase and answer questions about it in full context
- [ ] Write code, run it, read the error output, fix it, iterate — full autonomous debug loop
- [ ] Run shell commands and report results
- [ ] Push to GitHub — commits, PRs, branch management — on your instruction
- [ ] Monitor running services and alert you if something crashes or misbehaves

### Web and research
- [ ] Browse the live internet with a real browser — not just HTTP requests, actual Chrome/Firefox automation that can navigate, click, scroll, log in
- [ ] Access pages behind your logged-in sessions — GCP console, Supabase, Notion, anything you're already signed into
- [ ] Deep research mode — given a topic, opens multiple pages, reads them fully, synthesizes a proper report with citations
- [ ] Web monitoring — watch a page or search query for changes and surface alerts (new job postings, price changes, repo updates, anything)
- [ ] Fills out forms on your behalf when you tell it to

### Email and communication
- [ ] Read and summarize inbox on demand — "what do I need to respond to today"
- [ ] Draft emails in your actual voice and writing style
- [ ] Send emails after voice or text confirmation
- [ ] Draft and send follow-ups, recruiter replies, application emails autonomously
- [ ] Read email threads in full and understand the context before drafting replies

### Calendar and scheduling
- [ ] Read your calendar — tell you what's coming up, how long until your next thing, what your day looks like
- [ ] Schedule events when you ask
- [ ] Factor deadlines and events into its advice — "you have an exam in 3 days, want me to block time tonight for review"

### Autonomous multi-step tasks (agent mode)
- [ ] Accept a complex multi-step task and execute it fully without babysitting
- [ ] Runs background tasks while you work on something else entirely
- [ ] Asks for confirmation before any irreversible action (send, push, delete) via voice prompt or notification
- [ ] Keeps a full activity log of everything it did, every decision it made, every result it got
- [ ] Schedules recurring tasks — weekly summaries, daily briefings, monitoring jobs
- [ ] Can chain tools together on its own — research → write → save → send, all in one go

---

## Voice — how you interact

- [ ] Wake word detection — always listening passively for "hey Enosym", near-zero CPU cost when idle
- [ ] Natural conversation — not rigid command syntax, just talk to it normally
- [ ] Streaming responses — starts speaking before it's finished generating, no waiting for the full response
- [ ] Knows when to be brief and when to go deep based on the question
- [ ] Can talk while you code — you never have to look away from your screen
- [ ] Voice confirmation for sensitive actions — "I'm about to send this email to your recruiter, say yes to confirm"
- [ ] Mute toggle — hardware or hotkey, instant silence

---

## UI

- [ ] System tray icon — lives in the taskbar, near-invisible when not needed
- [ ] Click to open a minimal chat window for text interaction when you don't want voice
- [ ] Active task panel — shows what it's currently doing, queue of pending tasks
- [ ] Activity log viewer — full history of what it's done, searchable
- [ ] Settings panel — wake word toggle, mute, model selection, watched folders, connected accounts
- [ ] Notification toasts for alerts, confirmations, and task completions

---
...
## Privacy and architecture principles

- [ ] Fully local — nothing leaves your machine ever, no API calls to any external service
- [ ] Fully free — no subscriptions, no tokens, no usage limits after setup
- [ ] All models run on-device — LLM, embeddings, STT, TTS, all local
- [ ] All data stored locally — vector DB, memory, logs, everything on disk
- [ ] Open and inspectable — you can read every file it creates, every log it writes, every memory it stores
- [ ] No cloud sync, no telemetry, no analytics

---

## Build phases (rough order)

1. **Core LLM loop** — Ollama + model running locally, basic CLI interface working
2. **RAG over files** — ChromaDB + embeddings, ask questions about your own files
3. **Tool calling** — file read/write/create, shell commands, LLM can invoke them
4. **Voice I/O** — wake word + STT (faster-whisper) + TTS (Kokoro), full voice loop
5. **Browser automation** — Playwright agent that can navigate the live web and logged-in sessions
6. **Email + GitHub integration** — read/send email, interact with repos
7. **Memory system** — SQLite persistent memory, importance scoring, auto-flush
8. **Agent mode** — multi-step autonomous task execution with confirmation gates
9. **System tray UI** — minimal background process with tray icon and chat window
10. **Calendar + scheduling** — read and write calendar events
11. **Screen awareness** — knows what's in focus, current file, active app
12. **Monitoring + alerts** — web watchers, service health, proactive surface of relevant info

---

## The one-line version

You talk to it, it knows everything, it does the work, and it lives entirely on your machine.