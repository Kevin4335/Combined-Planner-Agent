#!/usr/bin/env python3
"""
schema_loader.py
Fast, memoised accessor for the Neo4j schema JSON and optional hints.
Also provides a simplified, distilled view of the schema for LLM prompting.

Usage
-----
from schema_loader import get_schema, get_schema_hints, get_simplified_schema
schema = get_schema()                # full dict, loaded once per process
hints = get_schema_hints()           # dict or None, loaded once per process
simple = get_simplified_schema()     # slim dict (labels, properties, relationships)
"""

from __future__ import annotations
import json, os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv

load_dotenv()
_SCHEMA_PATH = (Path(__file__).resolve().parent.parent / "data" / "input" / "neo4j_schema.json")

_HINTS_PATH = (Path(__file__).resolve().parent.parent / "data" / "input" / "schema_hints.json")


# ── internal cache --------------------------------------------------------
_cached_schema: Dict[str, Any] | None = None
_cached_hints: Dict[str, Any] | None = None
_cached_simple: Dict[str, Any] | None = None
_hints_loaded: bool = False

def get_schema() -> Dict[str, Any]:
    """Return the full Neo4j schema as a JSON dict (cached)."""
    global _cached_schema
    if _cached_schema is None:
        with _SCHEMA_PATH.open() as f:
            _cached_schema = json.load(f)
    return _cached_schema

def get_schema_hints() -> Optional[Dict[str, Any]]:
    """Return schema hints/clarifications if available (cached)."""
    global _cached_hints, _hints_loaded
    if not _hints_loaded:
        _hints_loaded = True
        if _HINTS_PATH and _HINTS_PATH.exists():
            with _HINTS_PATH.open() as f:
                _cached_hints = json.load(f)
    return _cached_hints

def get_simplified_schema() -> Dict[str, Any]:
    """Return a distilled schema with only labels, properties, and relationships."""
    global _cached_simple
    if _cached_simple is None:
        schema = get_schema()
        nodes = {
            label: list(props.keys())
            for label, props in schema.get("NodeTypes", {}).items()
        }
        relationships = {
            rel: {"source": spec["source"], "target": spec["target"]}
            for rel, spec in schema.get("RelationshipTypes", {}).items()
        }
        preferred_lookup = {
            "gene": "name",
            "ontology": ["name", "id"],
            "cell_type": "name"
        }
        Notes = {
            "ontology": "Disease and phenotype terms are represented as ontology nodes, identified by MONDO IDs (ontology.id) or names (ontology.name)."
        }
    
        _cached_simple = {
            "NodeLabels": list(nodes.keys()),
            "NodeProperties": nodes,
            "Relationships": relationships,
            "PreferredLookup": preferred_lookup,
            "Notes": Notes
        }
    return _cached_simple
