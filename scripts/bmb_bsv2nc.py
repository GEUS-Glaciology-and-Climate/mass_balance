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

# VHD is in mm w.eq / day → convert to m w.eq
for roi in ['sector', 'region']:
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

fn = './tmp/BMB.nc'
if os.path.exists(fn): os.remove(fn)
BMB.to_netcdf(fn)

print(BMB)
