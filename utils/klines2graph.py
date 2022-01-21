import matplotlib.pyplot as plot
import mplfinance as mpf
import pandas as pd
import datetime

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

def kline2graph(file_dir, file_name,type='line',max_plot=None):
    df = pd.read_csv(file_dir+file_name+".csv",names=column_name)
    df['datetime'] = pd.to_datetime(df['Open time'].astype(int)/1000, unit="s")
    df = df.drop(columns="Open time", axis=1)
    df = df.set_index('datetime')
    df = df[["Open","High", "Low", "Close", "Volume"]]
    if max_plot is not None:
        mpf.plot(df[0:max_plot],type=type, figratio=(12,4), savefig="figures/"+file_name+".png",volume=True)
    else:
        mpf.plot(df[0:],type=type, figratio=(12,4), savefig="figures/"+file_name+".png",volume=True)



if __name__ == "__main__":
    symbol = "BTCUSDT"
    candle = "1m"
    y= "2021"
    m="11".zfill(2)
    file_dir = "future_klines/%s/%s/"%(symbol,candle)
    file_name = "%s-%s-%s-%s"%(symbol,candle,y,m)
    kline2graph(file_dir,file_name)