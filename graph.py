import pandas as pd
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
import numpy as np

from strategy import GoldenCross

class Plot(object):
    def __init__(self, realtime=True):
        self.realtime = realtime
        self.fig = plt.figure(figsize=(8,6))
        self.gs_master = GridSpec(nrows=4, ncols=2, height_ratios=[1,1,1,1])
        self.gs_1 = GridSpecFromSubplotSpec(nrows=3, ncols=1, subplot_spec=self.gs_master[0:3, :])
        self.ax_1 = self.fig.add_subplot(self.gs_1[:,:])
        self.gs_2 = GridSpecFromSubplotSpec(nrows=1, ncols=1, subplot_spec=self.gs_master[3, :])
        self.ax_2 = self.fig.add_subplot(self.gs_2[:,:])
        self.ax_1v=self.ax_1.twinx()

    def plot_df(self, df):
        self.ohlcv_plot(df)
        self.ax_1.scatter(df.index, df["Long"].mask(df['Long'] == 1.0, df['Low']-20),marker="^",color="r",label="long")
        self.ax_1.scatter(df.index, df["Short"].mask(df['Short'] == 1.0, df['High']+20),marker="v",color="b",label="short")
        self.ax_1.legend()
        self.ax_2.plot(df.index, df["Profit"], color = "y")
        self.ax_2.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        if self.realtime:
            plt.pause(0.001)
            self.ax_1.cla()
            self.ax_1v.cla()
            self.ax_2.cla()
        else:
            plt.show()

    def ohlcv_plot(self, df):
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
        s_ema = df["ema"+str(GoldenCross.s_ema)]
        l_ema = df["ema"+str(GoldenCross.l_ema)]
        self.ax_1.plot(df.index,s_ema,color="#2EF9FF",linewidth=.5)
        self.ax_1.plot(df.index,l_ema,color="#FF2ED6",linewidth=.5)

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
        self.ax_1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        #plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M")) 
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
