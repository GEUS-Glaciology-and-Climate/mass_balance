#!/usr/bin/env bash
# Merge per-day BSV files into one BSV per RCM and ROI type.
source ./scripts/common.sh

for RCM in HIRHAM MAR RACMO; do
  for ROI in sector region; do
    log_info "${RCM} ${ROI}"
    head -n1 $(ls ./tmp/${RCM}/${ROI}_????-??-??.bsv | tail -n1) > ./tmp/${RCM}_${ROI}.bsv
    tail -q -n1 ./tmp/${RCM}/${ROI}_*.bsv >> ./tmp/${RCM}_${ROI}.bsv
  done
done
