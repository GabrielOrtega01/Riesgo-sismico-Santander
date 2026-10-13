"""Descarga reproducible de las fuentes complementarias (DANE y SGC) a `data/raw/`.

Se ejecuta una sola vez (necesita internet). Nunca sobrescribe datos crudos existentes salvo
que se pase `--force`. El resto del proyecto trabaja sin red, leyendo los archivos guardados.

    python -m src.data.acquisition

Fuentes:
- DIVIPOLA - Municipios Santander (DANE), datos.gov.co, id kyaq-ecfy, licencia CC BY-SA 4.0.
- Amenaza Sísmica 2020 (SGC): servicio ArcGIS MapServer, operación `identify` sobre rásteres.
- Proyecciones de población municipal 2005-2042 (DANE, base CNPV 2018): dos libros Excel.
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

# Proyecciones de población municipal del DANE (basadas en el CNPV 2018), con área.
_DANE_POP = "https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/Municipal/"
POPULATION_FILES = {
    "DCD-area-proypoblacion-Mun-2005-2017_VP.xlsx": _DANE_POP + "DCD-area-proypoblacion-Mun-2005-2017_VP.xlsx",
    "PPED-AreaMun-2018-2042_VP.xlsx": _DANE_POP + "PPED-AreaMun-2018-2042_VP.xlsx",
}

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


def _get_bytes(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def download_population_files(
    out_dir: str | Path,
    force: bool = False,
    fetch_bytes: Callable[[str], bytes] = _get_bytes,
) -> dict[str, str]:
    """Descarga las proyecciones de población del DANE (Excel) tal como se publican.

    No sobrescribe archivos existentes salvo `force`. Verifica que el contenido sea un .xlsx
    (un ZIP) antes de guardarlo y no deja archivos parciales. Devuelve {archivo: estado}.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, str] = {}
    for name, url in POPULATION_FILES.items():
        dest = out_dir / name
        if dest.exists() and not force:
            status[name] = "ya existe (no se sobrescribe)"
            continue
        content = fetch_bytes(url)
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError(f"{name}: la respuesta no es un archivo .xlsx válido")
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(content)
        tmp.replace(dest)
        status[name] = f"descargado ({len(content) / 1024 / 1024:.2f} MB)"
    return status


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Descarga DIVIPOLA, muestrea la amenaza del SGC y baja la población del DANE."
    )
    parser.add_argument("--out", default="data/raw")
    parser.add_argument("--force", action="store_true", help="Permite sobrescribir archivos crudos.")
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    divipola_path, hazard_path = out / DIVIPOLA_FILE, out / HAZARD_FILE

    if divipola_path.exists() and not args.force:
        print(f"DIVIPOLA: ya existe, no se sobrescribe -> {divipola_path}")
        divipola = pd.read_csv(divipola_path, dtype=str, keep_default_na=False)
    else:
        divipola = fetch_divipola()
        divipola.to_csv(divipola_path, index=False)
        print(f"DIVIPOLA: {len(divipola)} municipios -> {divipola_path}")

    if hazard_path.exists() and not args.force:
        print(f"Amenaza:  ya existe, no se sobrescribe -> {hazard_path}")
    else:
        hazard = sample_hazard(divipola)
        hazard.to_csv(hazard_path, index=False, float_format="%.6f")
        print(f"Amenaza:  {len(hazard)} municipios x {len(HAZARD_COLUMNS)} capas -> {hazard_path}")

    for name, state in download_population_files(out, force=args.force).items():
        print(f"Población: {name}: {state}")


if __name__ == "__main__":
    main()
