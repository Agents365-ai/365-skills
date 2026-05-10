"""P2.10 — citation-chase filter drops metadata noise at OpenAlex ingest.

The 0.13.0 test run pulled "Publisher's Note" with 274 577 cites into
the corpus via the citation chase — a journal back-matter pointer
referenced by every issue. This test pins the v0.13.3 filter that drops
five well-defined garbage classes at ingest time and tallies them by
reason for audit:

  - type=erratum / correction / paratext / peer-review → drop
  - cited_by_count > 100 000                            → drop
  - editorial / letter / news / regular journal-article → KEEP
    (those are sometimes useful and the agent will judge in Phase 2)

Tests work at the function level (`_drop_reason`) so they don't need
network access or a fake OpenAlex backend.
"""
from __future__ import annotations

import unittest

from build_citation_graph import _drop_reason


class DropReasonTest(unittest.TestCase):
    def test_erratum_dropped(self) -> None:
        self.assertEqual(_drop_reason({"type": "erratum"}), "type_erratum")

    def test_correction_dropped(self) -> None:
        self.assertEqual(_drop_reason({"type": "correction"}),
                         "type_correction")

    def test_paratext_dropped(self) -> None:
        self.assertEqual(_drop_reason({"type": "paratext"}),
                         "type_paratext")

    def test_peer_review_dropped(self) -> None:
        # Hyphen in OpenAlex's "peer-review" type → underscore in our
        # reason code so JSON consumers don't have to quote it.
        self.assertEqual(_drop_reason({"type": "peer-review"}),
                         "type_peer_review")

    def test_outlier_citations_dropped(self) -> None:
        # The exact "Publisher's Note 274K cites" pattern from the
        # 0.13.0 test run.
        self.assertEqual(
            _drop_reason({"type": "article", "cited_by_count": 274_577}),
            "outlier_citations",
        )

    def test_outlier_threshold_boundary(self) -> None:
        # 100 000 exactly → kept (boundary inclusive on the keep side).
        self.assertIsNone(
            _drop_reason({"type": "article", "cited_by_count": 100_000}))
        # 100 001 → dropped.
        self.assertEqual(
            _drop_reason({"type": "article", "cited_by_count": 100_001}),
            "outlier_citations",
        )

    def test_normal_article_kept(self) -> None:
        # Most-cited Nature paper-type record at 50K cites → kept.
        self.assertIsNone(
            _drop_reason({"type": "article", "cited_by_count": 50_000}))

    def test_editorial_kept(self) -> None:
        # Deliberately ambiguous types (editorial / letter / news) are
        # NOT in the drop set — Phase 2 ranking decides.
        self.assertIsNone(_drop_reason({"type": "editorial"}))
        self.assertIsNone(_drop_reason({"type": "letter"}))
        self.assertIsNone(_drop_reason({"type": "news"}))

    def test_book_chapter_kept(self) -> None:
        self.assertIsNone(_drop_reason({"type": "book-chapter"}))
        self.assertIsNone(_drop_reason({"type": "review"}))

    def test_missing_type_kept(self) -> None:
        # A record with no type at all should not be dropped — that
        # would be too aggressive on older or partially-indexed papers.
        self.assertIsNone(_drop_reason({"cited_by_count": 100}))
        self.assertIsNone(_drop_reason({}))

    def test_type_case_insensitive(self) -> None:
        self.assertEqual(_drop_reason({"type": "Erratum"}), "type_erratum")
        self.assertEqual(_drop_reason({"type": "ERRATUM"}), "type_erratum")

    def test_outlier_overrides_kept_type(self) -> None:
        # An "article" with absurd citations should still be dropped.
        self.assertEqual(
            _drop_reason({"type": "article", "cited_by_count": 999_999}),
            "outlier_citations",
        )


if __name__ == "__main__":
    unittest.main()
