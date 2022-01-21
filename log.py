import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import time

from strategy import GoldenCross
from graph import Plot

class Logger(object):
    def __init__(self, plot) -> None:
        self.first_step = True
        self.df = None
        self.initialize_log_name()
        self.long = []
        self.short = []

        self.profit = [None]
        self.rpnl = 0
        self.upnl = 0
        self.plot = plot

        # plot用のインスタンス
        if self.plot:
            self.i_plot = Plot(realtime=True)

    def save_position_side(self, signal, df):
        # log保存用
        if signal == 1:
            self.df.loc[self.df.index[-1],"Long"] = 1.0
        elif signal == -1:
            self.df.loc[self.df.index[-1],"Short"] = 1.0

    def save_upnl(self,df,upnl):
        # 未確定のpnl
        #　一番後ろにこれまでの利益＋今回のupnlが入る
        self.upnl = upnl
        self.df.loc[self.df.index[-1],"Profit"] = self.rpnl+self.upnl

    def save_rpnl(self,df,rpnl):
        # 確定のpnl
        self.rpnl += rpnl

    def save_pnl(self, df):
        # 足ごとのpnlを出す
        self.df.loc[self.df.index[-1],"Profit"] = self.rpnl+self.upnl
    
    def plot_df(self,df,signal):
        # self.dfに保存→dfを作る→作ったdfにlong short profitを入れる
        if self.plot:
            df = self.df[self.df.index[-100]:].copy()
            JST = timezone(timedelta(hours=+9), "JST")
            df['datetime'] = df["Open Time"].apply(lambda d: datetime.fromtimestamp(int(d/1000), JST))
            df=df.set_index("datetime")
            i_plot.plot_df(df)

    def initialize_log_name(self):
        # savedfで使用するログのパスを作る
            dt_now = datetime.now()
            log_dir = "df_log"
            file_name = dt_now.strftime('%Y-%m-%d_%H-%M-%S')
            self.df_log_path = log_dir + "\\" +file_name + '.csv'
    
    def save_to_csv(self):
        # logで溜め込んだohlcvデータをcsvにする
        self.df.to_csv(self.df_log_path, chunksize=10000)
        return self.df_log_path

    def save_df(self, df):
        df = GoldenCross.add_ema(df,GoldenCross.s_ema)
        df = GoldenCross.add_ema(df,GoldenCross.l_ema)
        if self.first_step:
            df["Long"] = pd.Series()
            df["Short"] = pd.Series()
            df["Profit"] = 0
            self.df = df
            self.first_step = False
        else:
            self.df.loc[self.df.index[-1], "Close"] = df.loc[df.index[-1], "Close"]
            self.df = self.df.append(df, ignore_index=False).drop_duplicates(subset="Close Time").reset_index(drop=True)

# 以下はバックテストのログを見る際に使用
def read_csv(file_path):
    df = pd.read_csv(file_path)
    return df

def plot_df(df):
    plot = Plot(realtime=False)
    JST = timezone(timedelta(hours=+9), "JST")
    df['datetime'] = df["Open Time"].apply(lambda d: datetime.fromtimestamp(int(d/1000), JST))
    df=df.set_index("datetime")
    plot.plot_df(df=df)

def main():
    file_path = "df_log/2022-01-21_17-50-04.csv"
    df = read_csv(file_path)
    plot_df(df)

if __name__ == "__main__":
    main()