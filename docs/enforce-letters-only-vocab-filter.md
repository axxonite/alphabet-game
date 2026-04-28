# Enforce the Letters-only vocabulary on the app side

## Context

The user is in **Letters-only** mode and Vosk is still emitting non-letter words ("ham", "moon", etc.) instead of being constrained to the ~50-word letter-homophone grammar in [index.html `LETTERS_ONLY_GRAMMAR_WORDS`](../index.html). Investigation of vosk-browser 0.0.8 found that the second argument to `KaldiRecognizer(sampleRate, grammar)` exists in the TypeScript declarations but is **likely a stub** — there's no documentation, no examples, and no confirmation it's plumbed through to the underlying WASM `SetGrammar` call. The user's observation is consistent with the grammar parameter being silently ignored.

This isn't just a UX nit — the relaxed letters-only matcher will *falsely advance letters* on common noise words. Concrete trace: `ham = [HH,AE,M]` against expected M `[EH,M]` — stress EH passes (AE is in the EH cousin set), letters-only skips the onset rule, the trailing-cons rule with lenient cousins `{M,N,NG}` is satisfied by the M in heard → **accept**. So if Vosk emits "ham" while the kid is spelling, M pops on its own.

## Approach

Stop trusting Vosk to honor grammar. Add an app-side allowlist gate that runs in Letters-only mode only.

### 1. Build a runtime allowlist Set

In [index.html](../index.html), near the existing `LETTERS_ONLY_GRAMMAR_WORDS` const, derive a Set that contains every token Letters-only mode is willing to accept:

```js
const LETTERS_ONLY_ALLOWED = new Set([
  ...LETTERS_ONLY_GRAMMAR_WORDS,
  ...Array.from({length: 26}, (_, i) => String.fromCharCode(97 + i)),
  "u", "you", "double",   // W-combo seeds (already in the lists, kept explicit for clarity)
]);
// W combos arrive as a joined token (e.g. "double u") via tokenizeWithCombos —
// those go through W_COMBOS in matchesExpected and bypass this gate.
```

### 2. Gate token processing

In `processTranscript`, after `tokenizeWithCombos` produces the token list, drop tokens not in the allowlist when in letters-only mode — *before* the matcher sees them. Two-word combos (`double u`, `double you`) are exempt because they go to W via `W_COMBOS` directly.

```js
const tokens = tokenizeWithCombos(cleaned);
for (const tok of tokens) {
  if (currentIdx >= currentWord.length) break;
  if (pronunciationMode === "letters-only"
      && !TWO_WORD_COMBOS.has(tok)
      && !LETTERS_ONLY_ALLOWED.has(tok)) {
    continue;  // Vosk emitted a non-letter word; ignore it
  }
  if (matchesExpected(tok, currentWord[currentIdx])) { ... }
}
```

### 3. Surface what was filtered (debug aid)

Update the `Heard:` line in `processTranscript` to also indicate when a token was filtered, so the user can see when Vosk is misbehaving. Minimal change:

```js
heardEl.textContent = `Heard: "${text}"${filteredCount > 0 ? ` (${filteredCount} ignored)` : ""}`;
```

This is a quality-of-life signal; if it gets noisy, drop it.

### 4. Keep the grammar parameter

Continue passing the grammar to `KaldiRecognizer` in `initVosk` — if a future vosk-browser version starts honoring it, we get tighter recognition for free, and the app-side filter just becomes a no-op redundant safety net.

## Files to modify

- [index.html](../index.html):
  - After the `LETTERS_ONLY_GRAMMAR_WORDS` literal: add `LETTERS_ONLY_ALLOWED` Set.
  - In `processTranscript`: add the per-token allowlist gate; optionally update the `Heard:` line.

No changes to the matcher logic, the equivalence tables, the test harness, or the build script.

## Why not upgrade vosk-browser

Checked the npm registry: **0.0.8 is the latest** (published 2022-12-25, project dormant). The constructor has `grammar?: string` and the message infrastructure does forward it to the worker as `ClientMessageCreateRecognizer.grammar`, but there's no `setGrammar` runtime method and no public confirmation the worker calls Kaldi's `SetGrm` — the user's observation that non-letter words still come through is consistent with the worker silently ignoring it. App-side filter is the only path forward.

## Out of scope

- Adding/removing words in `LETTERS_ONLY_GRAMMAR_WORDS`. The current list is the right starting point; tune from real `Heard:` traces after this fix lands.
- Doing the same gate in Strict/Lenient modes. Those modes legitimately expect Vosk to emit common English words ("and", "the", "eight") that the matcher then maps to letters — gating them would break the matcher.

## Verification

1. **Reload page**, ensure Letters-only is selected (button reads "Letters-only", check `localStorage`).
2. **Spell HAM** (or any word that previously triggered the false match): say H, then A, then M. Watch the `Heard:` line.
   - Before fix: if Vosk emits "ham" mid-spelling, M can pop spontaneously.
   - After fix: "ham" is dropped (the line shows it was ignored), M only advances on actual letter utterances.
3. **Spell BED**: confirm Letters-only's relaxed matcher (B↔E acoustic confusion) still works — say each letter, all should advance.
4. **Spell VAN**: N step still advances on `am`/`an`/`en`/`n` (the lenient nasal rule).
5. **Switch to Lenient/Strict** and re-verify: noise words like "and"→N still match (gate is letters-only only).
