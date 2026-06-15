# Twitter figure Sermeq Kujalleq
# :PROPERTIES:
# :header-args:python+: :tangle twitbot.py
# :END:


# [[file:code.org::*Twitter figure Sermeq Kujalleq][Twitter figure Sermeq Kujalleq:1]]
import matplotlib

matplotlib.use('Agg') # Must be before importing matplotlib.pyplot or pylab!
import xarray as xr
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


with xr.open_dataset('/home/shl/data/promice/TMB/MB_sector.nc') as ds:
    #print(ds.sel({'sector':71})[['MB','SMB','D','BMB']].to_dataframe().drop(columns='sector').tail(8))
    df = ds.sel({'sector':71})[['MB_ROI','SMB_ROI','D_ROI','BMB_ROI']].to_dataframe().drop(columns='sector').copy()

df = df.resample('1D').ffill()
df = df[df.index.dayofyear <= 365] # drop leap years for simplicity
df = df['1986-09-01':] # hydro years

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

    this['MB_ROI'].cumsum().plot(ax=ax, label='_no', **kw_plot)
    if hyr in [1992,1996,2000,2003,2012,2015,2018,2021]:
        ax.text(this.index[-1], this['MB_ROI'].cumsum().values[-1], str(hyr),
                fontsize=5,
                verticalalignment='center')

        

mean = df[(df['hydro_year'] >= 1991) & (df['hydro_year'] <= 2021)]
mean = mean.groupby(mean['hydro_doy']).mean()
mean.index = df['t_repeat'][0:365]
mean['MB_ROI'].cumsum().plot(ax=ax, drawstyle='steps', color='k', linewidth=2, label='1991 through 2021 mean')

kw_plot['color'] = 'r'
kw_plot['linewidth'] = 2
# this['MB'].cumsum().plot(ax=ax, label='2022 (through '+last_day+')', **kw_plot)
if this.index.size > 8:
    this['MB_ROI'].cumsum().iloc[:-10].plot(ax=ax, label='Through '+last_day, **kw_plot)
    kw_plot['alpha'] = 0.8
    this['MB_ROI'].cumsum().iloc[-7:].plot(ax=ax, label='_no', **kw_plot)
else:
    this['MB_ROI'].cumsum().plot(ax=ax, label='Through '+last_day, **kw_plot)


std = df[(df['hydro_year'] >= 1991) & (df['hydro_year'] <= 2021)]
for hy in std['hydro_year'].unique():
    idx = (std['hydro_year'] == hy)
    std = std.where(~idx, other=std[idx].cumsum())
std = std.groupby(std['hydro_doy']).std()
std.index = df['t_repeat'][0:365]
ax.fill_between(std.index,
                mean['MB_ROI'].cumsum()+std['MB_ROI'],
                mean['MB_ROI'].cumsum()-std['MB_ROI'],
                color='b', linewidth=2, label='_no', alpha=0.1)

adj(ax, ['bottom','left'])
ax.set_ylim([-40,20])
ax.set_yticks([-40,-30,-20,-10,0,10,20])
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

plt.savefig('./Sermeq_Kujalleq_twitfig.png', dpi=150, bbox_inches='tight')
# Twitter figure Sermeq Kujalleq:1 ends here

# Twitter figure Sermeq Kujalleq 2000-present
# :PROPERTIES:
# :header-args:python+: :tangle twitbot.py
# :END:


# [[file:code.org::*Twitter figure Sermeq Kujalleq 2000-present][Twitter figure Sermeq Kujalleq 2000-present:1]]
import matplotlib

matplotlib.use('Agg') # Must be before importing matplotlib.pyplot or pylab!
import xarray as xr
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


with xr.open_dataset('/home/shl/data/promice/TMB/MB_sector.nc') as ds:
    #print(ds.sel({'sector':71})[['MB','SMB','D','BMB']].to_dataframe().drop(columns='sector').tail(8))
    df = ds.sel({'sector':71})[['MB_ROI','SMB_ROI','D_ROI','BMB_ROI']].to_dataframe().drop(columns='sector').copy()

df = df.resample('1D').ffill()
df = df[df.index.dayofyear <= 365] # drop leap years for simplicity
df = df['1986-09-01':] # hydro years

