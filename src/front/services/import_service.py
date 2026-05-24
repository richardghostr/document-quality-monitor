"""Input management service: uploads, SharePoint links, import history."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

from src.etl.schema_mapper import detect_column_mapping, save_manual_mapping

from .data_service import ROOT, load_config, raw_path_from_config

HISTORY_PATH = ROOT / "src" / "front" / "data" / "import_history.csv"
IMPORT_ARCHIVE_DIR = ROOT / "data" / "raw" / "imports"


def _ensure_dirs() -> None:
    IMPORT_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def _history_df() -> pd.DataFrame:
    if HISTORY_PATH.exists():
        try:
            return pd.read_csv(HISTORY_PATH)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()


def _append_history(record: dict) -> None:
    df = _history_df()
    out = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    out.to_csv(HISTORY_PATH, index=False, encoding="utf-8")


def get_import_history() -> pd.DataFrame:
    return _history_df()


def _validate_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    if df is None or df.empty:
        return False, "Le fichier est vide ou illisible"
    return True, "Valide"


def _manual_mapping_path_from_config(config: dict) -> Path:
    rel = config.get("paths", {}).get("manual_mapping", "data/raw/manual_mapping.json")
    return ROOT / rel


def _read_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        content = uploaded_file.getvalue()
        errors = []
        for encoding in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return pd.read_csv(
                    pd.io.common.BytesIO(content),
                    sep=None,
                    engine="python",
                    encoding=encoding,
                    dtype=str,
                )
            except Exception as exc:
                errors.append(f"{encoding}: {exc}")
        raise ValueError("Lecture CSV impossible. " + " | ".join(errors))

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(pd.io.common.BytesIO(uploaded_file.getvalue()), dtype=str)

    raise ValueError("Type de fichier non supporté (CSV/Excel uniquement)")


def preview_uploaded_file(uploaded_file, manual_mapping: Optional[Dict[str, str]] = None) -> Tuple[bool, str, dict]:
    try:
        df = _read_uploaded_file(uploaded_file)
    except Exception as exc:
        return False, f"Lecture impossible: {exc}", {}

    ok, msg = _validate_dataframe(df)
    if not ok:
        return False, msg, {}

    mapping = detect_column_mapping(df.columns.tolist(), manual_mapping=manual_mapping or {})
    mapping_rows = []
    details_by_source = {d["source_column"]: d for d in mapping.get("details", [])}
    for source_col in df.columns.tolist():
        detail = details_by_source.get(source_col)
        mapping_rows.append(
            {
                "source_column": source_col,
                "target_standard": detail["standard_column"] if detail else "",
                "confidence": detail["confidence"] if detail else 0.0,
                "method": detail["method"] if detail else "none",
            }
        )

    payload = {
        "preview": df.head(30),
        "mapping_rows": pd.DataFrame(mapping_rows),
        "unmapped_source_columns": mapping.get("unmapped_source_columns", []),
        "missing_standard_columns": mapping.get("missing_standard_columns", []),
        "source_columns": df.columns.tolist(),
    }
    return True, "Prévisualisation prête", payload


def save_uploaded_file(
    uploaded_file,
    manual_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[bool, str, Optional[pd.DataFrame]]:
    _ensure_dirs()
    config = load_config()
    raw_target = raw_path_from_config(config)
    raw_target.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_name = uploaded_file.name
    archive_name = f"{ts}_{original_name}"
    archive_path = IMPORT_ARCHIVE_DIR / archive_name

    content = uploaded_file.getvalue()
    archive_path.write_bytes(content)

    try:
        # Réutilise la lecture robuste du fichier original uploadé.
        df = _read_uploaded_file(uploaded_file)
    except Exception as exc:
        return False, f"Lecture impossible: {exc}", None

    ok, msg = _validate_dataframe(df)
    if not ok:
        _append_history(
            {
                "timestamp": ts,
                "source": "upload",
                "fichier": original_name,
                "statut": "rejeté",
                "message": msg,
            }
        )
        return False, msg, df.head(30)

    # Harmonisation avec le pipeline existant: on dépose toujours un CSV sur le chemin raw_data.
    df.to_csv(raw_target, index=False, encoding="utf-8")

    if manual_mapping:
        mapping_path = _manual_mapping_path_from_config(config)
        save_manual_mapping(manual_mapping, mapping_path)

    detected = detect_column_mapping(df.columns.tolist(), manual_mapping=manual_mapping or {})
    recognized = len(detected.get("source_present_standard_columns", []))
    unmapped = len(detected.get("unmapped_source_columns", []))

    _append_history(
        {
            "timestamp": ts,
            "source": "upload",
            "fichier": original_name,
            "statut": "importé",
            "message": f"Stocké dans {raw_target} | mapping: {recognized} reconnu(s), {unmapped} non reconnu(s)",
        }
    )

    return True, f"Import réussi. Fichier prêt pour pipeline: {raw_target}", df.head(30)


def save_sharepoint_link(link: str) -> Tuple[bool, str]:
    _ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Exemple simple d'intégration: si lien public direct vers CSV, tentative de lecture.
    if link.lower().endswith(".csv"):
        try:
            df = pd.read_csv(link)
            config = load_config()
            raw_target = raw_path_from_config(config)
            raw_target.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(raw_target, index=False, encoding="utf-8")
            _append_history(
                {
                    "timestamp": ts,
                    "source": "sharepoint",
                    "fichier": link,
                    "statut": "importé",
                    "message": f"Lien CSV ingéré et stocké dans {raw_target}",
                }
            )
            return True, "Lien SharePoint/CSV importé avec succès."
        except Exception as exc:
            _append_history(
                {
                    "timestamp": ts,
                    "source": "sharepoint",
                    "fichier": link,
                    "statut": "erreur",
                    "message": str(exc),
                }
            )
            return False, f"Lecture du lien impossible: {exc}"

    _append_history(
        {
            "timestamp": ts,
            "source": "sharepoint",
            "fichier": link,
            "statut": "en attente",
            "message": "Lien enregistré. Connecteur SharePoint avancé à configurer selon tenant entreprise.",
        }
    )
    return True, "Lien SharePoint enregistré dans l'historique (mode démonstration)."
