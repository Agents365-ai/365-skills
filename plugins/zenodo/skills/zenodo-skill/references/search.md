# Zenodo Search Reference

`GET /api/records` — public, no auth needed for open records.

## Parameters

| Param | Notes |
|---|---|
| `q` | Elasticsearch query string |
| `size` | Results per page (default 10, max 10000 via pagination) |
| `page` | Page number |
| `sort` | `bestmatch` (default), `mostrecent`, `-mostrecent`, `version` |
| `status` | `draft` or `published` (auth only) |
| `all_versions` | `true` to include all versions, otherwise only latest |
| `communities` | community identifier |
| `type` | resource type filter |
| `subtype` | resource subtype |
| `bounds` | geographic bounding box `lon1,lat1,lon2,lat2` |
| `custom` | custom field filter |

## Query syntax (Elasticsearch)

```
# free text
q=climate model

# fielded
q=title:"sea level"
q=creators.name:"Doe, Jane"
q=resource_type.type:dataset
q=communities:zenodo
q=keywords:transformer
q=doi:10.5281/zenodo.1234567

# boolean
q=climate AND (ocean OR atmosphere) NOT model
q=+climate -model

# range
q=publication_date:[2024-01-01 TO 2024-12-31]

# wildcard / fuzzy
q=transform*
q=climate~
```

## Examples

```bash
# 10 most recent datasets about "single cell"
curl -sS "$ZENODO_BASE/records?q=resource_type.type:dataset+AND+single+cell&sort=mostrecent&size=10"

# All records by a specific ORCID
curl -sS "$ZENODO_BASE/records?q=creators.orcid:0000-0002-1825-0097&size=50"

# Records in a community
curl -sS "$ZENODO_BASE/records?q=communities:biosyslit"

# Single record by id
curl -sS "$ZENODO_BASE/records/1234567"
```

Response shape: `{"hits": {"total": N, "hits": [...records]}, "links": {"self", "next", "prev"}}`. Each record has `id`, `doi`, `metadata`, `files`, `links.self_html`, `stats`.
