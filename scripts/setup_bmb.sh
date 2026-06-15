#!/usr/bin/env bash
# One-time BMB setup: computes static GF and velocity basal melt per ROI,
# then builds the hydropotential 'scale' raster used by bmb_mar.sh.
# Runs in G_MAR (EPSG:3413) using the sectors/regions established by setup_mar.sh.
source ./scripts/common.sh

# --- Geothermal flux (GF) — static, from Karlsson 2021 ---
g.mapset -c GF
r.external -o source=NetCDF:${DATADIR}/Karlsson_2021/basalmelt.nc:gfmelt output=GF_ann
g.region raster=GF_ann
r.mapcalc "GF = GF_ann / 365"

r.univar -t --q map=GF zones=sectors_e@Zwally_2012 \
  | cut -d"|" -f1,13 \
  | datamash -t"|" transpose \
  | sed s/^sum/daily/ \
  > ./tmp/BMB_GF_sector.bsv

r.univar -t --q map=GF zones=regions_e@Mouginot_2019 \
  | cut -d"|" -f1,13 \
  | datamash -t"|" transpose \
  | sed s/^sum/daily/ \
  > ./tmp/BMB_GF_region.bsv

# --- Velocity-based melt — static, from Karlsson 2021 ---
g.mapset -c vel
r.external -o source=NetCDF:${DATADIR}/Karlsson_2021/basalmelt.nc:fricmelt output=vel_ann
g.region raster=vel_ann
r.mapcalc "vel = vel_ann / 365"

# TODO: Convert vel from NBK units to m melt per grid cell?
r.univar -t --q map=vel zones=sectors_e@Zwally_2012 \
  | cut -d"|" -f1,13 \
  | datamash -t"|" transpose \
  | sed s/^sum/daily/ \
  > ./tmp/BMB_vel_sector.bsv

r.univar -t --q map=vel zones=regions_e@Mouginot_2019 \
  | cut -d"|" -f1,13 \
  | datamash -t"|" transpose \
  | sed s/^sum/daily/ \
  > ./tmp/BMB_vel_region.bsv

# --- Viscous heat dissipation (VHD) setup — BedMachine v4 (Morlighem 2017) ---
log_info "Importing BedMachine"
g.mapset -c VHD

for var in $(echo mask surface bed thickness); do
  echo $var
  r.external source=${DATADIR}/Morlighem_2017/BMv4_3413/${var}.tif output=${var}
done

g.region raster=surface
g.region res=1000
g.region save=BedMachine

r.colors map=mask color=haxby
r.mapcalc "mask_ice_0 = if(mask == 2, 1, null())"

# Expand mask by 1 cell so land-terminating glaciers have a 0-thickness outlet cell
r.grow input=mask_ice_0 output=mask_ice_1 radius=1.5 new=1
r.mapcalc "mask_01 = if((mask == 0) | (mask == 3), null(), mask_ice_1)"

# Fill nunataks and small holes so hydrologic routing reaches the ice edge
r.colors map=mask color=haxby
r.mapcalc "not_ice = if(isnull(mask_01) ||| (mask != 2), 1, 0)"
r.clump input=not_ice output=clumps
main_clump=$(r.stats -c -n clumps sort=desc | head -n1 | cut -d" " -f1)
r.mask -i raster=clumps maskcats=${main_clump} --o
r.mapcalc "all_ice = 1"
r.clump input=all_ice output=clumps2
main_clump=$(r.stats -c -n clumps2 sort=desc | head -n1 | cut -d" " -f1)
r.mask raster=clumps2 maskcats=${main_clump} --o
r.mapcalc "mask_ice = MASK"

# Subglacial hydropotential head
log_info "Calculating subglacial head with k = 1.0"
r.mapcalc "pressure = 1 * 0.917 * thickness"
r.mapcalc "head = mask_ice * bed + pressure"

# Stream network
THRESH=300
log_warn "Using threshold: ${THRESH}"
log_info "r.stream.extract..."
r.stream.extract elevation=head threshold=${THRESH} memory=16384 direction=dir stream_raster=streams stream_vector=streams

# Outlets: negative direction values mark cells that drain out of the domain
log_info "Calculating outlets"
r.mapcalc "outlets_1 = if(dir < 0, 1, null())"
r.out.xyz input=outlets_1 | \
    cat -n | \
    tr '\t' '|' | \
    cut -d"|" -f1-3 | \
    v.in.ascii input=- output=outlets_uniq separator=pipe \
        columns="x int, y int, cat int" x=2 y=3 cat=1

# Drainage basins per outlet
log_info "r.stream.basins..."
g.extension r.stream.basins url=https://trac.osgeo.org/grass/browser/grass-addons/grass7/raster/r.stream.basins
r.stream.basins -m direction=dir points=outlets_uniq basins=basins_uniq memory=16384 --verbose

# Head difference between each cell and its outlet (gravitational + pressure components)
g.extension r.stream.distance url=https://trac.osgeo.org/grass/browser/grass-addons/grass7/raster/r.stream.distance
r.stream.distance -o stream_rast=outlets_1 direction=dir elevation=head method=downstream difference=delta_head
r.stream.distance -o stream_rast=outlets_1 direction=dir elevation=bed method=downstream difference=delta_z_head
r.stream.distance -o stream_rast=outlets_1 direction=dir elevation=pressure method=downstream difference=delta_p_head

# Effective head change: 36% of pressure release warms meltwater to match PTT,
# the remaining 64% drives basal melting (Mankoff 2017, Karlsson 2021)
r.mapcalc "dh = delta_z_head + 0.64 * delta_p_head"
r.mapcalc 'q_z = (1000 * 9.8 * delta_z_head)'
r.mapcalc 'q_p = (1000 * 9.8 * 0.64 * delta_p_head)'
r.mapcalc 'q = (1000 * 9.8 * dh)'
r.mapcalc "unit_melt = q / (335 * 1000)" # 335 kJ/kg ice

# Pre-compute the static scaling factor; daily MAR runoff (ru) is multiplied
# by this in bmb_mar.sh to get daily VHD melt per cell
r.mapcalc "scale = unit_melt * (10^-3.0) * if(mask@PERMANENT > 50, (mask@PERMANENT/100), null())"
