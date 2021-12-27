import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import dates as mdates
import numpy as np
from contextlib import redirect_stdout
import os

def ohlcv_plot(ax,df):
    """
    matplotlibのAxesオブジェクトにローソク足を描画する.
    :param ax:ローソク足を描画するAxesオブジェクト.
    :param df:DataFrameオブジェクト. 必要なカラムはtimestamp,open,high,low,close,volume.
    """

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
    with redirect_stdout(open(os.devnull, 'w')):
        df["body"]=df["Close"]-df["Open"]
        df["body"]=df["body"].abs()
    ax.bar(idx1,df.loc[idx1,"body"],width=w * (1-0.2),bottom=df.loc[idx1,"Open"],linewidth=1,color="#33b066",zorder=2)
    ax.bar(idx0,df.loc[idx0,"body"],width=w * (1-0.2),bottom=df.loc[idx0,"Close"],linewidth=1,color="#ff5050",zorder=2)

    # ヒゲ
    # zorderを指定して実体の後ろになるようにする。
    ax.vlines(df.index,df["Low"],df["High"],linewidth=1,color="#666666",zorder=1)

    # EMA
    ema3 = df["ema3"]
    ema7 = df["ema7"]
    ax.plot(df.index,ema3,color="#2EF9FF",linewidth=.5)
    ax.plot(df.index,ema7,color="#FF2ED6",linewidth=.5)

    # 価格目盛調整
    # グラフ下部に出来高の棒グラフを描画するので、そのためのスペースを空けるよう目盛を調整する
    ymin,ymax=df["Low"].min(),df["High"].max()
    ticks=ax.get_yticks()
    margin=(len(ticks)+4)/5
    tick_span=ticks[1]-ticks[0]
    min_tick=ticks[0]-tick_span*margin
    ax.set_ylim(min_tick, ticks[-1])
    ax.set_yticks(ticks[1:])
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M")) 
    plt.xticks(rotation=30)
    ax.set_axisbelow(True)
    ax.grid(True)

    # 出来高
    axv=ax.twinx()
    axv.bar(idx1,df.loc[idx1,"Volume"],width=w,color="#33c076",edgecolor="#33b066",linewidth=1)
    axv.bar(idx0,df.loc[idx0,"Volume"],width=w,color="#ff6060",edgecolor="#ff5050",linewidth=1)
    # 出来高目盛が価格目盛にかぶらないよう調整
    ymax=df["Volume"].max()
    axv.set_ylim(0,ymax*5)
    ytick=ymax//3
    tmp=0
    cnt=0
    while ytick-tmp>0:
        cnt+=1
        ytick-=tmp
        tmp=ytick%(10**cnt)
    axv.set_axisbelow(True)
    axv.set_yticks(np.arange(0,ymax,ytick))
    axv.tick_params(left=True,labelleft=True,right=False,labelright=False)
    axv.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
