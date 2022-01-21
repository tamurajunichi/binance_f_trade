
import numpy as np
import pandas as pd

class GoldenCross(object):
    s_ema = 10
    l_ema = 30
    def __init__(self) -> None:
        self.df = None

    @staticmethod
    def add_ema(df, n):
        # emaをデータフレーム入れて返す
        c_name = "ema"+str(n)
        df[c_name] = df["Close"].ewm(span=n).mean()
        return df

    def get_signal(self, df):
        signal = 0
        # emaを算出してdfに付け足す
        df = self.add_ema(df,GoldenCross.s_ema)
        df = self.add_ema(df,GoldenCross.l_ema)

        # 2個まえのemaからトレンドを判断
        pre_s_ema = df.loc[df.index[-3],["ema"+str(GoldenCross.s_ema)]][0]
        pre_l_ema = df.loc[df.index[-3],["ema"+str(GoldenCross.l_ema)]][0]
        if pre_s_ema > pre_l_ema:
            trend = 1
        elif pre_s_ema < pre_l_ema:
            trend = -1

        # 1個まえのemaとトレンドを比較してゴールデンクロスか判断
        cur_s_ema = df.loc[df.index[-2],["ema"+str(GoldenCross.s_ema)]][0]
        cur_l_ema = df.loc[df.index[-2],["ema"+str(GoldenCross.l_ema)]][0]
        if trend == -1 and cur_s_ema > cur_l_ema:
            signal = 1
        elif trend == 1 and cur_s_ema < cur_l_ema:
            signal = -1

        return signal, df