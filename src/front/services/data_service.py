"""Read backend outputs and expose front-end friendly data bundle."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import List

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_config() -> dict:
    cfg = ROOT / "config.yaml"
    if not cfg.exists():
        return {}
    with cfg.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def db_path_from_config(config: dict) -> Path:
    return ROOT / config.get("paths", {}).get("db_path", "data/processed/dqm.db")


def outputs_dir_from_config(config: dict) -> Path:
    return ROOT / config.get("paths", {}).get("outputs_dir", "data/outputs")


def raw_path_from_config(config: dict) -> Path:
    return ROOT / config.get("paths", {}).get("raw_data", "data/raw/documents.csv")


def _sql_table(db_path: Path, table_name: str) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()
    try:
        with sqlite3.connect(str(db_path)) as conn:
            return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    except Exception:
        return pd.DataFrame()


def _csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def list_generated_exports() -> List[Path]:
    config = load_config()
    out_dir = outputs_dir_from_config(config)
    if not out_dir.exists():
        return []
    files = [p for p in out_dir.rglob("*") if p.is_file()]
    return sorted(files, key=lambda p: str(p).lower())


def get_logs_tail(max_lines: int = 120) -> str:
    config = load_config()
    log_dir = outputs_dir_from_config(config) / "logs"
    if not log_dir.exists():
        return "Aucun log disponible."
    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return "Aucun log disponible."
    lines = log_files[0].read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(lines[-max_lines:])


def run_existing_pipeline() -> int:
    from main import run_pipeline

    return run_pipeline()


def _coerce_documents(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if "date_mise_a_jour" in out.columns:
        out["date_mise_a_jour"] = pd.to_datetime(out["date_mise_a_jour"], errors="coerce")
    if "conformite_score" in out.columns:
        out["conformite_score"] = pd.to_numeric(out["conformite_score"], errors="coerce")
    return out


def load_bundle(refresh_token: int = 0) -> dict:
    import streamlit as st

    @st.cache_data(show_spinner=False, ttl=120)
    def _cached(_token: int) -> dict:
        config = load_config()
        db_path = db_path_from_config(config)
        out_dir = outputs_dir_from_config(config)

        documents = _sql_table(db_path, "documents")
        anomalies = _sql_table(db_path, "anomalies")
        runs = _sql_table(db_path, "runs")

        source = "sqlite"
        if documents.empty:
            csv_candidate = out_dir / "documents_clean.csv"
            documents = _csv(csv_candidate)
            source = "csv_outputs" if not documents.empty else "none"

        documents = _coerce_documents(documents)

        total_documents = int(len(documents))
        if total_documents and "conformite_score" in documents.columns:
            scores = documents["conformite_score"].fillna(0)
            conformes = int((scores >= 90).sum())
            critiques = int((scores < 50).sum())
            taux = round((conformes / total_documents) * 100, 2)
            score_moyen = round(float(scores.mean()), 2)
        else:
            conformes = 0
            critiques = 0
            taux = 0.0
            score_moyen = 0.0

        stats = {
            "total_documents": total_documents,
            "anomalies": int(len(anomalies)),
            "conformes": conformes,
            "critiques": critiques,
            "taux_conformite": taux,
            "score_moyen": score_moyen,
            "source": source,
        }

        return {
            "config": config,
            "documents": documents,
            "anomalies": anomalies,
            "runs": runs,
            "stats": stats,
            "db_path": str(db_path),
            "outputs_dir": str(out_dir),
        }

    return _cached(refresh_token)
