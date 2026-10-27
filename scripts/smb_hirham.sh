#!/usr/bin/env bash
# Extract daily SMB from HIRHAM and aggregate to Zwally sectors, Mouginot regions
# and Mouginot catchments.
# Runs in G_HIRHAM_XY (XY domain). Requires the HIRHAM_{sectors,regions,catchments}_e
# TIFs exported by setup_hirham.sh.
source ./scripts/common.sh

declare -A ZONES=([sector]=sectors_e [region]=regions_e [catchment]=catchments_e)

log_info "HIRHAM ROI areas"

RCM=HIRHAM
mkdir -p tmp/${RCM}

g.region s=0 w=0 n=441 e=300 res=1 -a

dir=${DATADIR}/${RCM}/daily

r.in.gdal -o input="NetCDF:${DATADIR}/HIRHAM/ZwallyMasks_all_SD.nc:cellarea" output=area_HIRHAM

r.in.gdal -o input=./tmp/HIRHAM_sectors_e_Zwally_2012.tif output=sectors_e
r.in.gdal -o input=./tmp/HIRHAM_regions_e_Mouginot_2019.tif output=regions_e
r.in.gdal -o input=./tmp/HIRHAM_catchments_e_Mouginot_2019.tif output=catchments_e
r.region -c map=sectors_e
r.region -c map=regions_e
r.region -c map=catchments_e

if [ "$RECENT" = "false" ] || [ -z ${RECENT} ]; then
  f_list=$(ls ${dir}/*.nc)
  log_info "Initial run. Processing all files"
else
  f_list=$(ls ${dir}/*.nc | tail -n 30)
  log_warn "RECENT set to ${RECENT}. Processing subset of files"
fi

for f in ${f_list}; do
  dates=$(python ./scripts/nc_dates.py ${f})
  band=0
  for d in ${dates}; do
    band=$(( ${band} + 1 ))

    log_info "HIRHAM: ${d}"

    # Skip the day only once every ROI has its BSV, so adding an ROI back-fills it
    todo=""
    for ROI in ${!ZONES[@]}; do
      [[ -e ./tmp/${RCM}/${ROI}_${d}.bsv ]] || todo="${todo} ${ROI}"
    done
    if [[ -z ${todo} ]]; then continue; fi

    var=smb
    if [[ ${f} == *"SMBmodel"* ]]; then var=gld; fi

    r.in.gdal -o input="NetCDF:${f}:${var}" band=${band} output=SMB_raw --o --q
    r.mapcalc "SMB = SMB_raw * area_HIRHAM" --o

    for ROI in ${todo}; do
      r.univar -t --q map=SMB zones=${ZONES[$ROI]} \
      | cut -d"|" -f1,13 \
      | datamash -t"|" transpose \
      | sed s/^sum/${d}/ \
      > ./tmp/${RCM}/${ROI}_${d}.bsv
    done

  done
done
