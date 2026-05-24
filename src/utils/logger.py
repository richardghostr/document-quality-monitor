"""
utils/logger.py
Configuration centralisée du logging pour Document Quality Monitor.
"""

import logging
import os
from datetime import datetime


def get_logger(name: str, log_dir: str = "data/outputs/logs") -> logging.Logger:
    """
    Crée et retourne un logger configuré avec handler console + fichier.

    Args:
        name: Nom du module appelant (ex: 'etl.extract')
        log_dir: Répertoire où stocker les fichiers de log

    Returns:
        logging.Logger configuré
    """
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger(name)

    # Évite d'ajouter des handlers en double si appelé plusieurs fois
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler console (INFO et au-dessus)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Handler fichier (DEBUG et au-dessus, horodaté)
    log_filename = f"dqm_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(
        os.path.join(log_dir, log_filename), encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger