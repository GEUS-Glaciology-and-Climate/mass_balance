#!/usr/bin/env bash
# Sourced by all bash scripts — do not execute directly
set -o nounset
set -o pipefail

red='\033[0;31m'; orange='\033[0;33m'; green='\033[0;32m'; nc='\033[0m'
log_info() { echo -e "${green}[$(date --iso-8601=seconds)] [INFO] ${@}${nc}"; }
log_warn() { echo -e "${orange}[$(date --iso-8601=seconds)] [WARN] ${@}${nc}"; }
log_err()  { echo -e "${red}[$(date --iso-8601=seconds)] [ERR] ${@}${nc}" >&2; }

export GRASS_VERBOSE=3

# Give each Mouginot 2019 basin one id per NAME (a basin can be several
# polygons), numbered in C-locale name order, and write the id -> NAME table to
# tmp/<RCM>_catchment_names.bsv. Catchment BSVs are keyed by these ids, and
# smb_bsv2nc.py / bmb_bsv2nc.py turn them back into names with this table.
# Run in the Mouginot_2019 mapset, after the ICE_CAPS_ rows are deleted.
number_basins() {
  mkdir -p tmp
  v.db.select -c map=basins columns=NAME | LC_ALL=C sort -u \
    | awk '{printf "UPDATE basins SET basin_num=%d WHERE NAME='\''%s'\'';\n", NR, $0}' \
    | db.execute input=-
  v.db.select map=basins columns=basin_num,NAME separator=pipe \
    | awk 'NR == 1 || !seen[$0]++' \
    > ./tmp/${1}_catchment_names.bsv
}

if [ -z ${DATADIR+x} ]; then
    echo "DATADIR environment variable is unset."
    echo "Fix with: \"export DATADIR=/path/to/data\""
    exit 255
fi
