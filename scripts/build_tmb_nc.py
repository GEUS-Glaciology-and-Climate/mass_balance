#!/usr/bin/env python3
# Assemble Total Mass Balance (TMB) from SMB, D (ice discharge), BMB, and the
# Kjeldsen 2015 historical reconstruction. Forecasts D 7 days forward.
# Outputs NetCDF files to TMB/ for each ROI type (sector, region).

import pandas as pd
import os
DATADIR = os.environ['DATADIR']
fname = 'Greenland_mass_balance_totals_1840-2012_ver_20141130_with_uncert_via_Kjeldsen_et_al_2015.csv'
k2015 = pd.read_csv(DATADIR + '/Kjeldsen_2015/' + fname, index_col=0, parse_dates=True)\
          .rename(columns={'discharge from 6 year lagged average runoff' : 'D',
                           'discharge 1sigma' : 'D_err'})

k2015.index.name = 'time'

k2015['SMB'] = k2015['accumulation'] - k2015['runoff']
k2015['SMB_err'] = (k2015['accumulation 1sigma']**2 + k2015['runoff 1sigma']**2)**0.5

k2015 = k2015.drop(columns=['accumulation', 'accumulation 1sigma',
                            'melt', 'melt 1sigma', 'retention',
                            'retention 1sigma',
                            # 'runoff', 'runoff 1sigma',
                            'TMB', 'TMB 1sigma'])
import numpy as np
import xarray as xr
import datetime
import pandas as pd
SMB = xr.open_dataset("./tmp/SMB.nc")
SMB['region'] = SMB['region'].astype(str)
import xarray as xr
import os
DATADIR = os.environ['DATADIR']
ds = xr.open_dataset(DATADIR + "/Mankoff_2020/ice/latest/gate.nc")

# ds = xr.open_dataset("/home/kdm/projects/ice_discharge/out/gate.nc")

# rstr = {'NW':11, 'NO':12, 'NE':1, 'CE':3, 'CW':9, 'SE':5, 'SW':7}
# rnum = [rstr[r] for r in ds['region'].values]
# ds['region'] = (('gate'), rnum)

ds_sector = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","sector","region","coverage", "ID_Moon", "ID_Moon_dist"])\
          .groupby("Zwally_2012")\
          .sum()\
          .rename({"Zwally_2012":"sector",
                   "discharge":"D_sector",
                   "err":"err_sector"})

ds_region = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","sector","Zwally_2012","coverage", "ID_Moon", "ID_Moon_dist"])\
          .groupby("region")\
          .sum()\
          .rename({"discharge":"D_region",
                   "err":"err_region"})


# ds_basin = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","Zwally_2012","region","coverage"])\
#           .groupby("sector")\
#           .sum()\
#           .rename({"sector":"basin",
#                    "discharge":"D_basin",
#                    "err":"err_basin"})

D = ds_sector
D = D.merge(ds_region, compat='override')
# D = D.merge(ds_basin)

D['D'] = (('time'), D['D_sector'].sum(dim='sector').data)
D['D_err'] = (('time'), D['err_sector'].sum(dim='sector').data)

# convert from Gt/year @ misc time-steps -> Gt/day @ daily timestep
msave = D.copy(deep=True)
D = (D / 365).resample({"time":"1D"})\
                 .mean()\
                 .interpolate_na(dim="time")

# I want monotonic cubic interpolation for discharge
D['D'] = (('time'), (msave['D']/365).resample({'time':'1D'}).mean().to_dataframe().interpolate(method='pchip').values.flatten())
D['region'] = D['region'].astype(str)

import numpy as np
import pandas as pd
import xarray as xr
import scipy as sp
import scipy.stats
import scipy.signal

time_start = '1986-01-01'
# time_first_obs = D['time'][0].values
time_last_obs = D['time'][-1].values
time_forecast_start = pd.Timestamp(time_last_obs) + datetime.timedelta(days=1)
time_forecast_end = datetime.datetime.utcnow().date() + datetime.timedelta(days = 7)

time_index_all = pd.date_range(start=time_start, end=time_forecast_end, freq='D')
time_index_last3y = pd.date_range(start = pd.Timestamp(time_last_obs) - datetime.timedelta(days=365*3), end=time_last_obs, freq='D')
time_index_forecast = pd.date_range(start = time_forecast_start, end=time_forecast_end, freq='D')
time_index_hindcast = np.concatenate([time_index_forecast - datetime.timedelta(days=365*3),
                                      time_index_forecast - datetime.timedelta(days=365*2),
                                      time_index_forecast - datetime.timedelta(days=365*1)])

