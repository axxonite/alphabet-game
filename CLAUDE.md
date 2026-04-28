# AlphabetGame

Vanilla JS web app — a kids' alphabet game that listens for spoken letters and lights them up. Single-file: [index.html](index.html) plus [recognizer-processor.js](recognizer-processor.js) (AudioWorklet for Vosk).

## Always run a local server

The user tests the game in a browser after most changes. **Always make sure a local server is running** at http://localhost:8000 so they can refresh and try things immediately. Opening `index.html` as `file://` does not work — AudioWorklet, `fetch` of the Vosk model, and Web Speech API all require an HTTP origin.

Start it (background) at the start of any session that touches the game:

```bash
python -m http.server 8000
```

If port 8000 is already in use, assume the existing server is fine — don't start a second one. If unsure, `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/` should return `200`.

## Speech engines

The app supports two recognizers, selectable from the UI and persisted in `localStorage["engine"]`:

- **Vosk** (default, offline): uses `vosk-browser` + a small Kaldi model in `models/`. Streams continuously via AudioWorklet. Constrained grammar of letter-name pronunciations.
- **Web Speech API** (online): one-shot per tap. `continuous=true` is ignored on Android Chrome, so the UX is "press Listen, say one word, button auto-resets." Uses `maxAlternatives=5` and feeds every alternative through the matcher to compensate for the lack of biasing.

Both engines call the same `processTranscript()` and share the `LETTER_TOKENS` map — keep them aligned when changing recognition logic.

## Useful context

- Existing fuzzy-matching plan (deleted from `docs/` but in git history at commit `38c4117`) describes the H→"eight" / N-and-V-missing failure modes the user is trying to fix.
- The longer-term plan is a Capacitor wrap so iOS/Android native speech APIs (with phrase biasing) can be used — see `C:\Users\dfili\.claude\plans\what-are-our-options-composed-crane.md`.
