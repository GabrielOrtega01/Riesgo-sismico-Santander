"""Utilidades de prueba.

Los datos que se construyen aquí son SINTÉTICOS: sirven para verificar el comportamiento del
código en casos controlados y no representan sismos reales ni resultados del proyecto.
"""
import pandas as pd
import pytest

from src.data.loaders import SGC_COLUMNS

BASE_ROW = {
    "status": "manual", "rms": "0.4", "agency": "SGC", "gap": "120",
    "place": "Los Santos - Santander, Colombia",
    "magnitude": "2.0", "magnitude_error": "0.2", "nst": "10", "mag_type": "ML",
    "latitude": "6.80", "latitude_error": "1.0", "longitude": "-73.15",
    "longitude_error": "1.0", "depth": "145", "depth_error": "3",
}


@pytest.fixture
def make_raw():
    """Construye un catálogo crudo sintético (todo texto) a partir de sobrescrituras por fila."""

    def _make(*overrides: dict) -> pd.DataFrame:
        rows = []
        for i, over in enumerate(overrides):
            utc = f"2020-01-01T00:{i:02d}:00+00:00"
            row = {**BASE_ROW, "id": f"SYN{i:03d}", "utc_time": utc, "local_time": utc, **over}
            rows.append(row)
        return pd.DataFrame(rows, columns=SGC_COLUMNS)

    return _make