D_fc = D.reindex({'time':time_index_all})

# https://gist.github.com/rabernat/1ea82bb067c3273a6166d1b1f77d490f
def detrend_dim(da, dim, deg=1):
    # detrend along a single dimension
    p = da.polyfit(dim=dim, deg=deg)
    fit = xr.polyval(da[dim], p.polyfit_coefficients)
    return fit,p

for v in ['D_sector','D_region','D']:
    # trend is linear long term trend of last 3 years of observations.
    last3_plus_forecast = D_fc[v].sel({'time':slice(time_index_last3y[0],time_forecast_end)})
    trend, _ = detrend_dim(last3_plus_forecast, 'time')

    # season is the average of (the detrended values of forecasted calendar dates for the past 3 years starting at 0)
    season = (last3_plus_forecast - trend).reindex({'time':time_index_hindcast})
    # Find the average trend of the last 3 seasons
    last3_break = np.where(np.diff(season['time'].values).astype('timedelta64[D]').astype(int) > 1)[0]+1
    last3_3 = season.isel({'time':slice(0,last3_break[0])})
    last3_2 = season.isel({'time':slice(last3_break[0],last3_break[1])})
    last3_1 = season.isel({'time':slice(last3_break[1],999)})

    last3_3 = last3_3 - last3_3.isel({'time':0}) # start forecast at 0
    last3_2 = last3_2 - last3_2.isel({'time':0})
    last3_1 = last3_1 - last3_1.isel({'time':0})
    season_trend = xr.zeros_like(last3_3.reindex(time=time_index_forecast))
    season_trend.data = (last3_3.values + last3_2.values + last3_1.values)/3

    # forecast is the long term trend adjusted to start from the last observed,
    # then cropped to the last timestamp, then seasonality added, then gap-filled
    forecast = trend.reindex({'time':time_index_forecast})
    forecast = forecast - forecast.isel(time=0) + D[v].isel({'time':-1}) + forecast.diff(dim='time').isel({'time':-1})
    forecast = forecast + season_trend
    D_fc[v] = xr.concat([D[v],forecast], dim='time') # .interp(time=time_index_all)

    vv = {'D':'D_err', 'D_sector':'err_sector', 'D_region':'err_region'}[v]
    e = xr.ones_like(D_fc[vv].sel({'time':time_index_forecast})).cumsum(dim='time')/100
    baseline_err = D_fc[vv].dropna(dim='time').mean(dim='time')
    e = baseline_err * e
    e = e.reindex({'time':time_index_all})
    e = e.where(~e.isnull(), other=0)
    D_fc[vv] = D_fc[vv].ffill(dim='time') + e
    
D_fc = D_fc.bfill(dim='time')
D = D_fc

time = pd.date_range(start = "1986-01-01", end = str(D['time'].values[-1]), freq = "D")
D = D.reindex({'time':time}).bfill(dim='time')

SMB = SMB[['SMB_mean','SMB_mean_err']].resample({'time':'YS'}).sum().sel({'time':slice('1986','2012')}).to_dataframe()
D = D[['D','D_err']].resample({'time':'YS'}).sum().sel({'time':slice('1986','2012')}).to_dataframe()

k2015_overlap = k2015.loc['1986':'2012']

import scipy as sp
import scipy.stats as sps

slope, intercept, r_value, p_value, std_err = sps.linregress(SMB['SMB_mean'].values,
                                                             k2015_overlap['SMB'].values)
k2015 = k2015.rename(columns={'SMB':'SMB_orig'})
k2015['SMB'] = (k2015['SMB_orig'] - intercept)/slope
k2015['SMB_err'] = (k2015['SMB_err'] + SMB['SMB_mean_err'].mean())

slope, intercept, r_value, p_value, std_err = sps.linregress(D['D'].values,
                                                             k2015_overlap['D'].values)
k2015 = k2015.rename(columns={'D':'D_orig'})
k2015['D'] = (k2015['D_orig'] - intercept)/slope
k2015['D_err'] = (k2015['D_err'] + D['D_err'].mean())


## Add BMB
import numpy as np
import xarray as xr
import datetime
import pandas as pd

BMB = xr.open_dataset('./tmp/BMB.nc')
BMB['region'] = BMB['region'].astype(str)

BMB['BMB'] = (('time'), (BMB['GF_sector'] \
                         + BMB['vel_sector'] \
                         + BMB['VHD_sector']).sum(dim='sector').data)

