"""Chinese phoneme (polyphonic character) processing for TTS.

Ported from the video-podcast-maker skill. The --phonemes CLI flag points
at a JSON dict mapping words to space-separated pinyin, either tone-marked
("háng zhǎng") or numbered ("hang2 zhang3"):

    {"行长": "hang2 zhang3", "重庆": "chóng qìng"}

Keys starting with "_" are treated as comments and ignored.

Application per platform:
  azure   -> <phoneme alphabet="sapi"> SSML tags (apply_phonemes)
  minimax -> inline pinyin annotations 字(zi4)   (apply_phonemes_minimax)
  others  -> silently ignored
"""
import json


def load_phonemes(path):
    """Load a phoneme dict from a JSON file, dropping "_"-prefixed comment keys.

    Raises OSError if unreadable, ValueError if not a JSON object.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("phonemes file must be a JSON object")
    return {k: v for k, v in data.items() if not k.startswith("_")}


def pinyin_to_sapi(pinyin):
    """Convert pinyin to SAPI format with numeric tones.

    Accepts tone marks ("zhí xíng qì" -> "zhi 2 xing 2 qi 4") or numbered
    syllables ("hang2" -> "hang 2").
    """
    tone_map = {
        'ā': ('a', '1'), 'á': ('a', '2'), 'ǎ': ('a', '3'), 'à': ('a', '4'),
        'ē': ('e', '1'), 'é': ('e', '2'), 'ě': ('e', '3'), 'è': ('e', '4'),
        'ī': ('i', '1'), 'í': ('i', '2'), 'ǐ': ('i', '3'), 'ì': ('i', '4'),
        'ō': ('o', '1'), 'ó': ('o', '2'), 'ǒ': ('o', '3'), 'ò': ('o', '4'),
        'ū': ('u', '1'), 'ú': ('u', '2'), 'ǔ': ('u', '3'), 'ù': ('u', '4'),
        'ǖ': ('v', '1'), 'ǘ': ('v', '2'), 'ǚ': ('v', '3'), 'ǜ': ('v', '4'), 'ü': ('v', '5'),
    }

    syllables = pinyin.split()
    result = []

    for syllable in syllables:
        if syllable and syllable[-1].isdigit():
            result.append(f"{syllable[:-1]} {syllable[-1]}")
            continue
        tone = '5'
        converted = ''
        for char in syllable:
            if char in tone_map:
                base, t = tone_map[char]
                converted += base
                tone = t
            else:
                converted += char
        result.append(f"{converted} {tone}")

    return ' '.join(result)


def apply_phonemes(text, phoneme_dict):
    """Apply SSML phoneme tags for multi-character words (Azure SAPI alphabet).

    Longest words first, via placeholders so one word's tag can't be
    corrupted by a later substring replacement.
    """
    if not phoneme_dict:
        return text

    sorted_words = sorted(phoneme_dict.keys(), key=len, reverse=True)
    placeholders = {}
    result = text

    for i, word in enumerate(sorted_words):
        if word not in result:
            continue
        placeholder = f"__PH_{i}__"
        placeholders[placeholder] = (word, phoneme_dict[word])
        result = result.replace(word, placeholder)

    for placeholder, (word, pinyin) in placeholders.items():
        sapi_pinyin = pinyin_to_sapi(pinyin)
        phoneme_tag = f'<phoneme alphabet="sapi" ph="{sapi_pinyin}">{word}</phoneme>'
        result = result.replace(placeholder, phoneme_tag)

    return result


def apply_phonemes_minimax(text, phoneme_dict):
    """Annotate polyphonic words with MiniMax pinyin syntax: 重(chong2)庆(qing4).

    MiniMax (speech-2.x) reads a parenthesized numbered-pinyin annotation
    placed directly after a character. Each dict word is expanded to per-char
    annotations; entries whose syllable count doesn't match the character
    count are skipped (fail-safe: default pronunciation). Longest-first with
    placeholders, mirroring apply_phonemes().
    """
    if not phoneme_dict:
        return text

    sorted_words = sorted(phoneme_dict.keys(), key=len, reverse=True)
    placeholders = {}
    result = text

    for i, word in enumerate(sorted_words):
        syllables = phoneme_dict[word].split()
        if len(syllables) != len(word) or word not in result:
            continue
        placeholder = f"__PHM_{i}__"
        annotated = "".join(
            f"{char}({pinyin_to_sapi(syl).replace(' ', '')})"
            for char, syl in zip(word, syllables))
        placeholders[placeholder] = annotated
        result = result.replace(word, placeholder)

    for placeholder, annotated in placeholders.items():
        result = result.replace(placeholder, annotated)

    return result
