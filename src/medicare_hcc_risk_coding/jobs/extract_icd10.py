"""Code the diseases and problems in each note to ICD-10-CM with HCC and assertion."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align
from medicare_hcc_risk_coding.schemas import ICD10_CODES, REJECTED
from medicare_hcc_risk_coding.text.interface import TextModel
from medicare_hcc_risk_coding.text.parse import parse_items, validate_icd10_item

INPUTS = ("notes",)
OUTPUTS = ("icd10_codes", "rejected_icd10")


@dataclass(frozen=True)
class Params:
    """Parameters for ICD-10 coding."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return the coded problems and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("extract_icd10")
    rows: list[dict] = []
    rejected: list[dict] = []
    for note in notes.to_pylist():
        answer = model.complete(instructions, note["text"])
        try:
            items = parse_items(answer)
        except ValueError as error:
            rejected.append(
                {"note_id": note["note_id"], "reason": str(error), "model_answer": answer}
            )
            items = []
        for item in items:
            reason = validate_icd10_item(item)
            if reason:
                rejected.append(
                    {"note_id": note["note_id"], "reason": reason, "model_answer": str(item)}
                )
                continue
            rows.append(
                {
                    "note_id": note["note_id"],
                    "patient_id": note["patient_id"],
                    "chunk": item["chunk"],
                    "icd10_code": item["icd10_code"].strip(),
                    "hcc": int(item["hcc"]) if item["hcc"] is not None else None,
                    "assertion": item["assertion"],
                    "confidence": float(item["confidence"]),
                }
            )
    return {
        "icd10_codes": align(pa.Table.from_pylist(rows, schema=ICD10_CODES), ICD10_CODES),
        "rejected_icd10": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