df = df[df.index.dayofyear <= 365] # drop leap years for simplicity
df = df['1986-09-01':] # hydro years

# hydro year dates but dropping leap years
t = pd.date_range(start='1987-01-01', freq='D', periods=df.index.size+100) # hydro year index
t = t[t.dayofyear <= 365][0:df.index.size]
df['t_hydro'] = t
df = df['1999-09-01':]

df['hydro_year'] = df.set_index('t_hydro').index.year
df['hydro_doy'] = df.set_index('t_hydro').index.dayofyear

nyear = int(np.ceil(df.index.size/365))
df['t_repeat'] = (pd.date_range(start='2000-01-01', freq='D', periods=365).to_list() * nyear) [0:df.index.size]



plt.close(1)
fig = plt.figure(1, figsize=(3.5,2.0) ) # w,h 
fig.clf()
fig.set_tight_layout(True)

ax = fig.add_subplot(111)

kw_plot = {'drawstyle':'steps', 'rot':90, 'color':'k', 'linewidth':0.1}
this_year = datetime.datetime.now().year
last_day = df.index[-1].strftime("%b %-d")

for hyr in df['hydro_year'].unique():
    this = df[df['hydro_year'] == hyr]
    this = this.set_index('t_repeat')

    this['MB_ROI'].cumsum().plot(ax=ax, label='_no', **kw_plot)
    if hyr in [2000,2003,2012,2015,2018,2021] : #[2010,2011, 2012, 2021]:
        ax.text(this.index[-1], this['MB_ROI'].cumsum().values[-1], str(hyr),
                fontsize=5,
                verticalalignment='center')

        

mean = df[(df['hydro_year'] >= 2000) & (df['hydro_year'] <= 2021)]
mean = mean.groupby(mean['hydro_doy']).mean()
mean.index = df['t_repeat'][0:365]
mean['MB_ROI'].cumsum().plot(ax=ax, drawstyle='steps', color='k', linewidth=2, label='2000 through 2021 mean')

kw_plot['color'] = 'r'
kw_plot['linewidth'] = 2
# this['MB'].cumsum().plot(ax=ax, label='2022 (through '+last_day+')', **kw_plot)
if this.index.size > 8:
    this['MB_ROI'].cumsum().iloc[:-10].plot(ax=ax, label='Through '+last_day, **kw_plot)
    kw_plot['alpha'] = 0.8
    this['MB_ROI'].cumsum().iloc[-7:].plot(ax=ax, label='_no', **kw_plot)
else:
    this['MB_ROI'].cumsum().plot(ax=ax, label='Through '+last_day, **kw_plot)


std = df[(df['hydro_year'] >= 2000) & (df['hydro_year'] <= 2021)]
for hy in std['hydro_year'].unique():
    idx = (std['hydro_year'] == hy)
    std = std.where(~idx, other=std[idx].cumsum())
std = std.groupby(std['hydro_doy']).std()
std.index = df['t_repeat'][0:365]
ax.fill_between(std.index,
                mean['MB_ROI'].cumsum()+std['MB_ROI'],
                mean['MB_ROI'].cumsum()-std['MB_ROI'],
                color='b', linewidth=2, label='_no', alpha=0.1)

adj(ax, ['bottom','left'])
ax.set_ylim([-40,20])
ax.set_yticks([-40,-30,-20,-10,0,10,20])
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

plt.savefig('./Sermeq_Kujalleq_2000_present_twitfig.png', dpi=150, bbox_inches='tight')
# Twitter figure Sermeq Kujalleq 2000-present:1 ends here

# Twitter bot
# :PROPERTIES:
# :header-args:python+: :tangle twitbot.py
# :END:
 
# + Graph up :: 📈 (mass loss, SLR up)
# + Graph down :: 📉 (mass gain, SLR down)
# + Ocean wave :: 🌊
# + Ice cube :: 🧊
# + Water drop :: 💧
# + Greenland flag :: 🇬🇱


# [[file:code.org::*Twitter bot][Twitter bot:1]]
import tweepy
import pandas as pd
import numpy as np
import datetime

df = pd.read_csv('./TMB/MB_SMB_D_BMB.csv', index_col=0, parse_dates=True, usecols=(0,1,2))

