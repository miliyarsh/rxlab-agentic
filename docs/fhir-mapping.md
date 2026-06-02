# Analyzer → FHIR Mapping

> Documents how the Analyzer's output is mapped to FHIR R4 resources by the `fhir_composer` agent (C7/C8).

## Output container

A FHIR R4 `Bundle` with `type = "collection"`. The bundle's `entry[]` carries the resources below. Written to `s3://<reports-bucket>/<job_id>/bundle.json` with SSE-KMS.

## Resources

| Analyzer field | FHIR resource | Implementation notes |
| --- | --- | --- |
| `calls[].gene` + `calls[].genotype` | `Observation` | LOINC `81239-4` (genotype display); gene stored in `component.code.text`, genotype in `component.valueString`. |
| `calls[].phenotype` | `Observation` (linked via `derivedFrom`) | Separate Observation with `derivedFrom` pointing at the genotype Observation URN. |
| `calls[].cpic_recommendations[]` | `MedicationStatement` | One per recommendation; `medicationCodeableConcept.text` = drug; `note` combines recommendation + CPIC citation. |
| (Critic approve) | `DocumentReference` | On approve, Critic patches markdown summary into the existing `DocumentReference` attachment (`contentType=text/markdown`, base64 `data`). FHIR Composer writes a placeholder title until approval. |

## CPIC subset → calls (Analyzer)

| Gene | Variant match (CHROM:POS REF>ALT) | Genotype | Phenotype | Drug | Citation |
| --- | --- | --- | --- | --- | --- |
| CYP2C19 | 10:96541616 G>A | *1/*2 | Intermediate Metabolizer | clopidogrel | CPIC: Clopidogrel and CYP2C19 — 2022 update |
| TPMT | 6:18139208 G>A | *3A/*3A | Poor Metabolizer | azathioprine | CPIC: TPMT and azathioprine — 2018 update |

Rule data lives in `service/agents/analyzer/data/cpic_subset.json` and is baked into the Analyzer container image.

## Provenance & citation

Every `MedicationStatement` carries a `note[]` entry with the CPIC citation string. This is the Critic's hook for the `missing_cpic_citation` refusal rule (C9).

## What we are NOT mapping (in MVP)

- `Patient` / demographics — out of scope; this MVP is anonymized.
- `Practitioner` / authoring clinician — out of scope.
- `Encounter` / clinical context — out of scope.

These would be the natural next-iteration additions for a real EHR integration.
