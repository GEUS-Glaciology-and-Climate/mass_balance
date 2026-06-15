#!/usr/bin/env bash
source ./scripts/common.sh

g.region w=-13.65 e=1.3 s=-9.8 n=12.2 res=0:03
g.region w=w-0.025 e=e+0.025 s=s-0.025 n=n+0.025 -p
g.region save=RCM
g.region res=0:0.5 # ~1 km grid cell resolution
g.region save=sectors --o

# Load ROI shapefiles pre-converted to HIRHAM rotated-pole coordinates
log_info "Loading Zwally 2012"
g.mapset -c Zwally_2012
v.in.ogr -o input=Zwally_2012_HIRHAM.gpkg output=sectors
v.db.dropcolumn map=sectors columns="cat_"
v.db.renamecolumn map=sectors column=cat__1,cat_

log_info "Loading Mouginot 2019"
g.mapset -c Mouginot_2019
v.in.ogr -o input=Mouginot_2019_HIRHAM.gpkg output=basins
db.execute sql="DELETE FROM basins WHERE name LIKE 'ICE_CAPS_%'"
v.db.addcolumn map=basins columns="SUBREGION1_num INT"
db.execute sql="UPDATE basins SET SUBREGION1_num=11 WHERE SUBREGION1='NW'"
db.execute sql="UPDATE basins SET SUBREGION1_num=12 WHERE SUBREGION1='NO'"
db.execute sql="UPDATE basins SET SUBREGION1_num=1 WHERE SUBREGION1='NE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=3 WHERE SUBREGION1='CE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=9 WHERE SUBREGION1='CW'"
db.execute sql="UPDATE basins SET SUBREGION1_num=5 WHERE SUBREGION1='SE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=7 WHERE SUBREGION1='SW'"
g.mapset PERMANENT

# Ice mask: main ice sheet only (largest cluster), no peripheral glaciers
r.in.gdal -ol input="NetCDF:${DATADIR}/HIRHAM/GL2offline_CountryGlacierMasks_SD.nc:glacGRL" output=mask
r.region map=mask region=RCM
r.mapcalc "mask_ice_all = if(mask == 1, 1, null())"
r.clump input=mask_ice_all output=mask_ice_clump
main_clump=$(r.stats -c -n mask_ice_clump sort=desc | head -n1 | cut -d" " -f1)
r.mapcalc "mask_ice = if(mask_ice_clump == ${main_clump}, 1, null())"

# Expand sectors/basins to cover the full model domain (no ice left unassigned)
log_info "Expanding Zwally sectors to cover RCM domain"
g.mapset Zwally_2012
g.region region=sectors
v.to.rast input=sectors output=sectors use=attr attribute_column=cat_
r.grow.distance input=sectors value=value
r.mapcalc "sectors_e = if(mask_ice, int(value), null())"
r.to.vect input=sectors_e output=sectors_e type=area

log_info "Expanding Mouginot basins to cover RCM domain"
g.mapset Mouginot_2019
g.region region=sectors
v.to.rast input=basins output=basins use=attr attribute_column=cat_ labelcolumn=SUBREGION1
r.grow.distance input=basins value=value_b
r.mapcalc "basins_e = if(mask_ice, int(value_b), null())"
r.category map=basins separator=":" > ./tmp/basins_cats
r.category map=basins_e separator=":" rules=./tmp/basins_cats
r.to.vect input=basins_e output=basins_e type=area

v.to.rast input=basins output=regions use=attr attribute_column=SUBREGION1_num labelcolumn=SUBREGION1
r.grow.distance input=regions value=value_r
r.mapcalc "regions_e = if(mask_ice, int(value_r), null())"
r.category map=regions separator=":" > ./tmp/region_cats
r.category map=regions_e separator=":" rules=./tmp/region_cats
r.to.vect input=regions_e output=regions_e type=area

# Export ROI rasters for use in the HIRHAM XY domain (smb_hirham.sh loads these)
mkdir -p tmp
r.out.gdal input=sectors_e@Zwally_2012 output=./tmp/HIRHAM_sectors_e_Zwally_2012.tif
r.out.gdal input=regions_e@Mouginot_2019 output=./tmp/HIRHAM_regions_e_Mouginot_2019.tif
