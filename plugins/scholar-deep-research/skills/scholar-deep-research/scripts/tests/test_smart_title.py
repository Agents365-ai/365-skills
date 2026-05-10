"""P2.8 — `_smart_title_case` preserves acronyms, mixed case, and function words.

The 0.12.x H1 generator title-cased the slug, which produced
"How Reliable Is The Llm As: A Literature Review" — destroying the LLM
acronym and chopping at the colon. The 0.13.0 rewrite preserves:

  - All-caps acronyms (LLM, MT, GPT, RAG, NLG, RLHF)
  - Mixed-case identifiers the author chose deliberately (AlpacaEval,
    ChatGPT, OpenAI)
  - Function words (a, the, in, of, as) stay lowercase mid-sentence
  - Function words inside hyphenated phrases (LLM-as-a-Judge)

Plus: trailing punctuation stripped, first word always capitalised
even if it's a function word, no truncation at colons.
"""
from __future__ import annotations

import unittest

from render_report import _smart_title_case


class SmartTitleCaseTest(unittest.TestCase):
    def test_preserves_all_caps_acronym(self) -> None:
        # The headline regression: LLM stays LLM, not "Llm".
        out = _smart_title_case("how reliable is the LLM-as-a-judge paradigm")
        self.assertIn("LLM", out)
        self.assertNotIn("Llm", out)

    def test_function_words_stay_lower_in_hyphens(self) -> None:
        out = _smart_title_case("LLM-as-a-judge methods")
        self.assertIn("LLM-as-a-Judge", out)

    def test_first_word_always_capitalised(self) -> None:
        out = _smart_title_case("the role of evaluation")
        self.assertTrue(out.startswith("The "),
                        f"expected 'The ...', got: {out!r}")

    def test_mid_sentence_function_words_lower(self) -> None:
        out = _smart_title_case("comparison of methods")
        self.assertIn(" of ", out)
        self.assertNotIn(" Of ", out)

    def test_mixed_case_identifier_preserved(self) -> None:
        # AlpacaEval, ChatGPT — author capitalisation is intentional.
        out = _smart_title_case("comparison of AlpacaEval and ChatGPT")
        self.assertIn("AlpacaEval", out)
        self.assertIn("ChatGPT", out)

    def test_multi_acronym_question(self) -> None:
        out = _smart_title_case("MT-Bench vs Chatbot Arena vs G-Eval")
        self.assertIn("MT-Bench", out)
        self.assertIn("Chatbot Arena", out)
        self.assertIn("G-Eval", out)

    def test_trailing_punctuation_stripped(self) -> None:
        for q in ("what is X?", "what is X.", "what is X!"):
            out = _smart_title_case(q)
            self.assertFalse(out.endswith(("?", ".", "!")),
                             f"trailing punct survived: {out!r}")

    def test_hyphenated_compound_at_start(self) -> None:
        # Even at position 0 the hyphenated phrase capitalises the first
        # subtoken; later subtokens follow the function-word rule.
        out = _smart_title_case("LLM-as-a-judge is reliable")
        self.assertTrue(out.startswith("LLM-as-a-Judge"),
                        f"unexpected: {out!r}")

    def test_empty_or_none_returns_report_default(self) -> None:
        self.assertEqual(_smart_title_case(""), "Report")
        self.assertEqual(_smart_title_case("   "), "Report")
        self.assertEqual(_smart_title_case(None), "Report")  # type: ignore[arg-type]

    def test_glp1_style_alphanumeric_preserved(self) -> None:
        out = _smart_title_case("efficacy of GLP-1 receptor agonists")
        self.assertIn("GLP-1", out)


if __name__ == "__main__":
    unittest.main()
