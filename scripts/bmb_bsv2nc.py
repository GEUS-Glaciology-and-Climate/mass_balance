#!/usr/bin/env python3
# Convert BMB BSV files to a single BMB NetCDF (tmp/BMB.nc).
# Combines three components: geothermal flux (GF), velocity-based melt (vel),
# and viscous heat dissipation (VHD from MAR runoff).

import pandas as pd
import xarray as xr
import numpy as np
import datetime
import os

time = pd.date_range(start="1986-01-01",
                     end=datetime.datetime.utcnow().date() + datetime.timedelta(days=7),
                     freq="D")

BMB = xr.Dataset()
BMB["time"] = (("time"), time)

BMB["sector"] = pd.read_csv("./tmp/BMB_GF_sector.bsv", delimiter="|", nrows=0, index_col=0).columns.astype(int)

rstr = {11:'NW', 12:'NO', 1:'NE', 3:'CE', 9:'CW', 5:'SE', 7:'SW'}
rnum = pd.read_csv("./tmp/BMB_GF_region.bsv", delimiter="|", nrows=0, index_col=0).columns.astype(int)
BMB["region"] = [rstr[n] for n in rnum]

# Catchments are basin ids on the MAR grid (setup_mar.sh); map them to NAME.
# GF and vel are summed on the Karlsson grid and VHD on the MAR grid, so a small
# catchment can be missing from one of them: align on the union, zero-filled.
cnames = pd.read_csv("./tmp/MAR_catchment_names.bsv", delimiter="|", index_col=0).iloc[:, 0]
def catchment_bsv(bsv, **kw):
    df = pd.read_csv("./tmp/" + bsv + ".bsv", delimiter="|", index_col=0, **kw)
    df.columns = cnames[df.columns.astype(int)].values
    return df
cGF = catchment_bsv("BMB_GF_catchment")
cvel = catchment_bsv("BMB_vel_catchment")
cVHD = catchment_bsv("BMB_VHD_catchment", parse_dates=True).reindex(time)
BMB["catchment"] = sorted(set(cGF.columns) | set(cvel.columns) | set(cVHD.columns))

BMB['GF_sector'] = (('sector'),
                    pd.read_csv("./tmp/BMB_GF_sector.bsv",
                                delimiter="|", index_col=0).values.flatten())
BMB['vel_sector'] = (('sector'),
                     pd.read_csv("./tmp/BMB_vel_sector.bsv",
                                 delimiter="|", index_col=0).values.flatten())
BMB['VHD_sector'] = (('time', 'sector'),
                     pd.read_csv("./tmp/BMB_VHD_sector.bsv",
                                 delimiter="|", index_col=0, parse_dates=True).reindex(time))

BMB['GF_region'] = (('region'),
                    pd.read_csv("./tmp/BMB_GF_region.bsv",
                                delimiter="|", index_col=0).values.flatten())
BMB['vel_region'] = (('region'),
                     pd.read_csv("./tmp/BMB_vel_region.bsv",
                                 delimiter="|", index_col=0).values.flatten())
BMB['VHD_region'] = (('time', 'region'),
                     pd.read_csv("./tmp/BMB_VHD_region.bsv",
                                 delimiter="|", index_col=0, parse_dates=True).reindex(time))

c = BMB["catchment"].values
BMB['GF_catchment'] = (('catchment'), cGF.reindex(columns=c, fill_value=0).values.flatten())
BMB['vel_catchment'] = (('catchment'), cvel.reindex(columns=c, fill_value=0).values.flatten())
BMB['VHD_catchment'] = (('time', 'catchment'), cVHD.reindex(columns=c, fill_value=0))

# VHD is in mm w.eq / day → convert to m w.eq
for roi in ['sector', 'region', 'catchment']:
    v = 'VHD_' + roi
    BMB[v] = (('time', roi), BMB[v].data * 1E-3)

#          grid cells    m^3->kg  kg->Gt
BMB = BMB * 1000 * 1000 * 1E3    / 1E12

BMB['GF_sector_err']  = (('sector'),       BMB['GF_sector'].data  * 0.5)
BMB['vel_sector_err'] = (('sector'),       BMB['vel_sector'].data * 0.333)
BMB['VHD_sector_err'] = (('time', 'sector'), BMB['VHD_sector'].data * 0.15)
BMB['GF_region_err']  = (('region'),       BMB['GF_region'].data  * 0.5)
BMB['vel_region_err'] = (('region'),       BMB['vel_region'].data * 0.333)
BMB['VHD_region_err'] = (('time', 'region'), BMB['VHD_region'].data * 0.15)
BMB['GF_catchment_err']  = (('catchment'),       BMB['GF_catchment'].data  * 0.5)
BMB['vel_catchment_err'] = (('catchment'),       BMB['vel_catchment'].data * 0.333)
BMB['VHD_catchment_err'] = (('time', 'catchment'), BMB['VHD_catchment'].data * 0.15)

fn = './tmp/BMB.nc'
if os.path.exists(fn): os.remove(fn)
BMB.to_netcdf(fn)

print(BMB)
