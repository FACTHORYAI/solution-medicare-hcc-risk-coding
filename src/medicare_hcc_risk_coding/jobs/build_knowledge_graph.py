"""Build the risk adjustment knowledge graph as node and edge tables."""

from __future__ import annotations

from dataclasses import dataclass

import pyarrow as pa

from medicare_hcc_risk_coding import io
from medicare_hcc_risk_coding.jobs._duck import align, run_query
from medicare_hcc_risk_coding.schemas import GRAPH_EDGES, GRAPH_NODES

INPUTS = ("notes", "icd10_codes", "demographics", "hcc_weights")
OUTPUTS = ("graph_nodes", "graph_edges")


@dataclass(frozen=True)
class Params:
    """Parameters for the knowledge-graph build."""


def run(inputs: dict[str, pa.Table], params: Params) -> dict[str, pa.Table]:
    """Return graph_nodes and graph_edges built from the notes and their coded problems."""
    nodes = align(run_query(io.read_sql("build_graph_nodes"), inputs), GRAPH_NODES)
    edges = align(run_query(io.read_sql("build_graph_edges"), inputs), GRAPH_EDGES)
    return {"graph_nodes": nodes, "graph_edges": edges}