BMB['BMB_err'] = (('time'), ((BMB['GF_sector_err']**2 \
                              + BMB['vel_sector_err']**2 \
                              + BMB['VHD_sector_err']**2)**0.5).sum(dim='sector').data)

BMB['BMB_sector'] = (('time','sector'), BMB['VHD_sector'].data + BMB['GF_sector'].data + BMB['vel_sector'].data)
BMB['BMB_region'] = (('time','region'), BMB['VHD_region'].data + BMB['GF_region'].data + BMB['vel_region'].data)
# BMB['BMB_basin'] = BMB['VHD_basin'] + BMB['GF_basin'] + BMB['vel_basin']

BMB['BMB_sector_err'] = (('time','sector'), \
                         ((BMB['GF_sector_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + (BMB['vel_sector_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + BMB['VHD_sector_err'].data**2\
                          )**0.5\
                         )

BMB['BMB_region_err'] = (('time','region'), \
                         ((BMB['GF_region_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + (BMB['vel_region_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + BMB['VHD_region_err'].data**2\
                          )**0.5\
                         )

# print(BMB)
BMB[['VHD_sector','GF_sector','vel_sector','BMB']].sum(dim='sector').to_dataframe().resample('MS').sum().head(12)

# constant or time invariant:
BMB_C = BMB[['GF_sector','vel_sector','GF_sector_err','vel_sector_err']]\
    .to_dataframe()\
    .sum(axis='index')

# VHD is time variable.
v = BMB[['VHD_sector','VHD_sector_err']]\
    .resample({'time':'YS'})\
    .sum()\
    .sum(dim='sector')\
    .to_dataframe()

vr = v.merge(k2015['runoff'], left_index=True, right_index=True)
slope, intercept, r_value, p_value, std_err = sps.linregress(vr['runoff'].values,
                                                             vr['VHD_sector'].values)

print('slope: ', slope)
print('intercept: ', intercept)
print('r^2: ', r_value**2)
print('p: ', p_value)
print('std_err :', std_err)

k2015['BMB_GF'] = BMB_C['GF_sector']*365
k2015['BMB_GF_err'] = BMB_C['GF_sector_err']*365
k2015['BMB_vel'] = BMB_C['vel_sector']*365
k2015['BMB_vel_err'] = BMB_C['vel_sector_err']*365

k2015['BMB_VHD'] = (k2015['runoff']) * slope
k2015['BMB_VHD_err'] = (k2015['runoff 1sigma']) * slope

k2015[[_ for _ in k2015.columns if '_' in _ ]].head()

k2015['BMB'] = k2015[['BMB_GF','BMB_vel','BMB_VHD']].sum(axis='columns')
k2015['BMB_err'] = (k2015['BMB_GF']**2 \
                  + k2015['BMB_vel']**2 \
                  + k2015['BMB_VHD']**2)**0.5

k2015['MB'] = k2015['SMB'] - k2015['D'] - k2015['BMB']

k2015 = k2015.loc['1840':'1986']
# k2015 = k2015.loc['1840':'1986'].resample('1D').ffill().iloc[:-1] # cut off 1986-01-01
k2015 = k2015.loc['1840':'1986'].iloc[:-1] # cut off 1986-01-01



import numpy as np
import xarray as xr
import datetime
import pandas as pd
SMB = xr.open_dataset("./tmp/SMB.nc")
SMB['region'] = SMB['region'].astype(str)
# Trim trailing zero-filled forecast days (MAR provides timestamps beyond real data)
last_real = int(np.where(SMB['SMB_MAR'].values != 0)[0][-1])
SMB = SMB.isel(time=slice(None, last_real + 1))
time = np.append(k2015.index, SMB['time'].values)
SMB = SMB.reindex({'time':time})
for RCM in ['mean', 'HIRHAM', 'MAR']:
    SMB['SMB_' + RCM] = (('time'),
              np.append(k2015['SMB'].values/365, SMB['SMB_'+RCM].sel({'time':slice('1986','2200')}).values))
    SMB['SMB_'+RCM+'_err'] = (('time'),
                  np.append(k2015['SMB_err'].values/365, SMB['SMB_'+RCM+'_err'].sel({'time':slice('1986','2200')}).values))




import xarray as xr
import os
DATADIR = os.environ['DATADIR']
ds = xr.open_dataset(DATADIR + "/Mankoff_2020/ice/latest/gate.nc")

# ds = xr.open_dataset("/home/kdm/projects/ice_discharge/out/gate.nc")

# rstr = {'NW':11, 'NO':12, 'NE':1, 'CE':3, 'CW':9, 'SE':5, 'SW':7}
# rnum = [rstr[r] for r in ds['region'].values]
# ds['region'] = (('gate'), rnum)

ds_sector = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","sector","region","coverage", "ID_Moon", "ID_Moon_dist"])\
          .groupby("Zwally_2012")\
          .sum()\
          .rename({"Zwally_2012":"sector",
                   "discharge":"D_sector",
                   "err":"err_sector"})

ds_region = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","sector","Zwally_2012","coverage", "ID_Moon", "ID_Moon_dist"])\
          .groupby("region")\
          .sum()\
          .rename({"discharge":"D_region",
                   "err":"err_region"})


