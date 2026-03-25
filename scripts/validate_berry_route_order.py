#!/usr/bin/env python3
"""
Validate that routes/berry-mappemonde-route-order.json matches the canon GeoJSON.

Usage:
  python3 scripts/validate_berry_route_order.py          # compare (CI)
  python3 scripts/validate_berry_route_order.py --write  # regenerate JSON from GeoJSON

After editing routes/naviguide-berry-mappemonde.geojson, run with --write and commit
both files. MR pipeline job berry_route_order_validate runs the compare mode.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GEOJSON_PATH = REPO_ROOT / "routes" / "naviguide-berry-mappemonde.geojson"
ORDER_JSON_PATH = REPO_ROOT / "routes" / "berry-mappemonde-route-order.json"
SOURCE_GEOJSON = "routes/naviguide-berry-mappemonde.geojson"

SPM_ENDPOINTS = frozenset(
    {
        "Halifax (Nouvelle-Écosse)",
        "Saint-Pierre (Saint-Pierre-et-Miquelon)",
    }
)


def extract_route_order(geojson: dict) -> dict:
    features = geojson.get("features") or []
    escales_ordered: list[str] = []
    legs_ordered: list[dict[str, str]] = []

    for feat in features:
        geom = feat.get("geometry") or {}
        props = feat.get("properties") or {}
        gtype = geom.get("type")

        if gtype == "Point" and props.get("point_type") == "escale":
            name = props.get("name")
            if name is not None:
                escales_ordered.append(str(name))

        if gtype == "LineString":
            f, t, lt = props.get("from"), props.get("to"), props.get("type")
            if f is not None and t is not None and lt is not None:
                legs_ordered.append(
                    {"from": str(f), "to": str(t), "type": str(lt)}
                )

    decoupled_legs = [
        leg for leg in legs_ordered if frozenset((leg["from"], leg["to"])) == SPM_ENDPOINTS
    ]

    return {
        "schema_version": 1,
        "source_geojson": SOURCE_GEOJSON,
        "escales_ordered": escales_ordered,
        "legs_ordered": legs_ordered,
        "decoupled_legs": decoupled_legs,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write routes/berry-mappemonde-route-order.json from GeoJSON",
    )
    args = parser.parse_args()

    if not GEOJSON_PATH.is_file():
        print(f"ERROR: missing {GEOJSON_PATH}", file=sys.stderr)
        return 1

    raw = GEOJSON_PATH.read_text(encoding="utf-8")
    geo = json.loads(raw)
    computed = extract_route_order(geo)

    if args.write:
        ORDER_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        ORDER_JSON_PATH.write_text(
            json.dumps(computed, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {ORDER_JSON_PATH}")
        return 0

    if not ORDER_JSON_PATH.is_file():
        print(f"ERROR: missing {ORDER_JSON_PATH}; run with --write first", file=sys.stderr)
        return 1

    expected = json.loads(ORDER_JSON_PATH.read_text(encoding="utf-8"))
    if expected != computed:
        print("ERROR: berry-mappemonde-route-order.json is out of sync with GeoJSON.", file=sys.stderr)
        exp_s = json.dumps(expected, indent=2, ensure_ascii=False, sort_keys=True)
        got_s = json.dumps(computed, indent=2, ensure_ascii=False, sort_keys=True)
        print("--- expected (file) ---", file=sys.stderr)
        print(exp_s, file=sys.stderr)
        print("--- computed (geojson) ---", file=sys.stderr)
        print(got_s, file=sys.stderr)
        return 1

    print("OK: route order JSON matches GeoJSON.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
