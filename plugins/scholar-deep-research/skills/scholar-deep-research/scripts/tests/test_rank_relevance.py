"""B1 — relevance scoring with stopwords stripped, suffix stemming, and phrase boost.

The 0.12.x relevance was unweighted Jaccard against the question's full
token bag (stopwords included, no morphology). This test pins the three
properties of the 0.13.0 rewrite that recovered the test-run failures:

  1. Stopwords ("how", "is", "the", …) don't inflate the question
     denominator. Two papers with the same content-word overlap should
     score the same regardless of natural-language padding in the query.
  2. Suffix stemming bridges bias↔biases / evaluating↔evaluation. The
     test compares scores for a paper that uses morphologically-related
     forms vs an exactly-matching paper — they should be close.
  3. Hyphenated and quoted phrases get a +0.15 (title) / +0.05
     (abstract) bonus on top of the base overlap.

Plus the headline test-run finding: on the actual question and corpus,
the seminal Zheng paper now beats a generic "Survey on Evaluation of
LLMs" — the inversion that took the canonical paper to rank #27 in
0.12.0.
"""
from __future__ import annotations

import unittest

from rank_papers import (
    _extract_phrases,
    _normalize_tokens,
    _stem_word,
    relevance,
)


class StemmerTest(unittest.TestCase):
    def test_evaluation_family_collapses(self) -> None:
        # All four of these are the morphology pile that broke ranking
        # in 0.12.0. They should stem to the same root.
        roots = {_stem_word(w) for w in
                 ("evaluation", "evaluations", "evaluating", "evaluator")}
        self.assertEqual(len(roots), 1, f"distinct roots: {roots}")

    def test_bias_biases_collapse(self) -> None:
        self.assertEqual(_stem_word("bias"), _stem_word("biases"))

    def test_short_words_passthrough(self) -> None:
        # ≤3 chars never get stemmed — would otherwise eat real signal.
        for w in ("llm", "mt", "nlg", "rag", "of"):
            self.assertEqual(_stem_word(w), w)

    def test_min_root_keeps_bias_intact(self) -> None:
        # The -s rule's min_root_len=5 is what protects "bias" (4 chars)
        # from becoming "bia". Regression guard.
        self.assertEqual(_stem_word("bias"), "bias")


class TokenizeTest(unittest.TestCase):
    def test_stopwords_stripped(self) -> None:
        toks = _normalize_tokens("how is the LLM evaluation reliable")
        self.assertNotIn("how", toks)
        self.assertNotIn("is", toks)
        self.assertNotIn("the", toks)
        # Content words preserved (stemmed).
        self.assertIn("llm", toks)
        self.assertIn("reliable", toks)

    def test_no_single_char_tokens(self) -> None:
        toks = _normalize_tokens("a b c X y z LLM")
        # Single-char tokens are dropped (length filter inside _normalize_tokens).
        self.assertEqual(toks, {"llm"})


class PhraseExtractTest(unittest.TestCase):
    def test_hyphenated_phrase_picked_up(self) -> None:
        phrases = _extract_phrases("study of LLM-as-a-judge bias")
        self.assertIn("llm-as-a-judge", phrases)

    def test_quoted_phrase_picked_up(self) -> None:
        phrases = _extract_phrases('LLM judges and "position bias" mitigation')
        self.assertIn("position bias", phrases)

    def test_short_phrases_dropped(self) -> None:
        # Phrases ≤3 chars contribute noise, not signal.
        phrases = _extract_phrases('"ab" "cd" "good phrase"')
        self.assertNotIn("ab", phrases)
        self.assertIn("good phrase", phrases)


class RelevanceTest(unittest.TestCase):
    QUESTION = (
        "How reliable is the LLM-as-a-judge paradigm for evaluating "
        "generative model outputs, and what biases, failure modes, and "
        "mitigation strategies have been identified?"
    )

    def test_zheng_outranks_generic_llm_survey(self) -> None:
        """The headline regression: Zheng-style paper > generic LLM survey.

        In 0.12.0 the generic survey scored ~0.25 vs Zheng's ~0.50, but
        with β=0.3 on log10(citations) the survey's ~2300 cites pushed
        it ahead. With stemming + phrase boost, the relevance signal
        itself separates them by enough that even balanced weights can't
        invert it.
        """
        zheng = {
            "title": "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena",
            "abstract": (
                "We examine the usage and limitations of LLM-as-a-judge, "
                "including position, verbosity, and self-enhancement biases. "
                "Our results reveal strong LLM judges like GPT-4 can match "
                "crowdsourced human preferences over 80% of the time."
            ),
        }
        generic_survey = {
            "title": "A Survey on Evaluation of Large Language Models",
            "abstract": (
                "This paper surveys evaluation approaches for large language "
                "models including benchmarks, automatic metrics, and human "
                "evaluation across many tasks."
            ),
        }
        zheng_score = relevance(self.QUESTION, zheng)
        survey_score = relevance(self.QUESTION, generic_survey)
        self.assertGreater(
            zheng_score, survey_score,
            f"Zheng ({zheng_score:.3f}) should outscore generic survey "
            f"({survey_score:.3f}) — was inverted in 0.12.0.",
        )
        # And the gap should be meaningful, not just hairline. With the
        # phrase boost Zheng should be ≥3x the survey's relevance.
        self.assertGreater(
            zheng_score, survey_score * 2,
            f"gap too small: zheng={zheng_score:.3f} survey={survey_score:.3f}",
        )

    def test_phrase_in_title_beats_phrase_in_abstract(self) -> None:
        title_match = {
            "title": "On LLM-as-a-judge methods",
            "abstract": "Some abstract text here.",
        }
        abstract_match = {
            "title": "On evaluation methods",
            "abstract": "We discuss LLM-as-a-judge in section 3.",
        }
        # Same content tokens, but the phrase appears in different fields.
        # Title hit is +0.15, abstract hit is +0.05 → title should win.
        self.assertGreater(
            relevance(self.QUESTION, title_match),
            relevance(self.QUESTION, abstract_match),
        )

    def test_morphology_does_not_lose_signal(self) -> None:
        # Same paper, two abstracts: one uses the question's exact word
        # forms, the other uses related forms. Score gap should be tiny
        # because the stemmer collapses them.
        exact = {"title": "T", "abstract": "bias evaluation generative"}
        morph = {"title": "T", "abstract": "biases evaluating generative"}
        gap = abs(relevance(self.QUESTION, exact)
                  - relevance(self.QUESTION, morph))
        self.assertLess(gap, 0.05,
                        f"stemmer didn't bridge morphology gap: {gap:.3f}")

    def test_empty_paper_returns_zero(self) -> None:
        self.assertEqual(relevance(self.QUESTION, {}), 0.0)
        self.assertEqual(relevance(self.QUESTION, {"title": "", "abstract": ""}),
                         0.0)

    def test_score_clipped_at_one(self) -> None:
        # Many phrase hits should not push the score over 1.0.
        rich = {
            "title": "LLM-as-a-judge: position bias and verbosity bias",
            "abstract": ("LLM-as-a-judge bias evaluation generative model "
                         "outputs reliable mitigation strategies failure modes "
                         "judge paradigm"),
        }
        score = relevance(self.QUESTION, rich)
        self.assertLessEqual(score, 1.0)
        self.assertGreater(score, 0.5)  # …but should still be solidly high


if __name__ == "__main__":
    unittest.main()
