#!/usr/bin/env bash
# =============================================================================
# NAVIGUIDE — Geospatial data under data/
# - GEBCO 2024 bathymetry (~7 GB) — manual download (no stable public direct URL)
# - AIS World Bank Global Ship Density (~510 MB) — curl + unzip
#
# Usage:
#   ./scripts/download_geodata.sh              # download AIS if needed; print GEBCO hint if missing
#   ./scripts/download_geodata.sh --check-only # exit 0 only if required files exist
# =============================================================================

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"
GEBCO_DIR="$DATA_DIR/gebco"
AIS_DIR="$DATA_DIR/ais_worldbank"
GEBCO_FILE="$GEBCO_DIR/GEBCO_2024_CF.nc"
AIS_URL="https://datacatalogfiles.worldbank.org/ddh-published/0037580/5/DR0045406/shipdensity_global.zip"
AIS_ZIP="$AIS_DIR/shipdensity_global.zip"
AIS_TIF="$AIS_DIR/shipdensity_global.tif"

usage() {
  echo "Usage: $(basename "$0") [--check-only]"
  exit 1
}

CHECK_ONLY=0
if [ "${1:-}" = "--check-only" ]; then
  CHECK_ONLY=1
elif [ -n "${1:-}" ]; then
  usage
fi

check_gebco() {
  if [ ! -f "$GEBCO_FILE" ]; then
    echo "✗ Missing GEBCO file: $GEBCO_FILE"
    echo "  Download from https://www.gebco.net/data_and_products/gridded_bathymetry_data/gebco_2024/"
    echo "  Save as GEBCO_2024_CF.nc under $GEBCO_DIR/"
    return 1
  fi
  echo "✓ GEBCO present: $GEBCO_FILE"
  return 0
}

check_ais() {
  if [ ! -f "$AIS_TIF" ]; then
    echo "✗ Missing AIS GeoTIFF: $AIS_TIF"
    echo "  Run without --check-only to download from World Bank, or extract shipdensity_global.zip into $AIS_DIR/"
    return 1
  fi
  echo "✓ AIS ship density present: $AIS_TIF"
  return 0
}

if [ "$CHECK_ONLY" -eq 1 ]; then
  ok=0
  check_gebco || ok=1
  check_ais || ok=1
  if [ "$ok" -ne 0 ]; then
    echo ""
    echo "✗ --check-only failed: fix the issues above."
    exit 1
  fi
  echo ""
  echo "✓ All required data files present."
  exit 0
fi

mkdir -p "$GEBCO_DIR" "$AIS_DIR"

# ── GEBCO 2024 (manual) ─────────────────────────────────────────────────────
if [ -f "$GEBCO_FILE" ]; then
  echo "✓ GEBCO already present: $GEBCO_FILE"
else
  echo "⚠ GEBCO: download manually from https://www.gebco.net/data_and_products/gridded_bathymetry_data/gebco_2024/"
  echo "  Place GEBCO_2024_CF.nc in $GEBCO_DIR/"
fi

# ── AIS World Bank — Global Ship Density ───────────────────────────────────
if [ -f "$AIS_TIF" ]; then
  echo "✓ AIS World Bank already present: $AIS_TIF"
elif [ -f "$AIS_ZIP" ]; then
  echo "Found $AIS_ZIP — extracting..."
  unzip -o "$AIS_ZIP" -d "$AIS_DIR"
  if [ ! -f "$AIS_TIF" ]; then
    echo "✗ unzip finished but $AIS_TIF is still missing."
    exit 1
  fi
  echo "✓ AIS extracted."
else
  echo "Downloading AIS World Bank Global Ship Density (~510 MB)..."
  curl -fL --retry 3 --retry-delay 5 -o "$AIS_ZIP" "$AIS_URL"
  echo "Extracting..."
  unzip -o "$AIS_ZIP" -d "$AIS_DIR"
  if [ ! -f "$AIS_TIF" ]; then
    echo "✗ Download/extract finished but $AIS_TIF is missing."
    exit 1
  fi
  echo "✓ AIS downloaded and extracted."
fi

echo ""
echo "Done. Expected paths: $GEBCO_FILE and $AIS_TIF"
echo "Verify with: ./scripts/fetch_data.sh --check-only"
