import tweepy
import pandas as pd
import numpy as np
import datetime

df = pd.read_csv('./TMB/mb_smb_mmb_bmb.csv', index_col=0, parse_dates=True, usecols=(0,1,2))

now = datetime.datetime.now()
this_year = now.year
today = now.isoformat()[0:10]
year_ago = str(this_year-1) + today[4:]
tomorrow = str(df.index[-7])[0:10]
next_week = str(df.index[-1])[0:10]


def SLR_daterange(t0, t1):
    d = df[(df.index >= t0) & (df.index <= t1)].sum()
    d['mm'] = -1*d['mb'] / 361.8 # Gt to mm
    d['mm_err'] = -1*d['mb_err'] / 361.8 # Gt to mm
    d[['mm_err','mb_err']] = np.abs(d[['mm_err','mb_err']])
    return d

far = SLR_daterange('1990-01-01', today)
ytd = SLR_daterange(str(this_year)+'-01-01', today)
next7 = SLR_daterange(tomorrow, next_week)

def my_fmt(n):
    return str(round(n,2))

tweet_str = ""
tweet_str += f"Sea level rise (#SLR: 📈=🌊+🧊💧) from 🇬🇱#Greenland"
tweet_str += f"\n  Since 1990 (IPCC FAR): {my_fmt(far['mm'])} ±{my_fmt(far['mm_err'])} mm"
tweet_str += f" ({my_fmt(far['mb'])} ±{my_fmt(far['mb_err'])} Gt)"

tweet_str += f"\n  {this_year} (through {today}): "
if float(ytd['mm']) > 0.01:
    tweet_str += f"{my_fmt(ytd['mm'])} ±{my_fmt(ytd['mm_err'])} mm ("
tweet_str += f"{my_fmt(ytd['mb'])} ±{my_fmt(ytd['mb_err'])} Gt"
if float(ytd['mm']) > 0.01: tweet_str += f")"

tweet_str += f"\n  Next 7 days ({tomorrow} through {next_week}): "
if float(next7['mm']) > 0:
    tweet_str += f"{my_fmt(next7['mm'])} ±{my_fmt(next7['mm_err'])} mm ("
tweet_str += f"{my_fmt(next7['mb'])} ±{my_fmt(next7['mb_err'])} Gt"
if float(next7['mm']) > 0: tweet_str += f")"
    
tweet_str += '\n\n'
tweet_str += 'Source: https://doi.org/10.22008/FK2/OHI23Z'

print(tweet_str)

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


