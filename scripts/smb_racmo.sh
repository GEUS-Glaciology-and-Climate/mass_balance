#!/usr/bin/env bash
# Extract daily SMB from RACMO and aggregate to Zwally sectors and Mouginot regions.
# Runs in G_RACMO (EPSG:3413).
source ./scripts/common.sh

RCM=RACMO
mkdir -p tmp/${RCM}

dir=${DATADIR}/${RCM}/daily

if [ "$RECENT" = "false" ] || [ -z ${RECENT} ]; then
  f_list=$(ls ${dir}/*.nc)
  log_info "Initial run. Processing all files"
else
  f_list=$(ls ${dir}/*.nc | tail -n 2)
  log_warn "RECENT set to ${RECENT}. Processing subset of files"
fi

for f in ${f_list}; do
  dates=$(python ./scripts/nc_dates.py ${f})
  band=0
  for d in ${dates}; do
    band=$(( ${band} + 1 ))

    log_info "${RCM}: ${d}"

    if [[ -e ./tmp/${RCM}/sector_${d}.bsv ]]; then continue; fi

    # Variable name differs between ERA5-forced files (post-1989) and earlier files
    var=smb_rec
    if [[ ${f} != *"ERA5"* ]]; then var=SMB_rec; fi

    r.in.gdal -o input="NetCDF:${f}:${var}" band=${band} output=SMB --o --q
    r.region map=SMB region=RCM

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
