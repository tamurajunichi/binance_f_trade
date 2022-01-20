import os
import time
import binance_f
from binance_f.model.constant import CandlestickInterval
from binance_f.exception.binanceapiexception import BinanceApiException
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

from manager import Manager
from interface import BinanceInterface, BacktestInterface
from strategy import GoldenCross
from log import Logger

# binance_f -> interface.py -> information -> bot.py -> signal -> manager.py -> order
class Bot():
    def __init__(self, symbol, margin_type, levarage, backtest=False, plot=False):
        self.symbol = symbol
        self.margin = margin_type
        self.lev = levarage
        self.backtest = backtest

        self.strategy = GoldenCross()
        self.interface = BinanceInterface(symbol)
        if self.backtest:
            self.interface = BacktestInterface(symbol,backtest_balance=100)
        self.manager = Manager(levarage, maker_fee=0.02, taker_fee=0.04)
        self.logger = Logger(plot=plot)

        self.interface.change_levarage(levarage)
        self.interface.change_margin_type(margin_type)

        self.active_position = False
        self.presignal = 0
        self.preinterval = 0
        self.timestamp = 0
        self.profit = 0
        self.balance = 0
        self.firststep = True
        self.df = None
    
    def excute(self):
        # botのメイン実行部分

        # 1分足のohlcvを読み取り
        df = self.interface.get_ohlcv_df(interval=CandlestickInterval.MIN1, limit=100)
        self.df = df.copy()
        self.logger.save_df(df.copy())
        close = df.loc[df.index[-1],["Close"]][0]
        curinterval = df.loc[df.index[-1],["Close Time"]][0]

        # position持ってればリスクと損益計算
        active_position = self.interface.check_in_position()
        if active_position:
            pos = self.interface.get_specific_positon()
            upnl, roe = self.manager.calc_upnl(pos)
            stop_loss = self.manager.calc_risk(roe)
            if stop_loss:
                print("stop_loss")
                self.close(None, True, df)
            self.logger.save_upnl(df, upnl)
            self.logger.save_pnl(df)
        else:
            # ポジションを持ってないときはupnlを0に初期化
            self.logger.upnl = 0

        # 次の足までの残り時間
        server_time = self.interface.get_time()
        balance = self.interface.get_futures_balance()
        if self.firststep:
            self.init_balance = balance
            self.firststep = False
        print("time:%s, close:%.3f, tline:%.3f, upnl:%.3f, rpnl:%.3f, fee:%.3f, cfee:%.3f, apos:%s, ibal:%.3f, rbal:%.3f, bal:%.3f, diff:%.3f"\
            %(datetime.fromtimestamp(server_time/1000),close,self.manager.trailing_line,self.logger.upnl,self.logger.rpnl,self.manager.fee,self.manager.cfee,\
            active_position,self.init_balance,self.init_balance+self.logger.rpnl,balance,balance-self.init_balance))
        # 足が決まってからsignalを見る
        signal = 0
        if self.preinterval < curinterval:
            # 戦略に従ってsignal決定(signal=1:LONG signal=-1:SHORT signal=0:NOOP)
            signal, df = self.strategy.get_signal(df)
            print("signal:",signal)
            if signal == 1 or signal == -1:
                # ポジション持ってる場合
                if active_position:
                    self.close(signal, False, df)
                    self.open(signal)
                # 持ってない場合
                else:
                    self.open(signal)
            self.logger.save_pnl(df)
            # ポジションサイドの保存
            self.logger.save_position_side(signal, df)
            self.preinterval = curinterval
        self.logger.plot_df(df, signal)
    
    def open(self, signal):
        # ポジションをもつ
        balance = self.interface.get_futures_balance()
        self.balance = balance
        price = self.interface.get_symbol_price()
        self.manager.open_position(balance, price, signal, self.interface)

    def close(self, signal, risk, df):
        # ポジションを閉じる
        pos = self.interface.get_specific_positon()
        rpnl = self.manager.close_position(pos, signal, risk, self.interface)
        self.logger.save_rpnl(df, rpnl)

    def exit(self):
        # botの停止
        if self.active_position:
            self.close(None, True, self.df)
        self.save_log()

    def save_log(self):
        # データフレームをcsvにして保存
        print("output logging...")
        file_path = self.logger.save_to_csv()
        print("log output '%s'"%(file_path))

def main():
    s = 'BTCUSDT'
    backtest = True
    plot = False
    bot = Bot(symbol=s,margin_type='CROSSED',levarage=20, backtest=backtest, plot=plot)
    while True:
        try:
            bot.excute()
            if not backtest:
                time.sleep(1)
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            bot.exit()
            exit()
        except BinanceApiException as e:
            print("Binance api exception")
            print(str(e))
            bot.interface = BinanceInterface(s)
            pass
        except ConnectionError as e:
            print(e)
            pass

if __name__ == "__main__":
    main()