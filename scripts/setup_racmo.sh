#!/usr/bin/env bash
source ./scripts/common.sh

g.region w=-638956 e=856044 s=-3354596 n=-655596 res=1000 -p
g.region n=n+500 s=s-500 w=w-500 e=e+500 res=1000 -p
g.region save=RCM
g.region res=1000 -p
g.region save=sectors

# Ice mask: Promicemask >= 2 (ice sheet cells), main contiguous cluster only
r.external -o source=NetCDF:${DATADIR}/RACMO/Icemask_Topo_Iceclasses_lon_lat_average_1km.nc:Promicemask output=mask
r.region map=mask region=RCM
r.colors map=mask color=haxby
r.mapcalc "mask_ice_all = if(mask >= 2, 1, null())"
r.clump input=mask_ice_all output=mask_clump
main_clump=$(r.stats -c -n mask_clump sort=desc | head -n1 | cut -d" " -f1)
r.mapcalc "mask_ice = if((mask_clump == ${main_clump}) & (mask > 0.5), 1, null())"

log_info "Loading Zwally 2012"
g.mapset -c Zwally_2012
v.import input=${DATADIR}/Zwally_2012/sectors output=sectors snap=1

log_info "Expanding Zwally sectors to cover RCM domain"
g.mapset Zwally_2012
g.region region=sectors
v.to.rast input=sectors output=sectors use=attr attribute_column=cat_
r.grow.distance input=sectors value=value
r.mapcalc "sectors_e = if(mask_ice, int(value), null())"
r.to.vect input=sectors_e output=sectors_e type=area

log_info "Loading Mouginot 2019"
g.mapset -c Mouginot_2019
v.import input=${DATADIR}/Mouginot_2019/Greenland_Basins_PS_v1.4.2.shp output=basins snap=1
db.execute sql="DELETE FROM basins WHERE name LIKE 'ICE_CAPS_%'"
v.db.addcolumn map=basins columns="SUBREGION1_num INT,cat_ INT"
db.execute sql="UPDATE basins SET cat_=cat"
db.execute sql="UPDATE basins SET SUBREGION1_num=11 WHERE SUBREGION1='NW'"
db.execute sql="UPDATE basins SET SUBREGION1_num=12 WHERE SUBREGION1='NO'"
db.execute sql="UPDATE basins SET SUBREGION1_num=1 WHERE SUBREGION1='NE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=3 WHERE SUBREGION1='CE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=9 WHERE SUBREGION1='CW'"
db.execute sql="UPDATE basins SET SUBREGION1_num=5 WHERE SUBREGION1='SE'"
db.execute sql="UPDATE basins SET SUBREGION1_num=7 WHERE SUBREGION1='SW'"

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

g.mapset PERMANENT