now = datetime.datetime.now()
this_year = now.year
today = now.isoformat()[0:10]
tomorrow = str(df.index[-7])[0:10]
next_week = str(df.index[-1])[0:10]

assert(now.isoformat()[0:10] == str(df.index[-8])[0:10])

def SLR_daterange(t0, t1):
    d = df[(df.index >= t0) & (df.index <= t1)].sum()
    d['mm'] = -1*d['MB'] / 361.8 # Gt to mm
    d['mm_err'] = -1*d['MB_err'] / 361.8 # Gt to mm
    d[['mm_err','MB_err']] = np.abs(d[['mm_err','MB_err']])
    return d

far = SLR_daterange('1990-01-01', today)
ytd = SLR_daterange(str(this_year)+'-01-01', today)
next7 = SLR_daterange(tomorrow, next_week)

def my_fmt(n, dec=2):
    if dec == 0:
        return str(int(round(n)))
    return str(round(n,dec))

tweet_str = ""
tweet_str += f"Sea level rise (#SLR: 📈=🌊+🧊💧) from 🇬🇱Greenland"
tweet_str += f"\n\nSince 1990 (IPCC FAR): ~{my_fmt(far['mm'])} mm"
tweet_str += f" ({my_fmt(far['MB'], dec=0)} Gt)"

tweet_str += f"\n\n{this_year} → today: "
if ytd['mm'] > 0.01:
    tweet_str += f"~{my_fmt(ytd['mm'])} mm ("
tweet_str += f"{my_fmt(ytd['MB'], dec=0)} Gt"
if ytd['mm'] > 0.01: tweet_str += f")"

tweet_str += f"\n\nNext 7 days ({tomorrow} →️{next_week})"
if next7['mm'] < 0: # mass gain
    tweet_str += f"📉: mass gain +{my_fmt(next7['MB'], dec=1)} ±{my_fmt(next7['MB_err'], dec=1)} Gt"
if next7['mm'] > 0: # mass loss
    tweet_str += f"📈: {my_fmt(next7['mm'])} ±{my_fmt(next7['mm_err'])} mm ({my_fmt(next7['MB'], dec=1)} ±{my_fmt(next7['MB_err'], dec=1)} Gt)"

tweet_str += '\n'
tweet_str += '\nhttps://doi.org/10.5194/essd-13-5001-2021'
tweet_str += '\nhttps://doi.org/10.22008/FK2/OHI23Z'
tweet_str += '\nhttps://github.com/GEUS-Glaciology-and-Climate/mass_balance'

# print(len(tweet_str))
print(tweet_str)
# Twitter bot:1 ends here



# #+RESULTS:
# #+begin_example
# Sea level rise (#SLR: 📈=🌊+🧊💧) from 🇬🇱Greenland

# Since 1990 (IPCC FAR): ~14.43 mm (-5220 Gt)

# 2021 → today: ~0.65 mm (-233 Gt)

# Next 7 days (2021-11-03 →️2021-11-09)📈: 0.0 ±0.0 mm (-0.4 ±1.5 Gt)

# https://github.com/GEUS-Glaciology-and-Climate/mass_balance
# https://doi.org/10.5194/essd-13-5001-2021
# https://doi.org/10.22008/FK2/OHI23Z
# #+end_example


# [[file:code.org::*Twitter bot][Twitter bot:2]]
import secret

# # Authenticate to Twitter
auth = tweepy.OAuthHandler(secret.API_KEY, secret.API_SECRET)
# auth.get_authorization_url() # go to URL, get code
# auth.get_access_token("<code>")
# returns:
# ACCESS_TOKEN = 'string'
# ACCESS_TOKEN_SECRET = 'string'


auth.set_access_token(secret.ACCESS_TOKEN, secret.ACCESS_TOKEN_SECRET)

# Create API object
api = tweepy.API(auth)

# https://stackoverflow.com/questions/43490332/sending-multiple-medias-with-tweepy
# Upload an image and get ID
media = api.media_upload('twitfig.png')


# Create a tweet
api.update_status(tweet_str, media_ids=[media.media_id])
# Twitter bot:2 ends here
