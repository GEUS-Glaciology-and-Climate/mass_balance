#!/usr/bin/env bash
# Extract daily SMB from MAR and aggregate to Zwally sectors and Mouginot regions.
# Runs in G_MAR (EPSG:3413). MAR NetCDF has dimensions (time, sector, y, x) where
# sector k=1 is permanent ice and k=2 is tundra; GRASS exposes these as odd/even bands.
source ./scripts/common.sh

RCM=MAR
mkdir -p tmp/${RCM}

dir=${DATADIR}/MAR/3.12

if [ "$RECENT" = "false" ] || [ -z ${RECENT} ]; then
  f_list=$(ls ${dir}/*.nc)
  log_info "Initial run. Processing all files"
else
  f_list=$(ls ${dir}/*.nc | tail -n 2)
  log_warn "RECENT set to ${RECENT}. Processing subset of files"
fi

for f in ${f_list}; do
  dates=$(python ./scripts/nc_dates.py ${f})

  # Band indexing: k=1 (ice) is at odd bands, k=2 (tundra) at even.
  # We want ice (k=1), so start at band 1 and step by 2.
  band=-1
  for d in ${dates}; do
    band=$(( ${band} + 2 ))

    log_info "${RCM}: ${d}"

    if [[ -e ./tmp/${RCM}/sector_${d}.bsv ]]; then continue; fi

    r.in.gdal -o input="NetCDF:${f}:smb" band=${band} output=SMB_raw --o --q
    r.region map=SMB_raw region=RCM
    r.mapcalc "SMB = if(mask > 50, SMB_raw * (mask/100), null())" --o

    r.univar -t --q map=SMB zones=sectors_e@Zwally_2012 \
    | cut -d"|" -f1,13 \
    | datamash -t"|" transpose \
    | sed s/^sum/${d}/ \
    > ./tmp/${RCM}/sector_${d}.bsv

    r.univar -t --q map=SMB zones=regions_e@Mouginot_2019 \
    | cut -d"|" -f1,13 \
    | datamash -t"|" transpose \
    | sed s/^sum/${d}/ \
    > ./tmp/${RCM}/region_${d}.bsv

  done
done
