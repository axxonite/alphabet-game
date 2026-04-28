"""
Mirror of matchesExpected from index.html, run against phonemes.json.
Tests >100 cases focused on letters where Vosk historically fails (N, V, H).
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
PHONEMES = json.loads((REPO / "phonemes.json").read_text())

LETTER_PHONEMES = {
    "a": ["EY"],         "b": ["B","IY"],     "c": ["S","IY"],     "d": ["D","IY"],
    "e": ["IY"],         "f": ["EH","F"],     "g": ["JH","IY"],    "h": ["EY","CH"],
    "i": ["AY"],         "j": ["JH","EY"],    "k": ["K","EY"],     "l": ["EH","L"],
    "m": ["EH","M"],     "n": ["EH","N"],     "o": ["OW"],         "p": ["P","IY"],
    "q": ["K","Y","UW"], "r": ["AA","R"],     "s": ["EH","S"],     "t": ["T","IY"],
    "u": ["Y","UW"],     "v": ["V","IY"],     "w": ["D","AH","B","AH","L","Y","UW"],
    "x": ["EH","K","S"], "y": ["W","AY"],     "z": ["Z","IY"],
}
LETTER_STRESS = {
    "a":"EY","b":"IY","c":"IY","d":"IY","e":"IY","f":"EH","g":"IY","h":"EY",
    "i":"AY","j":"EY","k":"EY","l":"EH","m":"EH","n":"EH","o":"OW","p":"IY",
    "q":"UW","r":"AA","s":"EH","t":"IY","u":"UW","v":"IY","w":"UW",
    "x":"EH","y":"AY","z":"IY",
}
VOWELS = {"AA","AE","AH","AO","AW","AY","EH","ER","EY","IH","IY","OW","OY","UH","UW"}
STRESS_EQUIV = {
    "EY": {"EY","EH","AE"},
    "IY": {"IY","IH"},
    "EH": {"EH","AE","AH","IH"},
    "AY": {"AY"},
    "OW": {"OW","AO","AH","UH"},
    "UW": {"UW","UH"},
    "AA": {"AA","AO","AH"},
}
STRICT_TARGET_CONS_EQUIV = {
    "F":  {"F","V"},
    "CH": {"CH","T","JH","D","SH","S","Z","TH","DH"},
    "L":  {"L"},
    "M":  {"M"},
    "N":  {"N","NG"},
    "S":  {"S","Z","SH","ZH","TH"},
}
LENIENT_TARGET_CONS_EQUIV = {
    **STRICT_TARGET_CONS_EQUIV,
    "M": {"M","N","NG"},
    "N": {"N","M","NG"},
}
LENIENT_HEARD_CONS_EQUIV = {
    "B": {"B","P"}, "P": {"P","B"},
    "D": {"D","T"}, "T": {"T","D"},
}
W_COMBOS = {"double u","double you","doubleu","doubleyou","dub"}

MODE = "lenient"  # overridden by CLI


def matches(word, letter):
    if word == letter: return True
    if letter == "w" and word in W_COMBOS: return True
    heard = PHONEMES.get(word)
    if not heard: return False
    target = LETTER_PHONEMES[letter]
    equiv = STRESS_EQUIV[LETTER_STRESS[letter]]
    if not any(p in equiv for p in heard): return False

    lenient = MODE == "lenient"
    target_cons_table = LENIENT_TARGET_CONS_EQUIV if lenient else STRICT_TARGET_CONS_EQUIV

    if target[0] not in VOWELS:
        heard_cons = next((p for p in heard if p not in VOWELS), None)
        heard_equiv = LENIENT_HEARD_CONS_EQUIV.get(target[0]) if lenient else None
        if heard_equiv:
            if heard_cons not in heard_equiv: return False
        else:
            if heard_cons != target[0]: return False
    else:
        if heard[0] not in equiv: return False
        target_cons = [p for p in target if p not in VOWELS]
        if target_cons:
            last = target_cons[-1]
            cousins = target_cons_table.get(last, {last})
            if not any(p in cousins for p in heard): return False
    if len(heard) > len(target) + 2: return False
    return True


# Cases: (heard_word, expected_letter, should_match, note)
CASES = [
    # =================== N — flagged as missing entirely ===================
    ("n","n",True,"single char fast path"),
    ("en","n",True,"canonical"),
    ("an","n",True,"AE→EH stress equiv"),
    ("and","n",True,"AH→EH stress equiv (the headline N case)"),
    ("end","n",True,"exact stress vowel"),
    ("in","n",True,"IH→EH stress equiv"),
    ("inn","n",True,""),
    ("ann","n",True,"AE→EH"),
    ("any","n",True,"3-phon, has EH+N"),
    ("ant","n",True,"AE→EH"),
    ("am","n",False,"M ne N — fixed by trailing-cons rule"),
    ("ham","n",False,"cons-init H, vowel-init N requires heard[0] vowel"),
    ("hen","n",False,"cons-init HH"),
    ("men","n",False,"cons-init M"),
    ("then","n",False,"cons-init DH"),
    ("when","n",False,"cons-init W"),
    ("on","n",False,"AA not in EH-equiv"),
    ("one","n",False,"cons-init W"),
    ("done","n",False,"cons-init D"),
    ("moon","n",False,"cons-init M"),
    ("known","n",False,"cons-init N? n is consonant, but N is vowel-init letter — heard[0]=N not vowel"),

    # =================== V — flagged as missing entirely ===================
    ("v","v",True,"single char"),
    ("vee","v",True,"canonical"),
    ("ve","v",True,""),
    ("vie","v",False,"AY not IY-equiv (acceptable miss)"),
    ("eve","v",True,"V is cons in heard, target cons-init V matches"),
    ("we","v",False,"cons-init W"),
    ("be","v",False,"cons-init B"),
    ("me","v",False,"cons-init M"),
    ("he","v",False,"cons-init HH"),
    ("she","v",False,"cons-init SH"),
    ("the","v",False,"cons-init DH + IY-equiv miss"),
    ("three","v",False,"cons-init TH"),
    ("tree","v",False,"cons-init T"),
    ("see","v",False,"cons-init S"),
    ("free","v",False,"cons-init F"),
    ("green","v",False,"cons-init G"),
    ("very","v",True,"V cons-init match, has IY"),
    ("vote","v",False,"OW not IY-equiv"),
    ("view","v",False,"V cons-init ✓ but no IY-equiv (UW only)"),

    # =================== H — motivating example ===================
    ("h","h",True,""),
    ("eight","h",True,"the headline H case"),
    ("ate","h",True,""),
    ("ace","h",True,""),
    ("age","h",True,""),
    ("aim","h",False,"M not in CH-cousins — tightened"),
    ("aid","h",True,"D in CH-cousins"),
    ("ape","h",False,"P not in CH-cousins"),
    ("able","h",False,"B,L not in CH-cousins"),
    ("hey","h",False,"cons-init HH (acceptable miss)"),
    ("way","h",False,"cons-init W"),
    ("may","h",False,"cons-init M"),
    ("say","h",False,"cons-init S"),
    ("day","h",False,"cons-init D"),
    ("face","h",False,"cons-init F, vowel-init H needs heard[0]=EY-equiv"),

    # =================== A ===================
    ("a","a",True,""),
    ("ay","a",True,""),
    ("aye","a",False,"AY not EY"),
    ("eight","a",True,"shares EY with H — acceptable cross-match"),
    ("ate","a",True,"same"),
    ("hey","a",False,"cons-init HH, A vowel-init"),
    ("they","a",False,"cons-init DH"),
    ("say","a",False,"cons-init S"),
    ("the","a",False,""),

    # =================== B ===================
    ("b","b",True,""),
    ("be","b",True,""),
    ("bee","b",True,""),
    ("p","b",False,"cons-init mismatch"),
    ("pee","b",False,""),
    ("d","b",False,""),
    ("dee","b",False,""),
    ("the","b",False,""),
    ("we","b",False,""),

    # =================== C ===================
    ("c","c",True,""),
    ("see","c",True,""),
    ("sea","c",True,""),
    ("s","c",False,"S name = ess [EH,S], stress IY-equiv missing"),
    ("ess","c",False,""),
    ("she","c",False,"cons-init SH ≠ S"),
    ("seed","c",True,"len 3, S+IY"),

    # =================== D ===================
    ("d","d",True,""),
    ("dee","d",True,""),
    ("the","d",False,"the existing-bug fix"),
    ("be","d",False,""),
    ("bee","d",False,""),
    ("he","d",False,""),
    ("three","d",False,""),
    ("they","d",False,"cons-init DH ≠ D"),

    # =================== E ===================
    ("e","e",True,""),
    ("ee","e",True,""),
    ("he","e",False,"cons-init HH; E vowel-init needs heard[0]=IY/IH"),
    ("be","e",False,""),
    ("we","e",False,""),
    ("eat","e",True,"vowel-init [IY,T]"),
    ("each","e",True,""),
    ("east","e",True,""),

    # =================== F ===================
    ("f","f",True,""),
    ("ef","f",False,"not in CMU dict"),
    ("s","f",False,"S not in F-cousins — fixed"),
    ("ess","f",False,"same fix"),
    ("elf","f",True,"shares EH+F"),
    ("if","f",True,"[IH,F]; IH in EH-equiv, vowel-init heard[0]=IH ✓"),
    ("off","f",False,"AO; AO not in EH-equiv"),

    # =================== G ===================
    ("g","g",True,""),
    ("gee","g",True,""),
    ("jee","g",True,"jee IS in dict as [JH,IY] — canonical G sound"),
    ("j","g",False,""),
    ("jay","g",False,"stress EY ≠ IY-equiv"),

    # =================== I ===================
    ("i","i",True,""),
    ("eye","i",True,""),
    ("aye","i",True,""),
    ("high","i",False,"cons-init HH"),
    ("my","i",False,"cons-init M"),
    ("why","i",False,"cons-init W"),
    ("by","i",False,"cons-init B"),
    ("ice","i",True,"[AY,S] vowel-init AY ✓"),

    # =================== J ===================
    ("j","j",True,""),
    ("jay","j",True,""),
    ("a","j",False,""),
    ("hey","j",False,"cons-init HH ≠ JH"),
    ("day","j",False,"cons-init D ≠ JH"),
    ("age","j",True,"age=[EY,JH] cons-init JH=JH match — acceptable cross-match"),

    # =================== K ===================
    ("k","k",True,""),
    ("kay","k",True,""),
    ("okay","k",True,"OW skipped, K = K"),
    ("ok","k",True,""),
    ("q","k",False,"stress UW ≠ EY"),
    ("cue","k",False,""),
    ("cake","k",True,"[K,EY,K] cons-init K ✓ stress EY ✓"),
    ("came","k",True,""),

    # =================== L ===================
    ("l","l",True,""),
    ("el","l",True,""),
    ("m","l",False,"M=[EH,M]; L=[EH,L] vowel-init heard[0]=EH ✓ — known cross-match issue"),
    ("em","l",False,"same — cross-match"),
    ("else","l",True,""),

    # =================== M ===================
    ("m","m",True,""),
    ("em","m",True,""),
    ("n","m",False,"N=[EH,N]; M=[EH,M] — vowel-init cross-match"),
    ("en","m",False,""),
    ("am","m",True,"[AE,M]; AE in EH-equiv ✓"),

    # =================== N (more) ===================
    ("on","n",False,""),
    ("up","n",False,"no EH-equiv vowel"),

    # =================== O ===================
    ("o","o",True,""),
    ("oh","o",True,""),
    ("owe","o",True,""),
    ("go","o",False,"cons-init G"),
    ("no","o",False,""),
    ("so","o",False,""),
    ("low","o",False,""),
    ("on","o",False,"AA not in OW-equiv {OW,AO,AH,UH}"),
    ("ought","o",True,"[AO,T] AO in OW-equiv"),

    # =================== P ===================
    ("p","p",True,""),
    ("pee","p",True,""),
    ("pea","p",True,""),
    ("b","p",False,""),
    ("be","p",False,""),
    ("bee","p",False,""),

    # =================== Q ===================
    ("q","q",True,""),
    ("cue","q",True,""),
    ("queue","q",True,""),
    ("u","q",False,"cons-init Y ≠ K"),
    ("you","q",False,""),
    ("view","q",False,"cons-init V ≠ K"),
    ("few","q",False,"cons-init F ≠ K"),

    # =================== R ===================
    ("r","r",True,""),
    ("are","r",True,""),
    ("our","r",False,"AW not in AA-equiv"),
    ("hour","r",False,""),
    ("art","r",True,"[AA,R,T]"),

    # =================== S ===================
    ("s","s",True,""),
    ("es","s",True,""),
    ("ess","s",True,""),
    ("see","s",False,"good — see → C only"),
    ("sea","s",False,""),
    ("ass","s",True,"[AE,S] AE in EH-equiv, vowel-init heard[0]=AE ✓"),

    # =================== T ===================
    ("t","t",True,""),
    ("tea","t",True,""),
    ("tee","t",True,""),
    ("d","t",False,""),
    ("dee","t",False,""),
    ("the","t",False,""),
    ("three","t",False,"cons-init TH ≠ T"),

    # =================== U ===================
    ("u","u",True,""),
    ("you","u",True,""),
    ("ewe","u",True,""),
    ("q","u",False,"K skipped to find cons; first cons of cue=K ≠ Y"),
    ("cue","u",False,""),
    ("view","u",False,"cons-init V ≠ Y"),

    # =================== W (combos handled separately) ===================
    ("double u","w",True,""),
    ("double you","w",True,""),
    ("dub","w",True,""),
    ("you","w",False,"cons-init Y ≠ D for W"),

    # =================== X ===================
    ("x","x",True,""),
    ("ex","x",True,""),
    ("eggs","x",True,"[EH,G,Z] vowel-init EH ✓ — cross-match risk but rare in kid spelling"),

    # =================== Y ===================
    ("y","y",True,""),
    ("why","y",True,""),
    ("wye","y",True,""),
    ("i","y",False,"cons-init W ≠ no consonant in [AY]"),
    ("eye","y",False,""),
    ("high","y",False,"cons-init HH ≠ W"),
    ("my","y",False,"cons-init M ≠ W"),
    ("by","y",False,""),

    # =================== Z ===================
    ("z","z",True,""),
    ("zee","z",True,""),
    ("zed","z",False,"EH not in IY-equiv (acceptable miss)"),
    ("the","z",False,""),
    ("see","z",False,"cons-init S ≠ Z"),

    # =================== Adversarial: common noise words against ALL letters ===================
    # The noise words a kid spelling probably says incidentally.
    ("the","a",False,""), ("the","b",False,""), ("the","c",False,""),
    ("the","e",False,""), ("the","f",False,""), ("the","g",False,""),
    ("the","i",False,""), ("the","j",False,""), ("the","k",False,""),
    ("the","l",False,""), ("the","m",False,""), ("the","n",False,""),
    ("the","o",False,""), ("the","p",False,""), ("the","q",False,""),
    ("the","r",False,""), ("the","s",False,""), ("the","u",False,""),
    ("the","v",False,""), ("the","w",False,""), ("the","x",False,""),
    ("the","y",False,""), ("the","z",False,""),

    # "a" as a noise word (recognizer often emits it for "uh")
    ("a","b",False,""), ("a","c",False,""), ("a","d",False,""),
    ("a","f",False,""), ("a","g",False,""), ("a","i",False,""),
    ("a","k",False,""), ("a","n",False,""),
    ("a","o",True,"AH in OW-equiv — acceptable schwa/O cross-match"),
]

# Cases whose expected result FLIPS in lenient mode (key on (word, letter)).
# Cases not listed here keep the same expectation in both modes.
LENIENT_OVERRIDES = {
    # Nasal swap: M↔N
    ("am","n"): True,    # the user's reported case
    ("n","m"):  True,    # symmetric
    ("en","m"): True,
    ("an","m"): True,    # heard "an" when expected M
    # Voicing pairs in cons-init letters
    ("pee","b"): True,
    ("p","b"):   True,
    ("be","p"):  True,
    ("b","p"):   True,
    ("bee","p"): True,
    ("dee","t"): True,
    ("d","t"):   True,
    ("tea","d"): True,
    ("tee","d"): True,
    ("t","d"):   True,
}

# Lenient-mode-only cases (don't run in strict; meaningless to express as overrides).
LENIENT_ONLY_CASES = [
    ("ham","m",True,"HH cons-init blocks; but lenient... wait, M is vowel-init letter so cons-init rule doesn't apply. ham=[HH,AE,M]; M=[EH,M] vowel-init; heard[0]=HH not in EH-equiv → False even lenient. Skip."),
]
# Drop entries whose note shows we mis-predicted them — keep only ones we expect to truly differ.
LENIENT_ONLY_CASES = []


def fmt_phon(word):
    p = PHONEMES.get(word)
    if word in W_COMBOS: return "<combo>"
    return f"[{','.join(p)}]" if p else "<not in dict>"


def main():
    global MODE
    MODE = "lenient" if "--lenient" in sys.argv else (
        "strict" if "--strict" in sys.argv else "both"
    )

    if MODE == "both":
        ok_strict = run_one("strict")
        print()
        print("=" * 78)
        print()
        ok_lenient = run_one("lenient")
        return 0 if (ok_strict and ok_lenient) else 1
    return 0 if run_one(MODE) else 1


def run_one(mode):
    global MODE
    MODE = mode
    print(f"### MODE: {mode}")
    by_letter = {}
    fails = []
    pass_count = 0
    for word, letter, strict_expect, note in CASES:
        expect = LENIENT_OVERRIDES.get((word, letter), strict_expect) if mode == "lenient" else strict_expect
        got = matches(word, letter)
        ok = got == expect
        if ok: pass_count += 1
        else: fails.append((word, letter, expect, got, note))
        by_letter.setdefault(letter, []).append((word, got, expect, ok, note))

    # Per-letter summary
    print("=" * 78)
    print(f"{'Letter':<7}{'Word':<14}{'Heard phonemes':<22}{'Got':<7}{'Expect':<8}{'Pass'}")
    print("=" * 78)
    for letter in sorted(by_letter.keys()):
        for word, got, expect, ok, _ in by_letter[letter]:
            mark = "OK" if ok else "FAIL"
            print(f"  {letter:<5}{word:<14}{fmt_phon(word):<22}{str(got):<7}{str(expect):<8}{mark}")
        print()

    print(f"[{mode}] PASS: {pass_count}  FAIL: {len(fails)}  TOTAL: {len(CASES)}")
    if fails:
        print()
        print(f"[{mode}] FAILURES (matcher disagrees with predicted expectation):")
        for word, letter, expect, got, note in fails:
            print(f"  matches({word!r:<14}, {letter!r}) = {got}, expected {expect}  | {fmt_phon(word)}  - {note}")
    return not fails


sys.exit(main())
