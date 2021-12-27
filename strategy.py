
import numpy as np
import pandas as pd

class GoldenCross(object):
    def __init__(self) -> None:
        self.first_step = True
        self.df = None

    def add_ema(self, df, n):
        # emaをデータフレーム入れて返す
        c_name = "ema"+str(n)
        df[c_name] = df["Close"].ewm(span=n).mean()
        return df

    def get_signal(self, df):
        signal = 0
        # emaを算出してdfに付け足す
        df = self.add_ema(df,3)
        df = self.add_ema(df,7)

        # 2個まえのemaからトレンドを判断
        pre_ema3 = df.loc[df.index[-3],["ema3"]][0]
        pre_ema7 = df.loc[df.index[-3],["ema7"]][0]
        if pre_ema3 > pre_ema7:
            trend = 1
        elif pre_ema3 < pre_ema7:
            trend = -1

        # 1個まえのemaとトレンドを比較してゴールデンクロスか判断
        cur_ema3 = df.loc[df.index[-2],["ema3"]][0]
        cur_ema7 = df.loc[df.index[-2],["ema7"]][0]
        if trend == -1 and cur_ema3 > cur_ema7:
            signal = 1
        elif trend == 1 and cur_ema3 < cur_ema7:
            signal = -1

        return signal, df