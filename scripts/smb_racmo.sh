#!/usr/bin/env bash
# Extract daily SMB from RACMO and aggregate to Zwally sectors, Mouginot regions
# and Mouginot catchments.
# Runs in G_RACMO (EPSG:3413).
source ./scripts/common.sh

declare -A ZONES=([sector]=sectors_e@Zwally_2012 [region]=regions_e@Mouginot_2019 [catchment]=basins_e@Mouginot_2019)

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

    # Skip the day only once every ROI has its BSV, so adding an ROI back-fills it
    todo=""
    for ROI in ${!ZONES[@]}; do
      [[ -e ./tmp/${RCM}/${ROI}_${d}.bsv ]] || todo="${todo} ${ROI}"
    done
    if [[ -z ${todo} ]]; then continue; fi

    # Variable name differs between ERA5-forced files (post-1989) and earlier files
    var=smb_rec
    if [[ ${f} != *"ERA5"* ]]; then var=SMB_rec; fi

    r.in.gdal -o input="NetCDF:${f}:${var}" band=${band} output=SMB --o --q
    r.region map=SMB region=RCM

    for ROI in ${todo}; do
      r.univar -t --q map=SMB zones=${ZONES[$ROI]} \
      | cut -d"|" -f1,13 \
      | datamash -t"|" transpose \
      | sed s/^sum/${d}/ \
      > ./tmp/${RCM}/${ROI}_${d}.bsv
    done

  done
done
