#!/usr/bin/env bash
# Merge per-day BMB BSV files into one file per ROI type.
source ./scripts/common.sh

for ROI in sector region; do
  log_info "BMB ${ROI}"
  head -n1 ./tmp/BMB/${ROI}_2000-01-01.bsv > ./tmp/BMB_VHD_${ROI}.bsv
  tail -q -n1 ./tmp/BMB/${ROI}_*.bsv >> ./tmp/BMB_VHD_${ROI}.bsv
done
