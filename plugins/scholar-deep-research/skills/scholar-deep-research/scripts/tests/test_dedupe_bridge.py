"""Bridge pass for preprint/published doubles in dedupe_papers.py.

Pins the two real-world misses found by scholar-deep-research's own
end-to-end test:

  - CELLxGENE preprint (10.1101/2023.10.30.563174,
    "CZ CELL×GENE Discover: A single-cell data platform...")
    vs published NAR (10.1093/nar/gkae1142,
    "CZ CELLxGENE Discover: a single-cell data platform...").
    Differs by '×' vs 'x' (Unicode) and capitalization.

  - Nicheformer preprint (10.1101/2024.04.15.589472,
    "Nicheformer: a foundation model for single-cell and spatial omics")
    vs Nature Methods (10.1038/s41592-025-02814-z,
    same title with trailing period).

Without the bridge pass both pairs ended up as separate "deep tier"
selections in Phase 2 because the primary cluster key is the DOI.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dedupe_papers import (  # noqa: E402
    _bridge_preprint_clusters,
    _is_preprint_doi,
    _title_similar,
    cluster_key,
)
from _helpers import init_state, run_script  # noqa: E402


def _paper(*, doi: str | None = None, title: str = "",
           authors: list[str] | None = None, year: int | None = None,
           citations: int = 0, openalex_id: str | None = None,
           **extra) -> dict:
    p = {
        "id": extra.pop(
            "id",
            f"doi:{doi}" if doi else f"openalex:{openalex_id}",
        ),
        "doi": doi,
        "title": title,
        "authors": authors or [],
        "year": year,
        "abstract": f"abstract for {title[:30]}",
        "venue": "Test Venue",
        "citations": citations,
        "source": ["openalex"],
        "url": None,
        "pdf_url": None,
        "openalex_id": openalex_id,
    }
    p.update(extra)
    return p


def _seed_clusters(papers: list[dict]) -> dict[str, list[dict]]:
    clusters: dict[str, list[dict]] = {}
    for p in papers:
        clusters.setdefault(cluster_key(p), []).append(p)
    return clusters


class IsPreprintDoiTest(unittest.TestCase):
    def test_biorxiv(self) -> None:
        self.assertTrue(_is_preprint_doi("10.1101/2024.04.15.589472"))

    def test_arxiv(self) -> None:
        self.assertTrue(_is_preprint_doi("10.48550/arxiv.2504.16956"))

    def test_published(self) -> None:
        self.assertFalse(_is_preprint_doi("10.1038/s41592-025-02814-z"))
        self.assertFalse(_is_preprint_doi("10.1093/nar/gkae1142"))

    def test_none(self) -> None:
        self.assertFalse(_is_preprint_doi(None))
        self.assertFalse(_is_preprint_doi(""))


class TitleSimilarTest(unittest.TestCase):
    def test_punctuation_only_diff(self) -> None:
        a = "nicheformer a foundation model for single cell and spatial omics"
        # trailing period in raw → identical after normalize_title, but
        # callers pass already-normalized strings; pin the threshold for
        # near-identical strings.
        self.assertTrue(_title_similar(a, a))

    def test_one_char_substitution(self) -> None:
        a = "cz cellxgene discover a single cell data platform"
        b = "cz cell gene discover a single cell data platform"
        self.assertTrue(_title_similar(a, b))

    def test_genuinely_different(self) -> None:
        a = "scgpt toward building a foundation model for single cell"
        b = "geneformer transfer learning enables predictions in network biology"
        self.assertFalse(_title_similar(a, b))

    def test_empty_inputs(self) -> None:
        self.assertFalse(_title_similar("", "x"))
        self.assertFalse(_title_similar("x", ""))


class BridgePreprintClustersTest(unittest.TestCase):

    def test_cellxgene_preprint_bridges_to_published(self) -> None:
        preprint = _paper(
            id="doi:10.1101/2023.10.30.563174",
            doi="10.1101/2023.10.30.563174",
            title="CZ CELL×GENE Discover: A single-cell data platform "
                  "for scalable exploration",
            authors=["CZI Cell Science Program"],
            year=2023,
        )
        published = _paper(
            id="doi:10.1093/nar/gkae1142",
            doi="10.1093/nar/gkae1142",
            title="CZ CELLxGENE Discover: a single-cell data platform "
                  "for scalable exploration",
            authors=["CZI Cell Science Program"],
            year=2024,
            citations=273,  # bumps populated() → tiebreaker
        )
        clusters = _seed_clusters([preprint, published])
        self.assertEqual(len(clusters), 2)  # 2 DOI clusters before bridge
        bridges = _bridge_preprint_clusters(clusters)
        self.assertEqual(bridges, 1)
        self.assertEqual(len(clusters), 1)
        # Published-DOI cluster wins; preprint key is gone.
        self.assertIn("doi:10.1093/nar/gkae1142",
                      [k.lower() for k in clusters.keys()])
        self.assertNotIn("doi:10.1101/2023.10.30.563174",
                         [k.lower() for k in clusters.keys()])
        # Both members preserved in the surviving cluster for merge() later.
        survivor = next(iter(clusters.values()))
        self.assertEqual(len(survivor), 2)

    def test_nicheformer_preprint_bridges_to_published(self) -> None:
        preprint = _paper(
            id="doi:10.1101/2024.04.15.589472",
            doi="10.1101/2024.04.15.589472",
            title="Nicheformer: a foundation model for single-cell "
                  "and spatial omics",
            authors=["Anna C. Schaar"],
            year=2024,
        )
        published = _paper(
            id="doi:10.1038/s41592-025-02814-z",
            doi="10.1038/s41592-025-02814-z",
            title="Nicheformer: a foundation model for single-cell "
                  "and spatial omics.",
            authors=["Anna C. Schaar"],
            year=2025,
            citations=39,
        )
        clusters = _seed_clusters([preprint, published])
        bridges = _bridge_preprint_clusters(clusters)
        self.assertEqual(bridges, 1)
        self.assertEqual(len(clusters), 1)

    def test_distinct_papers_not_bridged(self) -> None:
        a = _paper(
            id="doi:10.1038/a", doi="10.1038/a",
            title="scGPT toward building a foundation model for single cell",
            authors=["Bo Wang"], year=2024,
        )
        b = _paper(
            id="doi:10.1038/b", doi="10.1038/b",
            title="scGPT-spatial continual pretraining for spatial",
            authors=["Bo Wang"], year=2025,
        )
        clusters = _seed_clusters([a, b])
        bridges = _bridge_preprint_clusters(clusters)
        # Same first author, near years, but title similarity is well
        # under threshold — must not collapse.
        self.assertEqual(bridges, 0)
        self.assertEqual(len(clusters), 2)

    def test_year_gap_too_wide_blocks_bridge(self) -> None:
        old = _paper(
            id="doi:10.1101/old", doi="10.1101/old",
            title="Nicheformer a foundation model for single cell and spatial",
            authors=["Anna C. Schaar"], year=2018,
        )
        new = _paper(
            id="doi:10.1038/new", doi="10.1038/new",
            title="Nicheformer a foundation model for single cell and spatial",
            authors=["Anna C. Schaar"], year=2025,
        )
        clusters = _seed_clusters([old, new])
        bridges = _bridge_preprint_clusters(clusters)
        # |2025-2018| = 7 > 2 → refuse to bridge even though title+author match.
        self.assertEqual(bridges, 0)
        self.assertEqual(len(clusters), 2)

    def test_short_title_skipped(self) -> None:
        # Two-word titles can collide spuriously; bridge requires len>=20.
        a = _paper(id="doi:10.1101/x", doi="10.1101/x",
                        title="Editorial Reply",
                        authors=["Same Author"], year=2024)
        b = _paper(id="doi:10.1038/x", doi="10.1038/x",
                        title="Editorial Reply",
                        authors=["Same Author"], year=2024)
        clusters = _seed_clusters([a, b])
        bridges = _bridge_preprint_clusters(clusters)
        self.assertEqual(bridges, 0)


class DedupeCLIBridgeIntegrationTest(unittest.TestCase):
    """End-to-end via the dedupe_papers.py CLI on a state file containing
    the CELLxGENE preprint/published pair. Verifies the response envelope
    surfaces the new `preprint_bridges` count.
    """
    def test_cli_reports_bridges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "s.json"
            init_state(state)
            # Inject the two papers directly.
            s = json.loads(state.read_text())
            s["papers"] = {
                "doi:10.1101/2023.10.30.563174": _paper(
                    id="doi:10.1101/2023.10.30.563174",
                    doi="10.1101/2023.10.30.563174",
                    title="CZ CELL×GENE Discover: A single-cell data platform "
                          "for scalable exploration",
                    authors=["CZI Cell Science Program"],
                    year=2023,
                ),
                "doi:10.1093/nar/gkae1142": _paper(
                    id="doi:10.1093/nar/gkae1142",
                    doi="10.1093/nar/gkae1142",
                    title="CZ CELLxGENE Discover: a single-cell data platform "
                          "for scalable exploration",
                    authors=["CZI Cell Science Program"],
                    year=2024,
                    citations=273,
                ),
            }
            state.write_text(json.dumps(s, indent=2))

            env = run_script("dedupe_papers.py", ["--state", str(state)])
            self.assertEqual(env["data"]["before"], 2)
            self.assertEqual(env["data"]["after"], 1)
            self.assertEqual(env["data"]["preprint_bridges"], 1)


if __name__ == "__main__":
    unittest.main()
