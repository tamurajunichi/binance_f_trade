import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import mplfinance as mpf
import pandas as pd
import datetime
import graph

class Logger(object):
    def __init__(self) -> None:
        self.first_step = True
        self.df = None
        self.initialize_log_name()
        self.long = []
        self.short = []
        self.profit = []

    def save_position_side(self, signal, df):
        # log保存用
        if signal == 1:
            self.long.append(df.loc[df.index[-1],["Close Time"]])
        elif signal == -1:
            self.short.append(df.loc[df.index[-1],["Close Time"]])

    def save_profit(self, df, profit):
        self.profit.append([df.loc[df.index[-1], ["Close Time"]], profit])

    def tograph(self,df):
        ema_df = df[["ema3","ema7"]]
        ema = mpf.make_addplot(ema_df[len(df.index)-50:len(df.index)])

        df['datetime'] = pd.to_datetime(df['Open Time'].astype(int)/1000, unit="s")
        df = df.drop(columns="Open Time", axis=1)
        df = df.set_index('datetime')
        df = df[["Open","High", "Low", "Close", "Volume"]]
        mpf.plot(df[len(df.index)-50:len(df.index)], addplot=ema,type='candle', figratio=(12,4), savefig="bot_test.png",volume=True)
    
    def tograph_mpl(self,df):
        # matplotでグラフ表示
        fig = plt.figure(figsize=(10,8))
        gs_master = GridSpec(nrows=4, ncols=2, height_ratios=[1,1,1,1])
        gs_1 = GridSpecFromSubplotSpec(nrows=3, ncols=1, subplot_spec=gs_master[0:3, :])
        ax_1 = fig.add_subplot(gs_1[:,:])
        gs_2 = GridSpecFromSubplotSpec(nrows=1, ncols=1, subplot_spec=gs_master[3, :])
        ax_2 = fig.add_subplot(gs_2[:,:])

        # timestampからdatetimeを作りindexにする。datetimeは日本時間を指定。
        df['datetime'] = pd.to_datetime(df['Open Time'].astype(int)/1000, unit="s")
        df=df.set_index("datetime")
        df=df.tz_localize('utc').tz_convert('Asia/Tokyo')
        #　現在の足から50前まで表示
        graph.ohlcv_plot(ax_1,df[len(df.index)-50:len(df.index)])

        # longとshortのマーカーをつける
        df["Long"] = pd.Series()
        df["Short"] = pd.Series()
        if len(self.long) > 0:
            for i in self.long:
                l = df.index[df['Close Time'] == i[0]].tolist()
                df.loc[df.index[df.index.get_loc(l[0])], ["Long"]] = 1.0
        ax_1.scatter(df.index, df["Long"].mask(df['Long'] == 1.0, df['Low']-20),marker="^",color="r",label="long")
        if len(self.short) > 0:
            for i in self.short:
                l = df.index[df['Close Time'] == i[0]].tolist()
                df.loc[df.index[df.index.get_loc(l[0])], ["Short"]] = 1.0
        ax_1.scatter(df.index, df["Short"].mask(df['Short'] == 1.0, df['High']+20),marker="v",color="b",label="short")
        ax_1.legend()

        df["Profit"] = 0
        if len(self.profit) > 0:
            for i,p in zip(self.profit):
                l = df.index[df['Close Time'] == i[0]].tolist()
                df.loc[df.index[df.index.get_loc(l[0])], ["Profit"]] = p
            ax_2.plot(df.index, df["Profit"], color = "y")
        plt.savefig('candle_mpl.png')
        self.save_df(df)

    def  initialize_log_name(self):
        # savedfで使用するログのパスを作る
            dt_now = datetime.datetime.now()
            log_dir = 'df_log/'
            file_name = dt_now.strftime('%Y-%m-%d_%H:%M:%S')
            self.df_log_path = log_dir + file_name + '.csv'
    
    def save_to_csv(self, df):
        # logで溜め込んだohlcvデータをcsvにする
        df.to_csv(self.df_log_path)

    def save_df(self, df):
        if self.first_step:
            self.df = df
            self.first_step = False
        else:
            self.df = self.df.append(df, ignore_index=False).drop_duplicates(subset="Close Time").reset_index(drop=True)