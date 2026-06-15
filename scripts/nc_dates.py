# Print dates


# [[file:code.org::*Print dates][Print dates:1]]
import xarray as xr
import sys

f = sys.argv[1]

ds = xr.open_dataset(f)

if 'time' in ds.variables:
    tvar = 'time'
if 'TIME' in ds.variables:
    tvar = 'TIME'
    
t = [(str(_)[0:10]) for _ in ds[tvar].values]
for _ in t: print(_)
# Print dates:1 ends here
