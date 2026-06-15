#!/usr/bin/env python3
# Convert per-RCM BSV files to a single SMB NetCDF (tmp/SMB.nc).
# HIRHAM resolution is in degrees; 0.5 arcmin ≈ 921 m at ~10°N rotated pole.
# Grid cell areas are pre-multiplied in smb_hirham.sh via the ZwallyMasks cellarea field.

import pandas as pd
import xarray as xr
import numpy as np
import datetime
import os
import uncertainties
from uncertainties import unumpy

time = pd.date_range(start="1986-01-01",
                     end=datetime.datetime.utcnow().date() + datetime.timedelta(days=7),
                     freq="D")

SMB = xr.Dataset()
SMB["time"] = (("time"), time)

SMB["sector"] = pd.read_csv("./tmp/HIRHAM_sector.bsv", delimiter="|", nrows=0, index_col=0).columns.astype(int)

rstr = {11:'NW', 12:'NO', 1:'NE', 3:'CE', 9:'CW', 5:'SE', 7:'SW'}
rnum = pd.read_csv("./tmp/HIRHAM_region.bsv", delimiter="|", nrows=0, index_col=0).columns.astype(int)
SMB["region"] = [rstr[n] for n in rnum]


def bsv2nc(SMB, bsv, dim):
    df = pd.read_csv("./tmp/" + bsv + ".bsv", delimiter="|", index_col=0, parse_dates=True).reindex(time)
    df.columns = df.columns.astype(np.int64)
    if dim == "region":
        df.columns = [rstr[n] for n in df.columns]
    missing = SMB[dim].values[~pd.Series(SMB[dim].values).isin(df.columns)]
    if len(missing) > 0:
        df[missing] = np.nan
        df = df.reindex(sorted(df.columns), axis=1)

    if 'HIRHAM' in bsv:
        # Grid areas already applied via 'r.mapcalc "SMB = SMB_raw * area_HIRHAM"'
        grid = 1
        error = 0.15
    if 'MAR' in bsv:
        grid = 1000 * 1000
        error = 0.15
    if 'RACMO' in bsv:
        grid = 1000 * 1000
        error = 0.15

    #       mm->m  grid  m^3->kg  kg->Gt
    CONV = 1E-3  * grid * 1E3    / 1E12
    df = df * CONV

    SMB[bsv] = (("time", dim), df)
    SMB[bsv + '_err'] = (("time", dim), df * error)
    return SMB


SMB = bsv2nc(SMB, "HIRHAM_sector", "sector")
SMB = bsv2nc(SMB, "HIRHAM_region", "region")

SMB = bsv2nc(SMB, "MAR_sector", "sector")
SMB = bsv2nc(SMB, "MAR_region", "region")

SMB = bsv2nc(SMB, "RACMO_sector", "sector")
SMB = bsv2nc(SMB, "RACMO_region", "region")


err = unumpy.uarray([1, 1, 1], [0.1, 0.15, 0.7])
print('{:.4f}'.format(err.sum()))

# Ensemble mean across HIRHAM and MAR (RACMO excluded until regularly updated)
for roi in ['sector', 'region']:
    mean = SMB[['HIRHAM_'+roi, 'MAR_'+roi]].to_array(dim='m').mean('m')
    s = 'SMB_mean_' + roi
    SMB[s] = (('time', roi), mean.data)
    SMB[s + '_err'] = (('time', roi), mean.data * 0.15)
    for RCM in ['HIRHAM', 'MAR']:
        s = 'SMB_'+RCM+'_' + roi
        SMB[s] = (('time', roi), SMB[RCM+'_'+roi].data)
        SMB[s + '_err'] = (('time', roi), SMB[RCM+'_'+roi].data * 0.15)

for RCM in ['mean', 'HIRHAM', 'MAR']:
    SMB['SMB_'+RCM] = (('time'), SMB['SMB_'+RCM+'_sector'].sum(dim='sector').data)
    SMB['SMB_'+RCM+'_err'] = (('time'), SMB['SMB_'+RCM+'_sector'].sum(dim='sector').data * 0.09)

fn = './tmp/SMB.nc'
if os.path.exists(fn): os.remove(fn)
SMB.to_netcdf(fn)
