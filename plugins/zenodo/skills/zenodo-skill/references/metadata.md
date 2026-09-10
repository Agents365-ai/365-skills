# Zenodo Deposition Metadata Reference

Metadata is set via `PUT /deposit/depositions/{id}` with body `{"metadata": {...}}`.

## Required fields

| Field | Type | Notes |
|---|---|---|
| `upload_type` | string | One of the values below |
| `title` | string | |
| `creators` | array | At least one; each `{name, affiliation?, orcid?, gnd?}`. `name` is `Family, Given` |
| `description` | string | HTML allowed |

## upload_type values

`publication`, `poster`, `presentation`, `dataset`, `image`, `video`, `software`, `lesson`, `physicalobject`, `other`

## Conditionally required

| Condition | Required field | Values |
|---|---|---|
| `upload_type == "publication"` | `publication_type` | `annotationcollection`, `book`, `section`, `conferencepaper`, `datamanagementplan`, `article`, `patent`, `preprint`, `deliverable`, `milestone`, `proposal`, `report`, `softwaredocumentation`, `taxonomictreatment`, `technicalnote`, `thesis`, `workingpaper`, `other` |
| `upload_type == "image"` | `image_type` | `figure`, `plot`, `drawing`, `diagram`, `photo`, `other` |
| `access_right == "embargoed"` | `embargo_date` | ISO8601 date |
| `access_right == "restricted"` | `access_conditions` | string (HTML allowed) |

## Optional but commonly used

| Field | Type | Notes |
|---|---|---|
| `publication_date` | string | ISO8601, defaults to today |
| `access_right` | string | `open` (default), `embargoed`, `restricted`, `closed` |
| `license` | string | Required when access is open/embargoed. Defaults to `cc-zero` for datasets, `cc-by` for everything else. Use SPDX-style id, e.g. `cc-by-4.0`, `mit`, `apache-2.0`, `gpl-3.0` |
| `doi` | string | Pre-reserved or external DOI. Omit to let Zenodo mint one |
| `keywords` | array of strings | |
| `notes` | string | Additional notes (HTML allowed) |
| `version` | string | Free-form, e.g. `v1.2.0` |
| `language` | string | ISO 639-3 code, e.g. `eng` |
| `communities` | array | `[{"identifier": "zenodo"}]` — submission requires community curator approval |
| `grants` | array | `[{"id": "10.13039/501100000780::283595"}]` — funder DOI :: grant id |
| `related_identifiers` | array | `[{"identifier": "10.1234/foo", "relation": "isSupplementTo", "resource_type": "publication-article"}]` |
| `references` | array of strings | Bibliographic references |
| `contributors` | array | Like creators, plus `type` (e.g. `Editor`, `DataCurator`, `Researcher`) |
| `subjects` | array | `[{"term": "...", "identifier": "...", "scheme": "url"}]` |
| `locations` | array | `[{"place": "...", "lat": 0.0, "lon": 0.0, "description": "..."}]` |
| `dates` | array | `[{"start": "...", "end": "...", "type": "Collected", "description": "..."}]` |
| `method` | string | Methodology (HTML allowed) |

## Relation values for `related_identifiers`

`isCitedBy`, `cites`, `isSupplementTo`, `isSupplementedBy`, `isContinuedBy`, `continues`, `isDescribedBy`, `describes`, `hasMetadata`, `isMetadataFor`, `isNewVersionOf`, `isPreviousVersionOf`, `isPartOf`, `hasPart`, `isReferencedBy`, `references`, `isDocumentedBy`, `documents`, `isCompiledBy`, `compiles`, `isVariantFormOf`, `isOriginalFormof`, `isIdenticalTo`, `isAlternateIdentifier`, `isReviewedBy`, `reviews`, `isDerivedFrom`, `isSourceOf`, `requires`, `isRequiredBy`, `isObsoletedBy`, `obsoletes`

## Full dataset example

```json
{
  "metadata": {
    "title": "Global temperature anomalies 1880-2024",
    "upload_type": "dataset",
    "publication_date": "2026-04-07",
    "description": "<p>Monthly global mean surface temperature anomalies derived from ...</p>",
    "creators": [
      {"name": "Doe, Jane", "affiliation": "Example University", "orcid": "0000-0002-1825-0097"}
    ],
    "access_right": "open",
    "license": "cc-by-4.0",
    "keywords": ["climate", "temperature", "global warming"],
    "version": "v1.0.0",
    "language": "eng",
    "related_identifiers": [
      {"identifier": "10.1038/s41586-020-2649-2", "relation": "isSupplementTo", "resource_type": "publication-article"}
    ]
  }
}
```

## Software release example

```json
{
  "metadata": {
    "title": "myproject v1.2.0",
    "upload_type": "software",
    "description": "<p>Release 1.2.0 of myproject. See CHANGELOG.</p>",
    "creators": [{"name": "Doe, Jane", "affiliation": "Example University"}],
    "license": "mit",
    "version": "1.2.0",
    "related_identifiers": [
      {"identifier": "https://github.com/me/myproject/tree/v1.2.0", "relation": "isSupplementTo", "resource_type": "software"}
    ]
  }
}
```
