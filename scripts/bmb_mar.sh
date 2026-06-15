#!/usr/bin/env bash
# Compute daily viscous heat dissipation (VHD) basal melt from MAR runoff.
# Requires the 'scale' raster produced by setup_bmb.sh.
# Runs in G_MAR (EPSG:3413).
source ./scripts/common.sh

g.mapset -c VHD

RCM=MAR
mkdir -p tmp/BMB

dir=${DATADIR}/${RCM}/3.12

if [ "$RECENT" = "false" ] || [ -z ${RECENT} ]; then
  f_list=$(ls ${dir}/*.nc)
  log_info "Initial run. Processing all files"
else
  f_list=$(ls ${dir}/*.nc | tail -n 2)
  log_warn "RECENT set to ${RECENT}. Processing subset of files"
fi

for f in ${f_list}; do
  dates=$(python3 ./scripts/nc_dates.py ${f})
  band=-1
  for d in ${dates}; do
    band=$(( ${band} + 2 ))

    log_info "MAR BMB: ${d} (band: ${band})"

    if [[ -e ./tmp/BMB/sector_${d}.bsv ]]; then continue; fi

    r.in.gdal -o input="NetCDF:${f}:ru" band=${band} output=ru_raw --o --q
    r.region map=ru_raw region=RCM

    r.mapcalc "vhd = scale * ru_raw" --o
    r.null map=vhd null=0

    r.univar -t --q map=vhd zones=sectors_e@Zwally_2012 \
    | cut -d"|" -f1,13 \
    | datamash -t"|" transpose \
    | sed s/^sum/${d}/ \
    > ./tmp/BMB/sector_${d}.bsv

    r.univar -t --q map=vhd zones=regions_e@Mouginot_2019 \
    | cut -d"|" -f1,13 \
    | datamash -t"|" transpose \
    | sed s/^sum/${d}/ \
    > ./tmp/BMB/region_${d}.bsv

  done
done
