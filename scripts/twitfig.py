# Twitter figure TMB
# :PROPERTIES:
# :header-args:python+: :tangle twitfig.py
# :END:


# [[file:code.org::*Twitter figure TMB][Twitter figure TMB:1]]
import matplotlib
matplotlib.use('Agg') # Must be before importing matplotlib.pyplot or pylab!
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as ticker
from adjust_spines import adjust_spines as adj
from matplotlib import rc
rc('font', size=8)
rc('text', usetex=False)


df = pd.read_csv('./TMB/MB_SMB_D_BMB.csv', index_col=0, parse_dates=True)
df = df.resample('1D').ffill()

df = df[df.index.dayofyear <= 365] # drop leap years for simplicity
df = df['1986-09-01':] # hydro years

# hydro year dates but dropping leap years
t = pd.date_range(start='1987-01-01', freq='D', periods=df.index.size+100) # hydro year index
t = t[t.dayofyear <= 365][0:df.index.size]
df['t_hydro'] = t

df['hydro_year'] = df.set_index('t_hydro').index.year
df['hydro_doy'] = df.set_index('t_hydro').index.dayofyear

nyear = int(np.ceil(df.index.size/365))
df['t_repeat'] = (pd.date_range(start='2000-01-01', freq='D', periods=365).to_list() * nyear) [0:df.index.size]

plt.close(1)
fig = plt.figure(1, figsize=(3.5,2.0)) # w,h
fig.clf()
fig.set_tight_layout(True)

ax = fig.add_subplot(111)

kw_plot = {'drawstyle':'steps', 'rot':90, 'color':'k', 'linewidth':0.1}
this_year = datetime.datetime.now().year
last_day = df.index[-1].strftime("%b %-d")

for hyr in df['hydro_year'].unique():
    this = df[df['hydro_year'] == hyr]
    this = this.set_index('t_repeat')

    this['MB'].cumsum().plot(ax=ax, label='_no', **kw_plot)
    if hyr in [1992,1996,2010,2011, 2012, 2019, 2020, 2021]:
        ax.text(this.index[-1], this['MB'].cumsum().values[-1], str(hyr),
                fontsize=5,
                verticalalignment='center')

        

mean = df[(df['hydro_year'] >= 1991) & (df['hydro_year'] <= 2020)]
mean = mean.groupby(mean['hydro_doy']).mean()
mean.index = df['t_repeat'][0:365]
mean['MB'].cumsum().plot(ax=ax, drawstyle='steps', color='k', linewidth=2, label='1991 through 2020 mean')

kw_plot['color'] = 'r'
kw_plot['linewidth'] = 2
# this['MB'].cumsum().plot(ax=ax, label='2022 (through '+last_day+')', **kw_plot)
if this.index.size > 8:
    this['MB'].cumsum().iloc[:-10].plot(ax=ax, label='Through '+last_day, **kw_plot)
    kw_plot['alpha'] = 0.8
    this['MB'].cumsum().iloc[-7:].plot(ax=ax, label='_no', **kw_plot)
else:
    this['MB'].cumsum().plot(ax=ax, label='Through '+last_day, **kw_plot)


std = df[(df['hydro_year'] >= 1991) & (df['hydro_year'] <= 2020)]
for hy in std['hydro_year'].unique():
    idx = (std['hydro_year'] == hy)
    std = std.where(~idx, other=std[idx].cumsum())
std = std.groupby(std['hydro_doy']).std()
std.index = df['t_repeat'][0:365]
ax.fill_between(std.index,
                mean['MB'].cumsum()+std['MB'],
                mean['MB'].cumsum()-std['MB'],
                color='b', linewidth=2, label='_no', alpha=0.1)

adj(ax, ['bottom','left'])
ax.set_ylim([-500,300])
ax.set_yticks([-500,-400,-300,-200,-100,0,100,200,300])
ax.set_ylabel('Hydrologic year cumulative\nmass change [Gt]')

## https://stackoverflow.com/questions/17158382/
ax.xaxis.set_major_formatter(ticker.NullFormatter())
ax.xaxis.set_minor_locator(ticker.FixedLocator(ax.get_xticks()+16))
months = ['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug']
ax.xaxis.set_minor_formatter(ticker.FixedFormatter(months))
ax.set_xlabel('')

plt.setp(ax.xaxis.get_minorticklabels(), rotation=90)
ax.tick_params(which='minor', length=0)
plt.xticks(rotation=90)
plt.legend(fontsize=7)

plt.savefig('./twitfig.png', dpi=150, bbox_inches='tight')
# Twitter figure TMB:1 ends here
