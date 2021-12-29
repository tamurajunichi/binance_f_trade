import os
import time
from binance_f.model.constant import CandlestickInterval
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

from manager import Manager
from interface import BinanceInterface
from strategy import GoldenCross
from log import Logger

_api_key = os.environ.get('BINANCE_API_KEY')
_api_secret = os.environ.get('BINANCE_API_SECRET')

# binance_f -> interface.py -> information -> bot.py -> signal -> manager.py -> order
class Bot():
    def __init__(self, symbol, margin_type, levarage):
        self.symbol = symbol
        self.margin = margin_type
        self.lev = levarage
        self.strategy = GoldenCross()
        self.interface = BinanceInterface(symbol)
        self.manager = Manager(levarage, maker_fee=0.04, taker_fee=0.02)
        self.logger = Logger()
        self.interface.change_levarage(levarage)
        self.interface.change_margin_type(margin_type)

        self.active_position = False
        self.timestamp = 0
        self.profit = 0
        self.firststep = True
    
    def excute(self):
        # 基本的にdfは読み込んだら捨てる
        # TODO: botの停止処理
        # TODO: 初回エントリーをクロスでエントリーさせるようにする
        # TODO: 損失の許容範囲と損切り(暴落対策) 
        # TODO: レンジ相場の場合無駄にエントリーさせない
        # 1分足のohlcvを読み取り
        df = self.interface.get_ohlcv_df(interval=CandlestickInterval.MIN1, limit=100)
        print("終値:",df.loc[df.index[-1], ["Close"]][0])
        if self.firststep:
            self.timestamp = df.loc[df.index[-1],["Close Time"]][0]
            self.firststep = False

        # position持ってればリスクと損益計算
        if self.interface.check_in_position():
            pos = self.interface.get_specific_positon()
            upnl, roe = self.manager.calc_upnl(pos)
            stop_loss = self.manager.calc_risk(roe)
            if stop_loss:
                print("stop_loss")
                self.close(None, True)
            self.logger.save_upnl(df, upnl)

        # 次の足までの残り時間
        server_time = self.interface.get_time()
        print(datetime.fromtimestamp(server_time/1000))

        # 足が決まってからsignalを見る
        signal = 0
        if self.timestamp+3000 < server_time:
            # policyに従ってsignal決定(signal=1:LONG signal=-1:SHORT signal=0:NOOP)
            signal, df = self.strategy.get_signal(df)
            print("signal:",signal)
            # ポジション持ってる場合
            if self.active_position:
                self.close(signal, False)
                self.open(signal)
            # 持ってない場合
            else:
                self.open(signal)
            self.logger.save_position_side(signal, df)
            self.timestamp += 60000
        self.logger.tograph_mpl(df, signal)
    
    def open(self, signal):
        balance = self.interface.get_futures_balance()
        price = self.interface.get_mark_price()
        self.active_position = self.manager.open_position(balance, price, signal, self.interface)

    def close(self, signal, risk):
        pos = self.interface.get_specific_positon()
        self.active_position, pnl = self.manager.close_position(pos, signal, risk, self.interface)
        if not pnl is None:
            self.logger.save_pnl(pnl)

    def save_log(self):
        print("output logging...")
        file_path = self.logger.save_to_csv(self.logger.df)
        print("log output '%s'"%(file_path))

def main():
    bot = Bot(symbol='BTCUSDT',margin_type='CROSSED',levarage=20)
    try:
        while True:
            bot.excute()
            time.sleep(1)
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        bot.save_log()
        exit()

if __name__ == "__main__":
    main()