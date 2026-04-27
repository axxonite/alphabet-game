# Improve fuzzy letter-recognition matching

## Context

After moving to Vosk, recognition still fails on individual letters because Vosk's general English model often emits a common word that *sounds like* the letter rather than the letter name itself — observed examples: H → `"eight"`, and reports of N and V missing entirely. The current matcher in [index.html `processTranscript`](../index.html) tries (a) exact alias lookup in `TOKEN_TO_LETTER`, (b) single-character fallback, (c) length-≤3 first-character fallback. None of those catch `"eight"` for H, and the alias lists for N and V are sparse.

The previous commit added a Vosk grammar constraint, but the vosk-browser README doesn't document a grammar parameter for `KaldiRecognizer`, so it may be silently ignored. Even if it works, ambiguity remains (e.g. `"see"` could be C, S, or just the word "see") — so we want a more forgiving, **expected-aware** matcher regardless.

Goal: when the kid clearly *intends* a letter, accept it. Reduce false negatives without raising false positives — the next letter the game expects is a strong context signal we currently ignore.

## Approach

### 1. Expected-aware matcher (the main change)

Instead of mapping `heard_token → letter` blindly, ask the inverse: *"could this token plausibly be the letter currently expected?"* Replace `TOKEN_TO_LETTER` and the three-tier fallback with a single per-letter variant table and one matcher.

**New data structure** (replaces `LETTER_TOKENS` and `TOKEN_TO_LETTER`):
```js
const LETTER_VARIANTS = {
  a: ["a","ay","aye","eh","hey"],
  b: ["b","be","bee","bea"],
  c: ["c","see","sea","cee"],
  d: ["d","de","dee"],
  e: ["e","ee","he"],
  f: ["f","ef","eff"],
  g: ["g","gee","jee"],
  h: ["h","aitch","haitch","ache","eight","ate","ace"],
  i: ["i","eye","aye"],
  j: ["j","jay"],
  k: ["k","kay","okay","ok"],
  l: ["l","el","ell"],
  m: ["m","em"],
  n: ["n","en","in","an","and","end","ann"],
  o: ["o","oh","owe"],
  p: ["p","pee","pea"],
  q: ["q","cue","queue","kew"],
  r: ["r","are","ar"],
  s: ["s","es","ess"],
  t: ["t","tee","tea","te"],
  u: ["u","you","ewe","yew"],
  v: ["v","vee","ve","vie"],
  w: ["w","double u","double you","double","dub"],
  x: ["x","ex","eks"],
  y: ["y","why","wye"],
  z: ["z","zee","zed"],
};
```
Notable additions vs. today: H ← `"eight"`/`"ate"`/`"ace"`; N ← `"and"`/`"end"`/`"ann"`; V ← `"vie"`. Also dropped a few entries that were causing false matches via the old reverse map (the `d: "the"` alias was a primary noise source — every Vosk transcript with "the" advanced D regardless of context).

**New matcher**:
```js
function matchesExpected(token, expectedLetter) {
  const variants = LETTER_VARIANTS[expectedLetter] || [];
  if (variants.includes(token)) return true;
  // single-char direct match (Vosk word-level may emit just the letter)
  if (token === expectedLetter) return true;
  // Levenshtein-1 forgiveness against any variant >=3 chars
  if (token.length >= 3) {
    for (const v of variants) {
      if (v.length >= 3 && editDistance1(token, v)) return true;
    }
  }
  return false;
}
```
`editDistance1(a, b)` returns true iff Damerau-Levenshtein distance is <=1. Tiny implementation, no library.

**New `processTranscript`**:
```js
function processTranscript(text) {
  heardEl.textContent = `Heard: "${text}"`;
  const cleaned = text.toLowerCase().replace(/[^a-z\s]/g, " ").replace(/\s+/g, " ").trim();
  if (!cleaned || currentIdx >= currentWord.length) return;

  const tokens = tokenizeWithCombos(cleaned); // 2-word combos for "double u" etc.
  for (const tok of tokens) {
    if (currentIdx >= currentWord.length) break;
    const expected = currentWord[currentIdx];
    if (matchesExpected(tok, expected)) {
      currentIdx++;
      renderWord();
      if (currentIdx === currentWord.length) {
        reward();
        return;
      }
    }
  }
}
```

### 2. Verify (and possibly remove) the Vosk grammar constraint

The previous commit passes a JSON grammar to `new model.KaldiRecognizer(sampleRate, grammar)` inside `initVosk`. If this is silently ignored by vosk-browser, it does nothing useful. After the matcher refactor, run the page once with the grammar and once without it (toggle a const) to confirm whether the grammar is actually narrowing outputs:

- Diagnostic: speak the alphabet straight through; capture all `Heard:` lines. If transcripts ever contain a non-letter-name word, the grammar is inactive (or some tokens are out-of-vocab and Vosk fell back).
- If inactive: leave grammar code in place but add a `// best-effort, may be ignored by vosk-browser` comment, since it can't hurt and may help in a future version. The expected-aware matcher carries the load.
- If active: keep it as-is — narrower outputs help the matcher even more.

### 3. Files to modify

- [index.html](../index.html) only:
  - Replace `LETTER_TOKENS` + `TOKEN_TO_LETTER` block with `LETTER_VARIANTS`.
  - Replace `processTranscript` body with the expected-aware version + add `matchesExpected` + `editDistance1` + `tokenizeWithCombos` helpers.
  - Update the grammar list inside `initVosk` to derive from `LETTER_VARIANTS` instead of `LETTER_TOKENS`.

### 4. Out of scope

- No changes to mic init, AudioWorklet, model loading, or the WebAudio fanfare.
- No changes to the word list or scaffolding.
- No phonetic library (Metaphone etc.) — the variant table + edit-distance-1 covers our needs without adding a dependency.

## Verification

For each letter A–Z, with that letter as the *current expected* in a contrived test word:

1. Speak the letter clearly. Should advance.
2. Speak the letter quickly/sloppily. Should still advance for letters with rich variant lists (H, N, V, W).
3. Speak a wrong letter. Should NOT advance.
4. Speak a non-letter word that previously caused false matches:
   - "the" with expected = D → should NOT advance (we removed that alias).
   - "okay" with expected ≠ K → should NOT advance (only matches when K is expected).
5. Spelling a real game word end-to-end (e.g. CAT, HOP, VAN) on Android Chrome and desktop Chrome — both should complete cleanly with the same audio behavior.
6. Watch the on-screen `Heard:` line for any letter that still fails after this change, and add the observed transcript to that letter's variant list as a follow-up.
