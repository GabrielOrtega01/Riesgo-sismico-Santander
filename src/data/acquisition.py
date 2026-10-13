"""Descarga reproducible de las fuentes complementarias (DANE y SGC) a `data/raw/`.

Se ejecuta una sola vez (necesita internet). Nunca sobrescribe datos crudos existentes salvo
que se pase `--force`. El resto del proyecto trabaja sin red, leyendo los archivos guardados.

    python -m src.data.acquisition

Fuentes:
- DIVIPOLA - Municipios Santander (DANE), datos.gov.co, id kyaq-ecfy, licencia CC BY-SA 4.0.
- Amenaza Sísmica 2020 (SGC): servicio ArcGIS MapServer, operación `identify` sobre rásteres.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pandas as pd

from src.data.integration import HAZARD_COLUMNS, parse_decimal

DIVIPOLA_URL = "https://www.datos.gov.co/resource/kyaq-ecfy.json?$limit=500"
DIVIPOLA_COLUMNS = ["cod_mpio", "nom_mpio", "tipo_municipio", "longitud", "latitud"]
DIVIPOLA_FILE = "divipola_municipios_santander.csv"

MAPSERVER_URL = (
    "https://srvags.sgc.gov.co/arcprod/rest/services/Amenaza_Sismica/Amenaza_Sismica/MapServer"
)
# id de capa del MapServer -> nombre de columna. PGA y Sa en g; intensidad en escala EMS/MMI.
HAZARD_LAYERS = {
    1: "pga_tr31", 5: "pga_tr225", 9: "pga_tr475", 13: "pga_tr975", 17: "pga_tr2475",
    10: "sa02_tr475", 11: "sa10_tr475", 21: "intensidad_esperada",
}
HAZARD_FILE = "sgc_amenaza_2020_cabeceras.csv"
_MAP_EXTENT = "-74.6,5.6,-72.4,8.2"   # cubre Santander; solo parametriza la consulta identify

GetJson = Callable[[str], object]


def _get_json(url: str, timeout: int = 45):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_divipola(get_json: GetJson = _get_json) -> pd.DataFrame:
    """Descarga DIVIPOLA de Santander tal como se publica (todo texto, sin convertir)."""
    rows = get_json(DIVIPOLA_URL)
    df = pd.DataFrame(rows)
    missing = [c for c in DIVIPOLA_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"DIVIPOLA cambió de formato; faltan {missing}")
    return df[DIVIPOLA_COLUMNS].astype(str)


def identify_point(lon: float, lat: float, get_json: GetJson = _get_json) -> dict[str, float | None]:
    """Valor de cada capa de amenaza en un punto (WGS84)."""
    query = urllib.parse.urlencode({
        "geometry": json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryPoint", "sr": 4326,
        "layers": "all:" + ",".join(str(i) for i in HAZARD_LAYERS),
        "tolerance": 2, "mapExtent": _MAP_EXTENT, "imageDisplay": "600,500,96",
        "returnGeometry": "false", "f": "json",
    })
    response = get_json(f"{MAPSERVER_URL}/identify?{query}")
    if isinstance(response, dict) and response.get("error"):
        raise RuntimeError(f"El servicio devolvió un error: {response['error']}")

    values: dict[str, float | None] = {name: None for name in HAZARD_LAYERS.values()}
    for item in response.get("results", []):
        name = HAZARD_LAYERS.get(item.get("layerId"))
        if name is None:
            continue
        attrs = item.get("attributes", {})
        raw = attrs.get("Classify.Pixel Value", attrs.get("Pixel Value"))
        try:
            values[name] = float(raw)
        except (TypeError, ValueError):
            values[name] = None            # "NoData" u otro texto
    return values


def sample_hazard(
    divipola: pd.DataFrame,
    identify: Callable[[float, float], dict] = identify_point,
    pause_s: float = 0.05,
) -> pd.DataFrame:
    """Muestrea la amenaza en la cabecera de cada municipio. Falla si algún valor falta."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for _, muni in divipola.iterrows():
        lon, lat = parse_decimal(muni["longitud"]), parse_decimal(muni["latitud"])
        values = identify(lon, lat)
        empty = [k for k, v in values.items() if v is None]
        if empty:
            raise RuntimeError(f"Sin valor de amenaza en {muni['nom_mpio']} para {empty}")
        rows.append({
            "cod_mpio": muni["cod_mpio"], "lon_usada": lon, "lat_usada": lat,
            **{c: values[c] for c in HAZARD_COLUMNS},
            "fecha_consulta_utc": stamp,
        })
        time.sleep(pause_s)
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Descarga DIVIPOLA y muestrea la amenaza del SGC.")
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--force", action="store_true", help="Permite sobrescribir archivos crudos.")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    targets = [out / DIVIPOLA_FILE, out / HAZARD_FILE]
    existing = [p.name for p in targets if p.exists()]
    if existing and not args.force:
        raise SystemExit(f"Ya existen {existing}. Los datos crudos no se sobrescriben (use --force).")

    divipola = fetch_divipola()
    hazard = sample_hazard(divipola)
    divipola.to_csv(targets[0], index=False)
    hazard.to_csv(targets[1], index=False, float_format="%.6f")
    print(f"DIVIPOLA: {len(divipola)} municipios -> {targets[0]}")
    print(f"Amenaza:  {len(hazard)} municipios x {len(HAZARD_COLUMNS)} capas -> {targets[1]}")


if __name__ == "__main__":
    main()