# ds_basin = ds.drop_vars(["mean_x","mean_y","mean_lon","mean_lat","Zwally_2012","region","coverage"])\
#           .groupby("sector")\
#           .sum()\
#           .rename({"sector":"basin",
#                    "discharge":"D_basin",
#                    "err":"err_basin"})

D = ds_sector
D = D.merge(ds_region, compat='override')
# D = D.merge(ds_basin)

D['D'] = (('time'), D['D_sector'].sum(dim='sector').data)
D['D_err'] = (('time'), D['err_sector'].sum(dim='sector').data)

# convert from Gt/year @ misc time-steps -> Gt/day @ daily timestep
msave = D.copy(deep=True)
D = (D / 365).resample({"time":"1D"})\
                 .mean()\
                 .interpolate_na(dim="time")

# I want monotonic cubic interpolation for discharge
D['D'] = (('time'), (msave['D']/365).resample({'time':'1D'}).mean().to_dataframe().interpolate(method='pchip').values.flatten())
D['region'] = D['region'].astype(str)

import numpy as np
import pandas as pd
import xarray as xr
import scipy as sp
import scipy.stats
import scipy.signal

time_start = '1986-01-01'
# time_first_obs = D['time'][0].values
time_last_obs = D['time'][-1].values
time_forecast_start = pd.Timestamp(time_last_obs) + datetime.timedelta(days=1)
time_forecast_end = datetime.datetime.utcnow().date() + datetime.timedelta(days = 7)

time_index_all = pd.date_range(start=time_start, end=time_forecast_end, freq='D')
time_index_last3y = pd.date_range(start = pd.Timestamp(time_last_obs) - datetime.timedelta(days=365*3), end=time_last_obs, freq='D')
time_index_forecast = pd.date_range(start = time_forecast_start, end=time_forecast_end, freq='D')
time_index_hindcast = np.concatenate([time_index_forecast - datetime.timedelta(days=365*3),
                                      time_index_forecast - datetime.timedelta(days=365*2),
                                      time_index_forecast - datetime.timedelta(days=365*1)])

D_fc = D.reindex({'time':time_index_all})

# https://gist.github.com/rabernat/1ea82bb067c3273a6166d1b1f77d490f
def detrend_dim(da, dim, deg=1):
    # detrend along a single dimension
    p = da.polyfit(dim=dim, deg=deg)
    fit = xr.polyval(da[dim], p.polyfit_coefficients)
    return fit,p

for v in ['D_sector','D_region','D']:
    # trend is linear long term trend of last 3 years of observations.
    last3_plus_forecast = D_fc[v].sel({'time':slice(time_index_last3y[0],time_forecast_end)})
    trend, _ = detrend_dim(last3_plus_forecast, 'time')

    # season is the average of (the detrended values of forecasted calendar dates for the past 3 years starting at 0)
    season = (last3_plus_forecast - trend).reindex({'time':time_index_hindcast})
    # Find the average trend of the last 3 seasons
    last3_break = np.where(np.diff(season['time'].values).astype('timedelta64[D]').astype(int) > 1)[0]+1
    last3_3 = season.isel({'time':slice(0,last3_break[0])})
    last3_2 = season.isel({'time':slice(last3_break[0],last3_break[1])})
    last3_1 = season.isel({'time':slice(last3_break[1],999)})

    last3_3 = last3_3 - last3_3.isel({'time':0}) # start forecast at 0
    last3_2 = last3_2 - last3_2.isel({'time':0})
    last3_1 = last3_1 - last3_1.isel({'time':0})
    season_trend = xr.zeros_like(last3_3.reindex(time=time_index_forecast))
    season_trend.data = (last3_3.values + last3_2.values + last3_1.values)/3

    # forecast is the long term trend adjusted to start from the last observed,
    # then cropped to the last timestamp, then seasonality added, then gap-filled
    forecast = trend.reindex({'time':time_index_forecast})
    forecast = forecast - forecast.isel(time=0) + D[v].isel({'time':-1}) + forecast.diff(dim='time').isel({'time':-1})
    forecast = forecast + season_trend
    D_fc[v] = xr.concat([D[v],forecast], dim='time') # .interp(time=time_index_all)

    vv = {'D':'D_err', 'D_sector':'err_sector', 'D_region':'err_region'}[v]
    e = xr.ones_like(D_fc[vv].sel({'time':time_index_forecast})).cumsum(dim='time')/100
    baseline_err = D_fc[vv].dropna(dim='time').mean(dim='time')
    e = baseline_err * e
    e = e.reindex({'time':time_index_all})
    e = e.where(~e.isnull(), other=0)
    D_fc[vv] = D_fc[vv].ffill(dim='time') + e
    
