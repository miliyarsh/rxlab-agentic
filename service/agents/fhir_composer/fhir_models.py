"""Build a FHIR R4 Bundle from Analyzer output."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from service.common.errors import PipelineError
from service.common.models import AnalyzerCall, AnalyzerOutput, FailureReason


def build_bundle(analyzer: AnalyzerOutput) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    observation_count = 0
    medication_count = 0

    for call in analyzer.calls:
        obs_entries = _observations_for_call(call)
        entries.extend(obs_entries)
        observation_count += len(obs_entries)
        med_entries, med_n = _medications_for_call(call)
        entries.extend(med_entries)
        medication_count += med_n

    entries.append(_document_reference_placeholder(analyzer.job_id))
    bundle = {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": entries,
    }
    _validate_bundle(bundle)
    return {
        "bundle": bundle,
        "resource_counts": {
            "Observation": observation_count,
            "MedicationStatement": medication_count,
            "DocumentReference": 1,
        },
    }


def _observations_for_call(call: AnalyzerCall) -> list[dict[str, Any]]:
    genotype_id = str(uuid4())
    entries: list[dict[str, Any]] = [
        {
            "fullUrl": f"urn:uuid:{genotype_id}",
            "resource": {
                "resourceType": "Observation",
                "status": "final",
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": "81239-4",
                            "display": "Genotype display name",
                        }
                    ]
                },
                "component": [
                    {
                        "code": {"text": call.gene},
                        "valueString": call.genotype,
                    }
                ],
            },
        }
    ]
    if call.phenotype:
        phenotype_id = str(uuid4())
        entries.append(
            {
                "fullUrl": f"urn:uuid:{phenotype_id}",
                "resource": {
                    "resourceType": "Observation",
                    "status": "final",
                    "code": {"text": f"{call.gene} phenotype"},
                    "valueString": call.phenotype,
                    "derivedFrom": [{"reference": f"urn:uuid:{genotype_id}"}],
                },
            }
        )
    return entries


def _medications_for_call(call: AnalyzerCall) -> tuple[list[dict[str, Any]], int]:
    entries: list[dict[str, Any]] = []
    for rec in call.cpic_recommendations:
        entries.append(
            {
                "fullUrl": f"urn:uuid:{uuid4()}",
                "resource": {
                    "resourceType": "MedicationStatement",
                    "status": "active",
                    "medicationCodeableConcept": {"text": rec.drug},
                    "note": [{"text": f"{rec.recommendation} ({rec.citation})"}],
                },
            }
        )
    return entries, len(entries)


def _document_reference_placeholder(job_id: str) -> dict[str, Any]:
    return {
        "fullUrl": f"urn:uuid:{uuid4()}",
        "resource": {
            "resourceType": "DocumentReference",
            "status": "current",
            "description": f"Clinician summary placeholder for job {job_id}",
            "content": [
                {
                    "attachment": {
                        "contentType": "text/markdown",
                        "title": "Summary pending Critic approval",
                    }
                }
            ],
        },
    }


def _validate_bundle(bundle: dict[str, Any]) -> None:
    if bundle.get("resourceType") != "Bundle":
        raise PipelineError(FailureReason.INVALID_FHIR_PAYLOAD, "bundle missing resourceType")
    if bundle.get("type") != "collection":
        raise PipelineError(FailureReason.INVALID_FHIR_PAYLOAD, "bundle type must be collection")
    entries = bundle.get("entry")
    if not isinstance(entries, list) or not entries:
        raise PipelineError(FailureReason.INVALID_FHIR_PAYLOAD, "bundle must contain entries")
