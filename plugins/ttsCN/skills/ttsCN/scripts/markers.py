"""Backend-neutral expressiveness markers for narration scripts.

Same marker spec as the video-podcast-maker skill so both repos speak
the same language. Input text may contain:
  [PAUSE:0.8]     — a pause in seconds (0.01-99.99)
  (chuckle) etc.  — MiniMax sound tags: laughs, chuckle, sighs, breath,
                    inhale, exhale, coughs (speech-2.8 models only)

Rendering policy per platform (applied in tts.py before synthesis):
  azure   -> [PAUSE:x] becomes <break time="xs"/> (SSML); sound tags stripped
  minimax -> [PAUSE:x] becomes <#x#>; sound tags kept only on speech-2.8
  others  -> all markers stripped (they would be spoken aloud)

[PAUSE:x] contains a '.' which the sentence chunker treats as a boundary —
protect_pauses()/restore_pauses() swap the dot out around chunk_text().
"""
import re

PAUSE_RE = re.compile(r"\[PAUSE:(\d{1,2}(?:\.\d{1,2})?)\]")
# Dot swapped for 'p' so the chunker never splits inside a marker
_PROTECTED_PAUSE_RE = re.compile(r"\[PAUSE:(\d{1,2}(?:p\d{1,2})?)\]")

SOUND_TAGS = ("laughs", "chuckle", "sighs", "breath", "inhale", "exhale", "coughs")
SOUND_TAG_RE = re.compile(r"\((?:%s)\)" % "|".join(SOUND_TAGS))


def protect_pauses(text):
    """Make [PAUSE:x] chunker-safe ('.' -> 'p'). Inverse: restore_pauses."""
    return PAUSE_RE.sub(lambda m: "[PAUSE:%s]" % m.group(1).replace(".", "p"), text)


def restore_pauses(text):
    return _PROTECTED_PAUSE_RE.sub(
        lambda m: "[PAUSE:%s]" % m.group(1).replace("p", "."), text)


def strip_markers(text):
    """Remove all markers — for platforms that would speak them aloud."""
    text = PAUSE_RE.sub("", text)
    return SOUND_TAG_RE.sub("", text)


def render_markers(text, target):
    """Render markers for a synthesis target.

    target: 'ssml'    — Azure: pauses -> <break/>, sound tags stripped
            'minimax' — pauses -> <#x#>, sound tags kept (speech-2.8)
            'plain'   — everything stripped
    """
    if target == "ssml":
        text = PAUSE_RE.sub(lambda m: '<break time="%ss"/>' % m.group(1), text)
        return SOUND_TAG_RE.sub("", text)
    if target == "minimax":
        return PAUSE_RE.sub(lambda m: "<#%s#>" % m.group(1), text)
    return strip_markers(text)