D_fc = D_fc.bfill(dim='time')
D = D_fc
# dt_last_obs = D['time'].values[-1]
# err = []
# for dt in pd.date_range(start=dt_last_obs, end=time[-1]):
#     std = D['D'].sel(time=(D['time.month'] == dt.month) & (D['time.day'] == dt.day)).std().values
#     # print(std)
#     err_today = max(max(err), 2*std) if dt != dt_last_obs else 2*std
#     err.append(err_today)

D = D.reindex({'time':time})
D['D'] = (('time'),
              np.append(k2015['D'].values/365, D['D'].sel({'time':slice('1986','2200')}).values))
D['D_err'] = (('time'),
              np.append(k2015['D_err'].values/365, D['D_err'].sel({'time':slice('1986','2200')}).values))
# D['D_err'] = (('time'),
#                   np.hstack((k2015['D_err'].values/365,
#                              D['D_err'].sel({'time':slice('1986',dt_last_obs)}).to_dataframe().values,
#                              err[1:])).ravel())


import numpy as np
import xarray as xr
import datetime
import pandas as pd

BMB = xr.open_dataset('./tmp/BMB.nc')
BMB['region'] = BMB['region'].astype(str)

BMB['BMB'] = (('time'), (BMB['GF_sector'] \
                         + BMB['vel_sector'] \
                         + BMB['VHD_sector']).sum(dim='sector').data)

BMB['BMB_err'] = (('time'), ((BMB['GF_sector_err']**2 \
                              + BMB['vel_sector_err']**2 \
                              + BMB['VHD_sector_err']**2)**0.5).sum(dim='sector').data)

BMB['BMB_sector'] = (('time','sector'), BMB['VHD_sector'].data + BMB['GF_sector'].data + BMB['vel_sector'].data)
BMB['BMB_region'] = (('time','region'), BMB['VHD_region'].data + BMB['GF_region'].data + BMB['vel_region'].data)
# BMB['BMB_basin'] = BMB['VHD_basin'] + BMB['GF_basin'] + BMB['vel_basin']

