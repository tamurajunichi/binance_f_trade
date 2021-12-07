import os
import pandas as pd
from binance.client import Client

api_key = os.environ.get('BINANCE_API_KEY')
api_secret = os.environ.get('BINANCE_API_SECRET')
client = Client(api_key, api_secret)

'''
30分足の例
 [[
    1499040000000,      # Open time
    "0.01634790",       # Open
    "0.80000000",       # High
    "0.01575800",       # Low
    "0.01577100",       # Close
    "148976.11427815",  # Volume
    1499644799999,      # Close time
    "2434.19055334",    # Quote asset volume
    308,                # Number of trades
    "1756.87402397",    # Taker buy base asset volume
    "28.46694368",      # Taker buy quote asset volume
    "17928899.62484339" # Can be ignored
]]
'''
column_name = [
    "Open time",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Close time",
    "Quote asset volume",
    "Number of trades",
    "Taker base volume",
    "Taker quote volume",
    "ignored"
]
klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1MINUTE,  "1 Dec, 2017", "1 Jan, 2018")
#date = [datetime.datetime.fromtimestamp(float(k)/1000.0) for k in klines[:][0]]
df =  pd.DataFrame(klines,columns=column_name)
df = df.set_index('Open time')
df.to_csv('2017dec1-2018jan1.csv')
print("to csv")