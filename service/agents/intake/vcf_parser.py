"""VCF parsing and validation for the Intake agent."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from service.common.errors import PipelineError
from service.common.models import FailureReason, VariantCall

REQUIRED_COLUMNS = ("CHROM", "POS", "REF", "ALT")


@dataclass(frozen=True)
class ParsedVcf:
    sample_class: str
    variants: list[VariantCall]
    warnings: list[str]


def parse_vcf_text(content: str) -> ParsedVcf:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        raise PipelineError(FailureReason.EMPTY_VCF, "VCF contains no data lines")

    header_idx = _find_header_line(lines)
    if header_idx is None:
        raise PipelineError(
            FailureReason.INVALID_VCF_SCHEMA,
            "missing #CHROM header row",
        )

    columns = lines[header_idx].lstrip("#").split("\t")
    _validate_columns(columns)

    info_idx = columns.index("INFO") if "INFO" in columns else None
    format_idx = columns.index("FORMAT") if "FORMAT" in columns else None
    sample_start = (format_idx + 1) if format_idx is not None else len(columns)

    variants: list[VariantCall] = []
    warnings: list[str] = []

    for line in lines[header_idx + 1 :]:
        if line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            warnings.append("skipped malformed variant row")
            continue

        chrom, pos_raw, _id, ref, alt = fields[0], fields[1], fields[2], fields[3], fields[4]
        try:
            pos = int(pos_raw)
        except ValueError:
            warnings.append(f"skipped non-numeric POS on {chrom}")
            continue

        gene = _extract_gene(fields, info_idx)
        variants.append(
            VariantCall(
                chrom=chrom.removeprefix("chr"),
                pos=pos,
                ref=ref,
                alt=alt.split(",")[0],
                gene=gene,
            )
        )

    if not variants:
        raise PipelineError(FailureReason.EMPTY_VCF, "VCF contains no variant rows")

    sample_class = _classify_sample(columns, sample_start)
    return ParsedVcf(sample_class=sample_class, variants=variants, warnings=warnings)


def _find_header_line(lines: Iterable[str]) -> int | None:
    for idx, line in enumerate(lines):
        if line.startswith("#CHROM"):
            return idx
    return None


def _validate_columns(columns: list[str]) -> None:
    missing = [col for col in REQUIRED_COLUMNS if col not in columns]
    if missing:
        raise PipelineError(
            FailureReason.INVALID_VCF_SCHEMA,
            f"missing required VCF columns: {', '.join(missing)}",
        )


def _extract_gene(fields: list[str], info_idx: int | None) -> str | None:
    if info_idx is None or info_idx >= len(fields):
        return None
    info = fields[info_idx]
    for token in info.split(";"):
        if token.startswith("GENE="):
            return token.split("=", 1)[1]
    return None


def _classify_sample(columns: list[str], sample_start: int) -> str:
    sample_columns = columns[sample_start:]
    if not sample_columns:
        return "other"
    joined = " ".join(sample_columns).lower()
    if "exome" in joined:
        return "exome"
    if "panel" in joined:
        return "panel"
    return "other"
