import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import matplotlib.animation as animation
from matplotlib import dates as mdates
import mplfinance as mpf
import pandas as pd
import numpy as np
import datetime
from strategy import GoldenCross

class Logger(object):
    def __init__(self) -> None:
        self.first_step = True
        self.df = None
        self.initialize_log_name()
        self.long = []
        self.short = []

        self.profit = []
        self.pnl = 0

        # matplotでグラフ表示
        self.fig = plt.figure(figsize=(8,6))
        self.gs_master = GridSpec(nrows=4, ncols=2, height_ratios=[1,1,1,1])
        self.gs_1 = GridSpecFromSubplotSpec(nrows=3, ncols=1, subplot_spec=self.gs_master[0:3, :])
        self.ax_1 = self.fig.add_subplot(self.gs_1[:,:])
        self.gs_2 = GridSpecFromSubplotSpec(nrows=1, ncols=1, subplot_spec=self.gs_master[3, :])
        self.ax_2 = self.fig.add_subplot(self.gs_2[:,:])
        self.ax_1v=self.ax_1.twinx()

    def save_position_side(self, signal, df):
        # log保存用
        if signal == 1:
            self.long.append(df.loc[df.index[-1], ["Close Time"]])
        elif signal == -1:
            self.short.append(df.loc[df.index[-1], ["Close Time"]])

    def save_upnl(self, df, profit):
        self.profit.append([df.loc[df.index[-1], ["Close Time"]], profit])

    def save_pnl(self, pnl):
        print("save pnl %f"%(self.pnl))
        self.pnl += pnl

    def tograph_mpf(self,df):
        # 使用しない
        ema_df = df[["ema3","ema7"]]
        ema = mpf.make_addplot(ema_df[len(df.index)-50:len(df.index)])

        df['datetime'] = pd.to_datetime(df['Open Time'].astype(int)/1000, unit="s")
        df = df.drop(columns="Open Time", axis=1)
        df = df.set_index('datetime')
        df = df[["Open","High", "Low", "Close", "Volume"]]
        mpf.plot(df[len(df.index)-50:len(df.index)], addplot=ema,type='candle', figratio=(12,4), savefig="bot_test.png",volume=True)
    
    def tograph_mpl(self,df,signal):
        # emaを算出してdfに付け足す
        if signal == 0:
            df = GoldenCross.add_ema(df,3)
            df = GoldenCross.add_ema(df,7)

        # timestampからdatetimeを作りindexにする。datetimeは日本時間を指定。
        df['datetime'] = pd.to_datetime(df['Open Time'].astype(int)/1000, unit="s")
        df=df.set_index("datetime")
        df=df.tz_localize('utc').tz_convert('Asia/Tokyo')
        #　現在の足から50前まで表示
        self.ohlcv_plot(df[len(df.index)-50:len(df.index)])

        # longとshortのマーカーをつける
        df["Long"] = pd.Series()
        df["Short"] = pd.Series()
        if len(self.long) > 0:
            for i in self.long:
                l = df.index[df['Close Time'] == i[0]].tolist()
                df.loc[df.index[df.index.get_loc(l[0])], ["Long"]] = 1.0
        self.ax_1.scatter(df.index, df["Long"].mask(df['Long'] == 1.0, df['Low']-20),marker="^",color="r",label="long")
        if len(self.short) > 0:
            for i in self.short:
                l = df.index[df['Close Time'] == i[0]].tolist()
                df.loc[df.index[df.index.get_loc(l[0])], ["Short"]] = 1.0
        self.ax_1.scatter(df.index, df["Short"].mask(df['Short'] == 1.0, df['High']+20),marker="v",color="b",label="short")
        self.ax_1.legend()

        df["Profit"] = self.pnl
        for i in self.profit:
            l = df.index[df['Close Time'] == i[0][0]].tolist()
            # もらったdfが1分遅れてる場合があるので、そういう場合はスキップする
            try:
                df.loc[df.index[df.index.get_loc(l[0])], ["Profit"]] = self.pnl+i[1]
            except IndexError:
                pass
        self.ax_2.plot(df.index, df["Profit"], color = "y")
        plt.pause(0.001)
        self.ax_1.cla()
        self.ax_1v.cla()
        self.ax_2.cla()
        self.save_df(df)

    def animation(self, df, signal):
        # matplotでグラフ表示
        fig = plt.figure()
        gs_master = GridSpec(nrows=4, ncols=2, height_ratios=[1,1,1,1])
        gs_1 = GridSpecFromSubplotSpec(nrows=3, ncols=1, subplot_spec=gs_master[0:3, :])
        ax_1 = fig.add_subplot(gs_1[:,:])
        gs_2 = GridSpecFromSubplotSpec(nrows=1, ncols=1, subplot_spec=gs_master[3, :])
        ax_2 = fig.add_subplot(gs_2[:,:])

        ani = animation.FuncAnimation(fig, Logger.tograph_mpl, fargs=(df, signal, ax_1, ax_2),interval = 1000)
        plt.show()
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
        return self.df_log_path

    def save_df(self, df):
        if self.first_step:
            self.df = df
            self.first_step = False
        else:
            self.df = self.df.append(df, ignore_index=False).drop_duplicates(subset="Close Time").reset_index(drop=True)

    def ohlcv_plot(self,df):
        """
        matplotlibのAxesオブジェクトにローソク足を描画する.
        :param ax_1:ローソク足を描画するAxesオブジェクト.
        :param df:DataFrameオブジェクト. 必要なカラムはtimestamp,open,high,low,close,volume.
        """

        # warning出さないようにcopyする
        df = df.copy()

        # ローソク足の幅を設定
        # matplotlib上でwidth=1->1日となるのでローソク足の時間軸に応じて幅を設定
        time_span=df["Open Time"].diff()[1]
        time_span=time_span/1000
        w=time_span/(24*60*60)

        # ローソク足
        # 陽線と陰線で色を変えるため、それぞれのindexを取得
        idx1=df.index[df["Close"]>=df["Open"]]
        idx0=df.index[df["Close"]<df["Open"]]

        # 実体
        df["body"]=df["Close"]-df["Open"]
        df["body"]=df["body"].abs()
        self.ax_1.bar(idx1,df.loc[idx1,"body"],width=w * (1-0.2),bottom=df.loc[idx1,"Open"],linewidth=1,color="#33b066",zorder=2)
        self.ax_1.bar(idx0,df.loc[idx0,"body"],width=w * (1-0.2),bottom=df.loc[idx0,"Close"],linewidth=1,color="#ff5050",zorder=2)

        # ヒゲ
        # zorderを指定して実体の後ろになるようにする。
        self.ax_1.vlines(df.index,df["Low"],df["High"],linewidth=1,color="#666666",zorder=1)

        # EMA
        ema3 = df["ema3"]
        ema7 = df["ema7"]
        self.ax_1.plot(df.index,ema3,color="#2EF9FF",linewidth=.5)
        self.ax_1.plot(df.index,ema7,color="#FF2ED6",linewidth=.5)

        # 価格目盛調整
        # グラフ下部に出来高の棒グラフを描画するので、そのためのスペースを空けるよう目盛を調整する
        ymin,ymax=df["Low"].min(),df["High"].max()
        ticks=self.ax_1.get_yticks()
        margin=(len(ticks)+4)/5
        tick_span=ticks[1]-ticks[0]
        min_tick=ticks[0]-tick_span*margin
        self.ax_1.set_ylim(min_tick, ticks[-1])
        self.ax_1.set_yticks(ticks[1:])
        self.ax_1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M")) 
        plt.xticks(rotation=30)
        self.ax_1.set_axisbelow(True)
        self.ax_1.grid(True)

        # 出来高
        self.ax_1v.bar(idx1,df.loc[idx1,"Volume"],width=w,color="#33c076",edgecolor="#33b066",linewidth=1)
        self.ax_1v.bar(idx0,df.loc[idx0,"Volume"],width=w,color="#ff6060",edgecolor="#ff5050",linewidth=1)
        # 出来高目盛が価格目盛にかぶらないよう調整
        ymax=df["Volume"].max()
        self.ax_1v.set_ylim(0,ymax*5)
        ytick=ymax//3
        tmp=0
        cnt=0
        while ytick-tmp>0:
            cnt+=1
            ytick-=tmp
            tmp=ytick%(10**cnt)
        self.ax_1v.set_axisbelow(True)
        self.ax_1v.set_yticks(np.arange(0,ymax,ytick))
        self.ax_1v.tick_params(left=True,labelleft=True,right=False,labelright=False)
        self.ax_1v.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
