"""Shared lightweight text normalization for training and inference.

Carefully handles Unicode NFKC, invisible characters, file extensions, controlled
separator joining, mixed Cyrillic/Latin confusables, leetspeak, inserted digits,
and excessive character repetition without corrupting legitimate English, Russian,
or Kazakh academic vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

from .config import MAX_INPUT_LENGTH

KNOWN_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".txt", ".csv",
    ".md", ".rtf", ".odt", ".ods", ".odp", ".zip", ".rar", ".7z", ".tar", ".gz",
    ".png", ".jpg", ".jpeg", ".webp", ".svg", ".py", ".ipynb", ".java", ".cpp",
    ".c", ".js", ".ts", ".html", ".css", ".sql", ".json", ".xml", ".yaml", ".yml",
}

# Zero-width and invisible formatting characters commonly used to evade filters.
INVISIBLE_CHARS_RE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\ufeff\u00ad\u034f\u061c]"
)

# Visual homoglyphs between Cyrillic and Latin scripts.
CYR_TO_LAT = str.maketrans({
    "а": "a", "в": "b", "с": "c", "е": "e", "н": "h", "і": "i", "ї": "i",
    "к": "k", "м": "m", "о": "o", "р": "p", "т": "t", "х": "x", "у": "y",
    "ѕ": "s", "ј": "j", "ԁ": "d", "ɡ": "g", "ӏ": "l",
})

LAT_TO_CYR = str.maketrans({
    "a": "а", "b": "в", "c": "с", "e": "е", "h": "н", "k": "к", "m": "м",
    "o": "о", "p": "р", "t": "т", "x": "х", "y": "у", "u": "у",
})

# Characters unique to Cyrillic/Kazakh vs Latin to infer dominant script inside a mixed token.
LATIN_LETTER_RE = re.compile(r"[a-z]")
CYRILLIC_LETTER_RE = re.compile(r"[а-яёәіңғүұқөһ]")
CYRILLIC_UNIQUE_RE = re.compile(r"[бгджзйлпфцчшщъыьэюяёәіңғүұқөһ]")
LATIN_UNIQUE_RE = re.compile(r"[dfgijlqsuvwz]")

# Leetspeak mappings applied only in obfuscation-bearing contexts.
SYMBOL_LEET_MAP = str.maketrans({
    "@": "a", "$": "s", "!": "i", "|": "i", "€": "e", "£": "e",
    "¥": "y", "©": "c", "®": "r", "+": "t",
})

DIGIT_LEET_MAP = str.maketrans({
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "6": "g", "7": "t", "8": "b", "9": "g",
})

CYR_DIGIT_LEET_MAP = str.maketrans({
    "0": "о", "1": "и", "3": "е", "4": "а", "5": "с", "6": "б", "7": "т", "8": "в", "9": "я",
})

# Academic tokens ending in digits (Week12, CS101, Lab01, v1, v2) should keep numbers intact.
PURE_WORD_DIGITS_SUFFIX_RE = re.compile(r"^(?:[a-zа-яёәіңғүұқөһ]{2,}\d{1,4}|v\d{1,3})$")
PURE_DIGITS_RE = re.compile(r"^\d+$")
EMBEDDED_DIGITS_RE = re.compile(r"(?<=[a-zа-яёәіңғүұқөһ])\d+(?=[a-zа-яёәіңғүұқөһ])")
EMBEDDED_SYMBOLS_RE = re.compile(r"(?<=[a-zа-яёәіңғүұқөһ])[*#%^~`]+(?=[a-zа-яёәіңғүұқөһ])")
EXCESSIVE_REPEAT_RE = re.compile(r"(.)\1{2,}")
ANY_REPEAT_RE = re.compile(r"(.)\1+")
SEPARATOR_RE = re.compile(r"[\s_\-.,/\\:;()\[\]{}<>\"'+=~`]+")
SINGLE_CHAR_SEQ_RE = re.compile(
    r"(?:(?<=^)|(?<=[\s._\-]))([a-zа-яёәіңғүұқөһ@$!0-9](?:[\s._\-*]+[a-zа-яёәіңғүұқөһ@$!0-9]){2,})(?=$|[\s._\-])"
)
UPPER_REPEAT_CORE_RE = re.compile(r"[A-ZА-ЯЁӘІҢҒҮҰҚӨҺ]{4,}")


@dataclass(frozen=True)
class NormalizedText:
    """Structured multi-view representation of an input filename or title."""

    original: str
    basename: str
    stem: str
    extension: str
    raw_clean: str
    normalized: str
    deobfuscated: str
    has_invisible: bool
    has_mixed_script: bool
    has_excessive_repeat: bool
    has_leet: bool
    has_inserted_digits: bool
    has_split_chars: bool
    was_truncated: bool

    @property
    def combined_model_text(self) -> str:
        """Combined representation used by character-level ML models."""
        parts = [self.normalized]
        if self.deobfuscated and self.deobfuscated != self.normalized:
            parts.append(self.deobfuscated)
        return " | ".join(parts)

    def obfuscation_signals(self) -> dict[str, int]:
        return {
            "invisible": int(self.has_invisible),
            "mixed_script": int(self.has_mixed_script),
            "excessive_repeat": int(self.has_excessive_repeat),
            "leet": int(self.has_leet),
            "inserted_digits": int(self.has_inserted_digits),
            "split_chars": int(self.has_split_chars),
        }


def _extract_basename_and_stem(text: str) -> tuple[str, str, str]:
    """Strip directory traversal/path prefixes and separate known file extensions."""
    cleaned = text.strip().replace("\\", "/")
    basename = cleaned.rsplit("/", 1)[-1].strip() if "/" in cleaned else cleaned
    if not basename:
        basename = cleaned

    lower_base = basename.lower()
    for ext in KNOWN_EXTENSIONS:
        if lower_base.endswith(ext) and len(basename) > len(ext):
            return basename, basename[: -len(ext)], ext
    return basename, basename, ""


def _strip_invisible(text: str) -> tuple[str, bool]:
    no_zw = INVISIBLE_CHARS_RE.sub("", text)
    filtered = "".join(ch for ch in no_zw if unicodedata.category(ch) != "Cf")
    return filtered, filtered != text


def _resolve_mixed_script_token(token: str) -> tuple[str, bool]:
    has_lat = bool(LATIN_LETTER_RE.search(token))
    has_cyr = bool(CYRILLIC_LETTER_RE.search(token))
    if not (has_lat and has_cyr):
        return token, False

    has_cyr_unique = bool(CYRILLIC_UNIQUE_RE.search(token))
    has_lat_unique = bool(LATIN_UNIQUE_RE.search(token))
    if has_cyr_unique and not has_lat_unique:
        return token.translate(LAT_TO_CYR), True
    if has_lat_unique and not has_cyr_unique:
        return token.translate(CYR_TO_LAT), True

    # If ambiguous, favor the script with more characters (prefer Latin when tied).
    cyr_count = len(CYRILLIC_LETTER_RE.findall(token))
    lat_count = len(LATIN_LETTER_RE.findall(token))
    if cyr_count > lat_count:
        return token.translate(LAT_TO_CYR), True
    return token.translate(CYR_TO_LAT), True


def _normalize_token(token: str) -> tuple[str, str, bool, bool, bool, bool]:
    """Normalize a single token into (standard_norm, aggressive_deobf, mixed, repeat, leet, ins_digits)."""
    if not token:
        return "", "", False, False, False, False

    tok, is_mixed = _resolve_mixed_script_token(token)
    has_repeat = bool(EXCESSIVE_REPEAT_RE.search(tok))
    has_leet = False
    has_ins_digits = False

    # Symbol leetspeak (@, $, !, |, etc.).
    sym_mapped = tok.translate(SYMBOL_LEET_MAP)
    if sym_mapped != tok:
        has_leet = True
        tok = sym_mapped

    # Strip inline masking stars/hashes inside letters (f*ck -> fck, a#s -> as).
    de_masked = EMBEDDED_SYMBOLS_RE.sub("", tok)
    if de_masked != tok:
        has_leet = True
        tok = de_masked

    # Preserve pure numbers and clean academic suffixes (week12, cs101, assignment12).
    if PURE_DIGITS_RE.match(tok) or PURE_WORD_DIGITS_SUFFIX_RE.match(tok):
        norm = EXCESSIVE_REPEAT_RE.sub(r"\1\1", tok)
        deobf = ANY_REPEAT_RE.sub(r"\1", tok) if has_repeat else norm
        return norm, deobf, is_mixed, has_repeat, has_leet, has_ins_digits

    # Detect digits inserted inside a word (e.g., A123SS -> ass; f0ck -> fock/fck; қ0тақ -> қотақ).
    digit_map = CYR_DIGIT_LEET_MAP if CYRILLIC_LETTER_RE.search(tok) and not LATIN_LETTER_RE.search(tok) else DIGIT_LEET_MAP
    norm_tok = tok
    deobf_tok = tok
    if EMBEDDED_DIGITS_RE.search(tok):
        has_ins_digits = True
        stripped_digits = EMBEDDED_DIGITS_RE.sub("", tok)
        leet_digits = tok.translate(digit_map)
        # If there are 2+ consecutive digits inside letters (A123SS), stripping reveals the hidden word.
        if re.search(r"[a-zа-яёәіңғүұқөһ]\d{2,}[a-zа-яёәіңғүұқөһ]", tok):
            norm_tok = stripped_digits
            deobf_tok = stripped_digits
        else:
            norm_tok = leet_digits
            deobf_tok = f"{leet_digits} {stripped_digits}" if stripped_digits != leet_digits else leet_digits
        has_leet = True
    elif any(ch.isdigit() for ch in tok) and any(ch.isalpha() for ch in tok):
        # Leading/mixed digits like 4ss, 5hit, 3bat, p1zda (not clean word+suffix).
        leet_digits = tok.translate(digit_map)
        if leet_digits != tok:
            has_leet = True
            norm_tok = leet_digits
            deobf_tok = leet_digits

    # Keep natural double letters (class, pass, mass, assignment), cap 3+ repeats to 2.
    norm_tok = EXCESSIVE_REPEAT_RE.sub(r"\1\1", norm_tok)

    if has_repeat:
        # Also produce a single-collapsed variant for stretched tokens (pppAAASSSS -> pas / ppas).
        squeezed_parts = []
        for piece in deobf_tok.split():
            piece_cap2 = EXCESSIVE_REPEAT_RE.sub(r"\1\1", piece)
            piece_cap1 = EXCESSIVE_REPEAT_RE.sub(r"\1", piece)
            squeezed_parts.append(piece_cap2)
            if piece_cap1 != piece_cap2:
                squeezed_parts.append(piece_cap1)
        deobf_tok = " ".join(dict.fromkeys(squeezed_parts))
    else:
        deobf_tok = norm_tok

    # Remove leftover stray punctuation at token edges.
    norm_tok = re.sub(r"^[^a-zа-яёәіңғүұқөһ0-9]+|[^a-zа-яёәіңғүұқөһ0-9]+$", "", norm_tok)
    deobf_tok = " ".join(
        part for part in (
            re.sub(r"^[^a-zа-яёәіңғүұқөһ0-9]+|[^a-zа-яёәіңғүұқөһ0-9]+$", "", p)
            for p in deobf_tok.split()
        )
        if part
    )
    return norm_tok, deobf_tok, is_mixed, has_repeat, has_leet, has_ins_digits


def normalize_text(raw_input: str | None) -> NormalizedText:
    """Normalize a filename or study material title while preserving the original string."""
    original = "" if raw_input is None else str(raw_input)
    was_truncated = len(original) > MAX_INPUT_LENGTH
    working = original[:MAX_INPUT_LENGTH]

    basename, stem_orig, extension = _extract_basename_and_stem(working)
    stem_visible, has_invisible = _strip_invisible(stem_orig)

    # Unicode compatibility normalization (handles full-width, mathematical bold, superscripts).
    nfkc_stem = unicodedata.normalize("NFKC", stem_visible)

    # Capture stretched uppercase cores inside mixed-case stretched strings (e.g., pppAAASSSS -> ass).
    stretched_upper_hints: list[str] = []
    if EXCESSIVE_REPEAT_RE.search(nfkc_stem.casefold()):
        for match in UPPER_REPEAT_CORE_RE.finditer(nfkc_stem):
            core = match.group(0).casefold()
            if EXCESSIVE_REPEAT_RE.search(core):
                # Cap 3+ repeats to 2, and if a letter repeated 3+ at start (AAA) keep 1 too.
                cap2 = EXCESSIVE_REPEAT_RE.sub(r"\1\1", core)
                cap1 = EXCESSIVE_REPEAT_RE.sub(r"\1", core)
                # Special common pattern like AAASSSS -> ass (first run 1, trailing s run 2).
                trimmed = re.sub(r"^([a-zа-яёәіңғүұқөһ])\1+", r"\1", cap2)
                for candidate in (cap2, trimmed, cap1):
                    if len(candidate) >= 3 and candidate not in stretched_upper_hints:
                        stretched_upper_hints.append(candidate)

    folded = nfkc_stem.casefold().strip()
    raw_clean = re.sub(r"\s+", " ", folded)

    # Detect and join single-character separated obfuscations (A.S.S, A_S_S, F U C K, @ $ $).
    has_split_chars = False

    def _join_split(match: re.Match[str]) -> str:
        nonlocal has_split_chars
        segment = match.group(1)
        # Do not collapse pure numeric dates/codes like "1-2-3" or "2.0.1".
        compact = re.sub(r"[\s._\-*]+", "", segment)
        if PURE_DIGITS_RE.match(compact):
            return segment
        has_split_chars = True
        return compact

    joined_splits = SINGLE_CHAR_SEQ_RE.sub(_join_split, folded)

    # Replace remaining separators with spaces while preserving @, $, !, *, # inside tokens.
    spaced = SEPARATOR_RE.sub(" ", joined_splits).strip()
    raw_tokens = [tok for tok in spaced.split() if tok]

    norm_tokens: list[str] = []
    deobf_tokens: list[str] = []
    has_mixed_script = False
    has_excessive_repeat = False
    has_leet = False
    has_inserted_digits = False

    for token in raw_tokens:
        n_tok, d_tok, is_mixed, is_rep, is_leet, is_ins = _normalize_token(token)
        has_mixed_script = has_mixed_script or is_mixed
        has_excessive_repeat = has_excessive_repeat or is_rep
        has_leet = has_leet or is_leet
        has_inserted_digits = has_inserted_digits or is_ins
        if n_tok:
            norm_tokens.append(n_tok)
        if d_tok:
            deobf_tokens.append(d_tok)

    for hint in stretched_upper_hints:
        if hint not in deobf_tokens:
            deobf_tokens.append(hint)

    normalized = " ".join(norm_tokens)
    deobfuscated = " ".join(dict.fromkeys(" ".join(deobf_tokens).split()))

    return NormalizedText(
        original=original,
        basename=basename,
        stem=stem_orig,
        extension=extension,
        raw_clean=raw_clean,
        normalized=normalized,
        deobfuscated=deobfuscated,
        has_invisible=has_invisible,
        has_mixed_script=has_mixed_script,
        has_excessive_repeat=has_excessive_repeat,
        has_leet=has_leet,
        has_inserted_digits=has_inserted_digits,
        has_split_chars=has_split_chars,
        was_truncated=was_truncated,
    )
