"""Infer the patient's gender at birth and age from each note."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align
from medicare_hcc_risk_coding.schemas import DEMOGRAPHICS, REJECTED
from medicare_hcc_risk_coding.text.interface import TextModel
from medicare_hcc_risk_coding.text.parse import parse_object, validate_demographics_item

INPUTS = ("notes",)
OUTPUTS = ("demographics", "rejected_demographics")


@dataclass(frozen=True)
class Params:
    """Parameters for demographic inference."""


def run(inputs: dict[str, pa.Table], params: Params, model: TextModel) -> dict[str, pa.Table]:
    """Return one demographics row per patient and every answer that failed validation."""
    notes = inputs["notes"]
    instructions = io.read_prompt("infer_demographics")
    rows: dict[str, dict] = {}
    rejected: list[dict] = []
    for note in notes.to_pylist():
        answer = model.complete(instructions, note["text"])
        try:
            item = parse_object(answer)
            reason = validate_demographics_item(item)
        except ValueError as error:
            reason = str(error)
        if reason:
            rejected.append({"note_id": note["note_id"], "reason": reason, "model_answer": answer})
            continue
        existing = rows.get(note["patient_id"])
        if existing is None or float(item["confidence"]) > existing["confidence"]:
            rows[note["patient_id"]] = {
                "patient_id": note["patient_id"],
                "gender": item["gender"],
                "age": int(item["age"]),
                "confidence": float(item["confidence"]),
            }
    ordered = [rows[patient_id] for patient_id in sorted(rows)]
    return {
        "demographics": align(pa.Table.from_pylist(ordered, schema=DEMOGRAPHICS), DEMOGRAPHICS),
        "rejected_demographics": align(pa.Table.from_pylist(rejected, schema=REJECTED), REJECTED),
    }
