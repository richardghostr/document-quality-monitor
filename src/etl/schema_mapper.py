"""
Intelligent schema mapping for heterogeneous document datasets.

This module maps arbitrary user column names to a standard internal schema
using synonyms and fuzzy matching.
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger("etl.schema_mapper")

try:
    from rapidfuzz import fuzz as rapidfuzz_fuzz
except Exception:
    rapidfuzz_fuzz = None


STANDARD_DEFAULTS = {
    "doc_id": "",
    "nom_document": "UNKNOWN",
    "version": "N/A",
    "statut": "UNKNOWN",
    "date_mise_a_jour": pd.NaT,
    "responsable": "UNKNOWN",
    "discipline": "UNKNOWN",
    "criticite": "Moyenne",
    "type_document": "UNKNOWN",
    "projet": "UNKNOWN",
    "conformite": "En attente",
    "nb_revisions": 0,
    "commentaire": "",
}

SYNONYMS = {
    "doc_id": [
        "id", "document_id", "id_doc", "iddocument", "docid", "numero_doc",
        "num_doc", "reference", "reference_document", "document_reference",
    ],
    "nom_document": [
        "document_name", "doc_name", "nom", "titre", "title", "filename",
        "file_name", "document", "description_document",
    ],
    "version": ["rev", "revision", "indice", "index", "version_doc"],
    "statut": ["status", "etat", "state", "document_status", "statut_document"],
    "date_mise_a_jour": [
        "date", "date_maj", "last_update", "updated_at", "modification_date",
        "date_modification", "last_modified", "date_update", "update_date",
    ],
    "responsable": [
        "owner", "proprietaire", "auteur", "author", "assigned_to",
        "responsible", "responsable_document", "pilote",
    ],
    "discipline": ["metier", "departement", "department", "lot", "domaine", "trade"],
    "criticite": ["criticalite", "priority", "priorite", "severity", "criticity"],
    "type_document": [
        "doc_type", "type", "category", "categorie", "nature_document", "document_type",
    ],
    "projet": ["project", "project_name", "chantier", "site", "programme", "affaire"],
    "conformite": ["compliance", "quality_status", "etat_conformite"],
    "nb_revisions": ["revision_count", "revisions", "nb_rev", "nombre_revisions"],
    "commentaire": ["comment", "comments", "notes", "remarque", "observation"],
}


def _normalize(text: str) -> str:
    s = str(text or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if rapidfuzz_fuzz is not None:
        return float(rapidfuzz_fuzz.ratio(a, b))
    return SequenceMatcher(None, a, b).ratio() * 100.0


def standard_columns() -> List[str]:
    return list(STANDARD_DEFAULTS.keys())


def load_manual_mapping(mapping_path: str | Path | None) -> Dict[str, str]:
    if not mapping_path:
        return {}

    p = Path(mapping_path)
    if not p.exists():
        return {}

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        out = {}
        for source_col, standard_col in data.items():
            if isinstance(source_col, str) and isinstance(standard_col, str):
                out[source_col] = standard_col
        return out
    except Exception as exc:
        logger.warning(f"Impossible de lire le mapping manuel ({p}): {exc}")
        return {}


def save_manual_mapping(mapping: Dict[str, str], mapping_path: str | Path) -> None:
    p = Path(mapping_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


def detect_column_mapping(
    columns: List[str],
    manual_mapping: Dict[str, str] | None = None,
    fuzzy_threshold: float = 78.0,
) -> Dict:
    manual_mapping = manual_mapping or {}

    source_cols = [str(c) for c in columns]
    source_norm = {c: _normalize(c) for c in source_cols}

    synonym_norm = {
        std: {_normalize(std)}.union({_normalize(s) for s in SYNONYMS.get(std, [])})
        for std in standard_columns()
    }

    mapped_source_to_standard: Dict[str, str] = {}
    details = []

    # 1) Manual overrides first.
    for source_col, target_standard in manual_mapping.items():
        if source_col in source_cols and target_standard in STANDARD_DEFAULTS:
            mapped_source_to_standard[source_col] = target_standard
            details.append(
                {
                    "source_column": source_col,
                    "standard_column": target_standard,
                    "confidence": 100.0,
                    "method": "manual",
                }
            )

    # 2) Exact/synonym/fuzzy automatic mapping.
    already_mapped_sources = set(mapped_source_to_standard.keys())
    used_standard = set(mapped_source_to_standard.values())

    for source_col in source_cols:
        if source_col in already_mapped_sources:
            continue

        src_norm = source_norm[source_col]

        best_standard = None
        best_confidence = 0.0
        best_method = "none"

        for std in standard_columns():
            if std in used_standard:
                continue

            candidates = synonym_norm[std]
            if src_norm in candidates:
                best_standard = std
                best_confidence = 100.0
                best_method = "synonym"
                break

            # Fuzzy against standard and known synonyms.
            local_best = 0.0
            for candidate in candidates:
                score = _similarity(src_norm, candidate)
                if score > local_best:
                    local_best = score

            if local_best > best_confidence:
                best_confidence = local_best
                best_standard = std
                best_method = "fuzzy"

        if best_standard and (
            best_method == "synonym" or best_confidence >= fuzzy_threshold
        ):
            mapped_source_to_standard[source_col] = best_standard
            used_standard.add(best_standard)
            details.append(
                {
                    "source_column": source_col,
                    "standard_column": best_standard,
                    "confidence": round(best_confidence, 1),
                    "method": best_method,
                }
            )

    mapped_sources = set(mapped_source_to_standard.keys())
    mapped_standards = set(mapped_source_to_standard.values())

    return {
        "mapped_source_to_standard": mapped_source_to_standard,
        "details": sorted(details, key=lambda x: x["source_column"].lower()),
        "unmapped_source_columns": sorted([c for c in source_cols if c not in mapped_sources]),
        "missing_standard_columns": sorted([c for c in standard_columns() if c not in mapped_standards]),
        "source_present_standard_columns": sorted(mapped_standards),
    }


def standardize_dataframe(
    df: pd.DataFrame,
    manual_mapping: Dict[str, str] | None = None,
) -> Tuple[pd.DataFrame, Dict]:
    mapping = detect_column_mapping(df.columns.tolist(), manual_mapping=manual_mapping)
    rename_map = mapping["mapped_source_to_standard"]

    standardized = df.rename(columns=rename_map).copy()

    # Ensure all standard columns exist.
    for col, default in STANDARD_DEFAULTS.items():
        if col not in standardized.columns:
            standardized[col] = default

    # Fill critical default values if empty.
    if "doc_id" in standardized.columns:
        standardized["doc_id"] = standardized["doc_id"].astype(str).replace({"nan": "", "None": ""}).str.strip()
        auto_ids = standardized["doc_id"].eq("")
        if auto_ids.any():
            standardized.loc[auto_ids, "doc_id"] = [f"AUTO-{i:06d}" for i in range(1, int(auto_ids.sum()) + 1)]

    for col in [
        "nom_document", "version", "statut", "responsable", "discipline",
        "criticite", "type_document", "projet", "conformite", "commentaire",
    ]:
        if col in standardized.columns:
            standardized[col] = standardized[col].astype(str).replace({"nan": "", "None": ""}).str.strip()
            fill_value = STANDARD_DEFAULTS[col]
            standardized.loc[standardized[col].eq(""), col] = fill_value

    if "nb_revisions" in standardized.columns:
        standardized["nb_revisions"] = pd.to_numeric(standardized["nb_revisions"], errors="coerce").fillna(0).astype(int)

    if "date_mise_a_jour" in standardized.columns:
        standardized["date_mise_a_jour"] = pd.to_datetime(standardized["date_mise_a_jour"], errors="coerce")

    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_columns": [str(c) for c in df.columns.tolist()],
        "mapping_details": mapping["details"],
        "unmapped_source_columns": mapping["unmapped_source_columns"],
        "missing_standard_columns": mapping["missing_standard_columns"],
        "source_present_standard_columns": mapping["source_present_standard_columns"],
        "manual_overrides_applied": sorted(list((manual_mapping or {}).keys())),
    }

    standardized.attrs["dqm_mapping_report"] = report
    return standardized, report