BMB['BMB_sector_err'] = (('time','sector'), \
                         ((BMB['GF_sector_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + (BMB['vel_sector_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + BMB['VHD_sector_err'].data**2\
                          )**0.5\
                         )

BMB['BMB_region_err'] = (('time','region'), \
                         ((BMB['GF_region_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + (BMB['vel_region_err'].expand_dims({'time':BMB['time'].size}).data)**2 \
                          + BMB['VHD_region_err'].data**2\
                          )**0.5\
                         )

# print(BMB)
BMB[['VHD_sector','GF_sector','vel_sector','BMB']].sum(dim='sector').to_dataframe().resample('MS').sum().head(12)
BMB = BMB.reindex({'time':time}).fillna(0)
BMB['BMB'] = (('time'),
              np.append(k2015['BMB'].values/365, BMB['BMB'].sel({'time':slice('1986','2200')}).values))
BMB['BMB_err'] = (('time'),
                  np.append(k2015['BMB_err'].values/365, BMB['BMB_err'].sel({'time':slice('1986','2200')}).values))


# add the sectors from SMB to D (14 and 21(?) don't have any D)
D = D.reindex({'sector': SMB['sector']})# .fillna(0)
# D = D.reindex({'basin': SMB['basin']})# .fillna(0)
D = D.reindex({'region': SMB['region']})# .fillna(0)
D['region'] = D['region'].astype(str)
D = D.ffill(dim='time')
D = D.bfill(dim='time')



# #+RESULTS:
# : slope:  0.02779523106638524
# : intercept:  -3.204674758436137
# : r^2:  0.7503894036942795
# : p:  5.267031413783773e-09
# : std_err : 0.003206184032882044


import subprocess
import os

for roi in ['sector', 'region']: # TODO: 'basin'
    MB = xr.Dataset()
    
    MB["time"] = (("time"), time)
    MB["time"].attrs["cf_role"] = "timeseries_id"
    MB["time"].attrs["standard_name"] = "time"
    MB["time"].attrs["axis"] = "T"

    # First make the mean MB columns (index only time not roi)
    for RCM in ['mean', 'HIRHAM', 'MAR']:
        MB_hist = (k2015['SMB'] - k2015['D'] - k2015['BMB'])/365
        MB_recent = (SMB['SMB_'+RCM] - D['D'] - BMB['BMB']).to_dataframe('MB').loc['1986':]['MB']

        MB['MB_'+RCM] = (('time'), MB_hist._append(MB_recent))
        MB['MB_'+RCM+'_err'] = (('time'), (SMB['SMB_'+RCM+'_err'].data**2 + D['D_err'].data**2 + BMB['BMB_err'].data**2)**0.5)

        v = 'MB_' + RCM
        MB[v].attrs["long_name"] = "Mass balance"
        MB[v].attrs["standard_name"] = "land_ice_mass_transport"
        MB[v].attrs["units"] = "Gt d-1"
        MB[v].attrs["coordinates"] = 'time'

    MB = MB.rename({
        'MB_mean': 'MB',
        'MB_mean_err': 'MB_err'})
    
    MB[roi] = ((roi), D[roi].astype(str).data)

    if roi == 'sector':
        MB[roi].attrs["long_name"] = "Zwally 2012 sectors"
    elif roi == 'region':
        MB[roi].attrs["long_name"] = "Mouginot 2019 regions"
    elif roi == 'basin':
        MB[roi].attrs["long_name"] = "Mouginot 2019 basins"
       
    MB['MB_ROI'] = (('time',roi), (SMB['SMB_mean_' + roi] - D['D_'+roi] - BMB['BMB_'+roi]).data)
    MB['MB_ROI_err'] = (('time',roi), (SMB['SMB_mean_'+roi+'_err'].data**2 + D['err_'+roi].data**2 + BMB['BMB_'+roi+'_err'].data**2)**0.5)

    v = 'MB'
    MB[v].attrs['long_name'] = 'Mass balance mean of HIRHAM and MAR'
    MB[v].attrs["standard_name"] = "land_ice_mass_transport"
    MB[v].attrs["units"] = "Gt d-1"
    MB[v].attrs["coordinates"] = 'time ' + roi
        
    for RCM in ['HIRHAM', 'MAR']:
        MB['MB_'+RCM+'_ROI'] = (('time',roi), (SMB[RCM+'_'+roi] - D['D_'+roi] - BMB['BMB_'+roi]).data)
        MB['MB_'+RCM+'_ROI_err'] = (('time',roi), (SMB[RCM+'_'+roi+'_err'].data**2 + D['err_'+roi].data**2 + BMB['BMB_'+roi+'_err'].data**2)**0.5)
        
    for v in ['MB', 'MB_ROI', 'MB_err', 'MB_ROI_err', 'MB_HIRHAM', 'MB_HIRHAM_ROI', 'MB_HIRHAM_err', 'MB_HIRHAM_ROI_err','MB_MAR', 'MB_MAR_ROI', 'MB_MAR_err', 'MB_MAR_ROI_err']:
        ln = 'Mass balance'
        if 'err' in v: ln = ln + ' uncertainty'
        MB[v].attrs['long_name'] = 'Mass balance'
        MB[v].attrs["standard_name"] = "land_ice_mass_transport"
        MB[v].attrs["units"] = "Gt d-1"
        MB[v].attrs["coordinates"] = 'time ' + roi
        
    # MB['MB_ROI'].attrs = MB['MB'].attrs
    # MB['MB_ROI'].attrs["coordinates"] = 'time ROI'

    # if roi == 'region':
    #     from IPython import embed; embed()
    
    MB['SMB'] = (('time'), SMB['SMB_mean'].data)
    MB['SMB_err'] = (('time'), SMB['SMB_mean_err'].data)
    MB['SMB_HIRHAM'] = (('time'), SMB['SMB_HIRHAM'].data)
    MB['SMB_HIRHAM_err'] = (('time'), SMB['SMB_HIRHAM_err'].data)
    MB['SMB_MAR'] = (('time'), SMB['SMB_MAR'].data)
    MB['SMB_MAR_err'] = (('time'), SMB['SMB_MAR_err'].data)
    MB['SMB_ROI'] = (('time',roi), SMB['SMB_mean_'+roi].data)
    MB['SMB_ROI_err'] = (('time',roi), SMB['SMB_mean_'+roi+'_err'].data)
    MB['SMB_HIRHAM_ROI'] = (('time',roi), SMB['SMB_HIRHAM_'+roi].data)
    MB['SMB_HIRHAM_ROI_err'] = (('time',roi), SMB['SMB_HIRHAM_'+roi+'_err'].data)
    MB['SMB_MAR_ROI'] = (('time',roi), SMB['SMB_MAR_'+roi].data)
    MB['SMB_MAR_ROI_err'] = (('time',roi), SMB['SMB_MAR_'+roi+'_err'].data)

    
    for v in ['SMB', 'SMB_ROI', 'SMB_err', 'SMB_ROI_err', 'SMB_HIRHAM', 'SMB_HIRHAM_ROI', 'SMB_HIRHAM_err', 'SMB_HIRHAM_ROI_err','SMB_MAR', 'SMB_MAR_ROI', 'SMB_MAR_err', 'SMB_MAR_ROI_err']:
        ln = 'Surface mass balance'
        if 'err' in v: ln = ln + ' uncertainty'
        MB[v].attrs['long_name'] = ln
        MB[v].attrs["standard_name"] = "land_ice_mass_transport"
        MB[v].attrs["units"] = "Gt d-1"
        MB[v].attrs["coordinates"] = 'time ' + roi

       
    MB['D'] = (('time'), D['D'].data)
    MB['D_err'] = (('time'), D['D_err'].data)
    MB['D_ROI'] = (('time',roi), D['D_'+roi].data)
    MB['D_ROI_err'] = (('time',roi), D['err_'+roi].data)
    for v in ['D','D_ROI', 'D_err', 'D_ROI_err']:
        ln = 'Marine mass balance'
        if 'err' in v: ln = ln + ' uncertainty'
        MB[v].attrs['long_name'] = ln
        MB[v].attrs["standard_name"] = "land_ice_mass_transport"
        MB[v].attrs["units"] = "Gt d-1"
    MB['D'].attrs["coordinates"] = 'time'
    MB['D_ROI'].attrs["coordinates"] = 'time ' + roi

    
    MB['BMB'] = (('time'), BMB['BMB'].data)
    MB['BMB_err'] = (('time'), BMB['BMB_err'].data)
    MB['BMB_ROI'] = (('time',roi), BMB['BMB_'+roi].data)
    MB['BMB_ROI_err'] = (('time',roi), BMB['BMB_'+roi+'_err'].data)
    for v in ['BMB','BMB_ROI', 'BMB_err', 'BMB_ROI_err']:
        ln = 'Basal mass balance'
        if 'err' in v: ln = ln + ' uncertainty'
        MB[v].attrs['long_name'] = ln
        MB[v].attrs["standard_name"] = "land_ice_mass_transport"
        MB[v].attrs["units"] = "Gt d-1"
    MB['BMB'].attrs["coordinates"] = 'time'
    MB['BMB_ROI'].attrs["coordinates"] = 'time ' + roi
    
        
    # MB['BMB'] = (('time'), BMB['BMB'])
    # MB['BMB_ROI'] = (('time',roi), BMB['BMB_'+roi])
    # MB['BMB_GF_ROI'] = (('time',roi), BMB['BMB_GF_'+roi])
    # MB['BMB_vel_ROI'] = (('time',roi), BMB['BMB_vel_'+roi])
    # MB['BMB_VHD_ROI'] = (('time',roi), BMB['BMB_VHD_'+roi])
    # for v in ['BMB','BMB_ROI']:
    #     MB[v].attrs['long_name'] = 'Basal mass balance'
    #     MB[v].attrs["standard_name"] = "land_ice_mass_transport"
    #     MB[v].attrs["units"] = "Gt d-1"
    # MB['BMB'].attrs["coordinates"] = 'time'
    # MB['BMB_ROI'].attrs["coordinates"] = 'time ' + roi

    
    # if roi == 'region':
    #     from IPython import embed; embed()
        # SMB['SMB_'+roi].sel({'region':'CE'}), '\n\n', D['D_'+roi].sel({'region':'CE'}), '\n\n', (SMB['SMB_'+roi] - D['D_'+roi]).sel({'region':'CE'}), '\n\n', MB.sel({'region':'CE'})
        # SMB['SMB_'+roi].isel({'time':0}), '\n\n', D['D_'+roi].isel({'time':0}), '\n\n', (SMB['SMB_'+roi] - D['D_'+roi]).isel({'time':0}), '\n\n', MB.isel({'time':0})

    
    MB.attrs['featureType'] = 'timeSeries'
    MB.attrs['title'] = 'Greenland ice sheet mass balance from 1840 through next week'
    MB.attrs['summary'] = MB.attrs['title']
    MB.attrs['keywords'] = 'Greenland; Mass; Mass balance'
    # MB.attrs['Conventions'] = 'CF-1.8'
    MB.attrs['source'] = 'git commit: ' + subprocess.check_output(['git', 'describe', '--always']).strip().decode('UTF-8')
    # MB.attrs['comment'] = 'TODO'
    # MB.attrs['acknowledgment'] = 'TODO'
    # MB.attrs['license'] = 'TODO'
    # MB.attrs['date_created'] = datetime.datetime.now().strftime('%Y-%m-%d')
    MB.attrs['creator_name'] = 'Ken Mankoff'
    MB.attrs['creator_email'] = 'kdm@geus.dk'
    MB.attrs['creator_url'] = 'http://kenmankoff.com'
    MB.attrs['institution'] = 'GEUS'
    # MB.attrs['time_coverage_start'] = 'TODO'
    # MB.attrs['time_coverage_end'] = 'TODO'
    # MB.attrs['time_coverage_resolution'] = 'TODO'
    MB.attrs['references'] = '10.22008/promice/mass_balance'
    MB.attrs['product_version'] = 1.0

    comp = dict(zlib=True, complevel=2, dtype='float32')

    encoding = {var: comp for var in MB.data_vars} # all variables
    encoding['time'] = {'dtype':'float64'} #time (to be compatible with openDAP)
    fn = './TMB/MB_'+roi+'.nc'
    if os.path.exists(fn): os.remove(fn)
    MB.to_netcdf(fn, mode='w', encoding=encoding)


# maybe also some CSV output
MB_df = MB[['MB','MB_err', 'MB_MAR', 'MB_HIRHAM','SMB','SMB_err', 'SMB_MAR', 'SMB_HIRHAM','D','D_err','BMB','BMB_err']].to_dataframe()
# Remove the forecast after september 1st if data after september 1st is only forecast 
# Determine the last date processed
# last_date = MB_df.index.max()

# Calculate September 1st of the last year processed
# sep_1_last_year = pd.to_datetime(f'{last_date.year}-09-01')

# Check if the difference is less than 7 days
# if (last_date - sep_1_last_year).days < 7:
    # Filter the DataFrame to remove dates beyond September 1st
#     MB_df = MB_df[MB_df.index < sep_1_last_year]
MB_df.to_csv('./TMB/MB_SMB_D_BMB.csv', float_format='%.6f')

# daily to annual
df = pd.read_csv('./TMB/MB_SMB_D_BMB.csv', index_col=0, parse_dates=True)
df = df.resample('1D')\
       .ffill()\
       .resample('YS')\
       .sum()\
       .iloc[:-1]
df.index = df.index.year
df.to_csv('./TMB/MB_SMB_D_BMB_ann.csv', float_format='%.6f')

# daily to hydrological year (Sep 1 – Aug 31, labelled by end year)
df = pd.read_csv('./TMB/MB_SMB_D_BMB.csv', index_col=0, parse_dates=True)
df = df.resample('1D')\
       .ffill()\
       .resample('YS-SEP')\
       .sum()\
       .iloc[:-1]
df.index = df.index.year + 1
df.to_csv('./TMB/MB_SMB_D_BMB_ann_hydro.csv', float_format='%.6f')

# cumulative MB from 1986-01-01 (daily)
df = pd.read_csv('./TMB/MB_SMB_D_BMB.csv', index_col=0, parse_dates=True)
df = df.resample('1D').ffill().loc['1986':]
cum = pd.DataFrame(index=df.index)
cum['MB_cumulative']     = df['MB'].cumsum()
cum['MB_cumulative_err'] = np.sqrt((df['MB_err']**2).cumsum())
cum.to_csv('./TMB/MB_cumulative.csv', float_format='%.6f')

# cumulative MB — end-of-year snapshot (annual)
cum_ann = cum.resample('YE').last().iloc[:-1]
cum_ann.index = cum_ann.index.year
GT_TO_SLE = 0.0028  # mm SLE per Gt
cum_ann['SLE_cumulative']     = cum_ann['MB_cumulative']     * GT_TO_SLE
cum_ann['SLE_cumulative_err'] = cum_ann['MB_cumulative_err'] * GT_TO_SLE
cum_ann.to_csv('./TMB/MB_cumulative_ann.csv', float_format='%.6f')
