# Analyzer → FHIR Mapping

> Filled in Phase 2. This file documents how the Analyzer's output is mapped to FHIR R4 resources by the `fhir_composer` agent.

## Output container

A FHIR R4 `Bundle` with `type = "collection"`. The bundle's `entry[]` carries the resources below.

## Resources

| Analyzer field | FHIR resource | Notes |
| --- | --- | --- |
| `calls[].gene` + `calls[].genotype` | `Observation` | `code` = LOINC for "genotype display name" (TBD); `valueCodeableConcept` = the genotype call. |
| `calls[].phenotype` | `Observation` (linked via `derivedFrom`) | Phenotype is derived from genotype per the CPIC subset; recorded as its own Observation for traceability. |
| `calls[].cpic_recommendations[]` | `MedicationStatement` | One per (drug, recommendation) pair. `medicationCodeableConcept` = RxNorm code for the drug; `note` = recommendation text. |
| Summarizer output (only when Critic approves) | `DocumentReference` | `content[0].attachment.contentType = "text/markdown"`, `content[0].attachment.data = base64(summary)`. |

## Provenance & citation

Every `MedicationStatement` carries a `note[]` entry with the CPIC citation string (e.g., `"CPIC: Clopidogrel and CYP2C19 — 2022 update"`). This is the Critic's hook for the `missing_cpic_citation` refusal rule.

## What we are NOT mapping (in MVP)

- `Patient` / demographics — out of scope; this MVP is anonymized.
- `Practitioner` / authoring clinician — out of scope.
- `Encounter` / clinical context — out of scope.

These would be the natural next-iteration additions for a real EHR integration.
