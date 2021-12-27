import os
import time
from binance_f.model.constant import CandlestickInterval
import numpy as np
import pandas as pd
import mplfinance as mpf
import datetime

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import graph
from manager import Manager
from interface import BinanceInterface
from strategy import GoldenCross
from log import Logger

_api_key = os.environ.get('BINANCE_API_KEY')
_api_secret = os.environ.get('BINANCE_API_SECRET')

# 戦略を元に買いシグナルと売りシグナル
# binance_f -> interface.py -> information -> bot.py -> signal -> manager.py -> order
# strategyによるsignal出力 output_signal、positionに対するリスク管理 manage_position
class Bot():
    def __init__(self, symbol, margin_type, levarage):
        self.symbol = symbol
        self.margin = margin_type
        self.lev = levarage
        self.strategy = GoldenCross()
        self.interface = BinanceInterface(symbol)
        self.manager = Manager(levarage)
        self.logger = Logger()
        self.interface.change_levarage(levarage)
        self.interface.change_margin_type(margin_type)

        self.active_position = False
        self.timestamp = 0
        self.pre_time = 0
        self.profit = 0
    
    def excute(self):
        # 基本的にdfは読み込んだら捨てる
        # TODO: botの停止処理
        # TODO: 初回エントリーをクロスでエントリーさせるようにする
        # TODO: 損失の許容範囲と損切り(暴落対策) 
        # TODO: レンジ相場の場合無駄にエントリーさせない
        # TODO: 利益率を出す → calc_profit
        # TODO: botのログを残すようにする → save_df 
        test = False

        # 1分足のohlcvを読み取り
        df = self.interface.get_ohlcv_df(interval=CandlestickInterval.MIN1, limit=100)
        print("終値:",df.loc[df.index[-1], ["Close"]][0])

        # position持ってればリスクと損益計算
        if self.interface.check_in_position():
            pos = self.interface.get_specific_positon()
            balance = self.interface.get_futures_balance()
            pnl, roe = self.manager.calc_profit(pos, balance)
            stop_loss = self.manager.calc_risk(roe)
            if stop_loss:
                print("stop_loss")
                self.active_position = self.manager.close_position(pos, signal=None, risk=True, interface=self.interface)
            self.logger.save_profit(df, pnl)

        # 次の足までの残り時間
        time_res = self.interface.client.get_server_time()
        server_time = time_res['serverTime']
        print(self.timestamp - server_time)

        # 足が決まってからsignalを見る
        if self.timestamp < server_time:
            # policyに従ってsignal決定(signal=1:LONG signal=-1:SHORT signal=0:NOOP)
            signal, df = self.strategy.get_signal(df)
            print("signal:",signal)
            if self.active_position:
                pos = self.interface.get_specific_positon()
                self.active_position = self.manager.close_position(pos, signal,risk=False, interface=self.interface)
            else:
                balance = self.interface.get_futures_balance()
                price = self.interface.get_mark_price()
                self.active_position = self.manager.open_position(balance, price, signal=signal, interface=self.interface)
            self.logger.save_position_side(signal, df)
            self.logger.tograph_mpl(df)
        self.timestamp = df.loc[df.index[-1],["Close Time"]][0]

if __name__ == "__main__":
    bot = Bot(symbol='BTCUSDT',margin_type='CROSSED',levarage=20)
    while True:
        bot.excute()
        time.sleep(1)