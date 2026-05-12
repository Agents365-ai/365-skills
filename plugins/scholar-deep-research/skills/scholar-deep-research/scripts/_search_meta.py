"""Per-source metadata schema for the federated search family.

Each `search_*.py` exposes a module-level `SOURCE_META` dict matching the
schema below. `list_sources.py` aggregates them so an orchestrator can
route by capability — "which source covers preprints under 24h old?",
"which one needs an API key?" — without grepping every script's header.

The schema is intentionally narrow. Add fields only when an actual
decision-maker needs them; otherwise it's just metadata-for-its-own-sake.

Fields:

  name                       Stable lowercase identifier matching the
                             search_<name>.py filename (and the `source:`
                             field on every paper this source emits).

  domain                     Broad subject area. One of DOMAINS below.

  index_type                 What kind of index this source is. One of
                             INDEX_TYPES — drives expectations about
                             freshness, completeness, and venue diversity.

  covers                     Record types this source returns (papers,
                             authors, venues, datasets, web_pages, ...).
                             Free-form list — agents grep it.

  lookup_by                  ID/key types this source accepts as input
                             (doi, arxiv_id, pmid, dblp_id, title, ...).

  freshness_lag_days         Typical days between a record's existence
                             upstream and its appearance in this index.
                             0 = real-time; arxiv/biorxiv ≈ 1; openalex
                             ≈ 7; crossref ≈ 14.

  rate_limit_qps_polite      Recommended sustained query rate when
                             behaving politely (with email/key where
                             applicable). Lower bound — actual ceilings
                             often higher.

  auth                       Authentication requirement. One of AUTH_KINDS.

  needs_relevance_filter     True when results require LLM post-filtering
                             because the source returns broad/web matches
                             (e.g., exa). False for narrowly-scoped
                             academic indexes.

  language_scope             Primary languages covered, ISO-639-1.
                             ["en"] for English-dominant indexes,
                             ["en","zh","ja",...] for multilingual.
"""
from __future__ import annotations

from typing import TypedDict

# Stable vocabularies. Extend these (never shrink) when adding a new
# source that needs a new value — agents may have cached the schema.
DOMAINS = (
    "academic",         # broad academic / multi-field aggregators
    "preprint",         # generic preprint server
    "bio_preprint",     # life-sci preprint (biorxiv, medrxiv)
    "medical",          # medical literature (pubmed)
    "cs_academic",      # CS-focused academic (dblp)
    "general",          # web / non-academic
)

INDEX_TYPES = (
    "metadata_aggregator",   # crosslinks DOIs across publishers (openalex, crossref)
    "preprint_server",       # publishes directly (arxiv, biorxiv)
    "publisher_api",         # specific publisher's API (none currently)
    "subject_aggregator",    # subject-scoped aggregator (pubmed, dblp)
    "web_search",            # general web / semantic search (exa)
)

AUTH_KINDS = (
    "none",
    "polite_email_optional",   # email in query string raises politeness pool
    "ncbi_key_optional",       # NCBI api key raises rate ceiling
    "api_key_required",        # call won't work without a key
)


class SourceMeta(TypedDict):
    """The exact shape every SOURCE_META dict must match."""
    name: str
    domain: str
    index_type: str
    covers: list[str]
    lookup_by: list[str]
    freshness_lag_days: int
    rate_limit_qps_polite: float
    auth: str
    needs_relevance_filter: bool
    language_scope: list[str]


def validate_source_meta(meta: dict) -> list[str]:
    """Return a list of human-readable validation errors.

    Empty list means valid. Used by `list_sources.py` to surface
    misconfigured sources via the envelope's `validation_warnings`
    field instead of crashing the whole list.
    """
    errors: list[str] = []
    required = set(SourceMeta.__annotations__.keys())
    missing = required - set(meta.keys())
    for field in sorted(missing):
        errors.append(f"missing field: {field}")
    if (d := meta.get("domain")) is not None and d not in DOMAINS:
        errors.append(
            f"domain must be one of {DOMAINS}; got {d!r}"
        )
    if (t := meta.get("index_type")) is not None and t not in INDEX_TYPES:
        errors.append(
            f"index_type must be one of {INDEX_TYPES}; got {t!r}"
        )
    if (a := meta.get("auth")) is not None and a not in AUTH_KINDS:
        errors.append(
            f"auth must be one of {AUTH_KINDS}; got {a!r}"
        )
    # Cheap type checks — catches dict literals that accidentally use
    # strings instead of lists.
    for list_field in ("covers", "lookup_by", "language_scope"):
        if list_field in meta and not isinstance(meta[list_field], list):
            errors.append(
                f"{list_field} must be a list; got {type(meta[list_field]).__name__}"
            )
    return errors
