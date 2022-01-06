import os
import time
import binance_f
from binance_f.model.constant import CandlestickInterval
from binance_f.exception.binanceapiexception import BinanceApiException
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
        self.presignal = 0
        self.preinterval = 0
        self.timestamp = 0
        self.profit = 0
        self.balance = 0
        self.firststep = True
    
    def excute(self):
        # botのメイン実行部分
        # TODO: 手数料含めた利益の計算
        # TODO: レンジ相場の場合無駄にエントリーさせない
        # TODO: interfaceのクラスをmanagerのクラスに継承させる -> 再接続時にinterfaceをもう一度インスタンス化させなおす可能性
        # TODO: 再接続の実装
        # TODO: log.pyの修正
        # 1分足のohlcvを読み取り
        df = self.interface.get_ohlcv_df(interval=CandlestickInterval.MIN1, limit=100)
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
        else:
            # ポジションを持ってないときはupnlを0に初期化
            self.logger.upnl = 0

        # 次の足までの残り時間
        server_time = self.interface.get_time()
        print("時刻：%s, 終値：%s, upnl：%s, rpnl：%s, trailing_line：%s, active_position:%s"%(datetime.fromtimestamp(server_time/1000),close,self.logger.upnl,self.logger.rpnl,self.manager.trailing_line,active_position))

        # 足が決まってからsignalを見る
        signal = 0
        if self.preinterval < curinterval:
            # policyに従ってsignal決定(signal=1:LONG signal=-1:SHORT signal=0:NOOP)
            signal, df = self.strategy.get_signal(df)
            print("signal:",signal)
            if signal == 1 or signal == -1:
                # ポジション持ってる場合
                if active_position:
                    self.close(signal, False, df)
                    time.sleep(0.5)
                    self.open(signal)
                # 持ってない場合
                else:
                    self.open(signal)
            self.logger.save_pnl(df)
            # ポジションサイドの保存
            self.logger.save_position_side(signal, df)
            self.preinterval = curinterval
        self.logger.tograph_mpl(df, signal)
    
    def open(self, signal):
        # ポジションをもつ
        balance = self.interface.get_futures_balance()
        self.balance = balance
        price = self.interface.get_mark_price()
        self.manager.open_position(balance, price, signal, self.interface)

    def close(self, signal, risk, df):
        # ポジションを閉じる
        pos = self.interface.get_specific_positon()
        rpnl = self.manager.close_position(pos, signal, risk, self.interface)
        self.logger.save_rpnl(df, rpnl)

    def exit(self):
        # botの停止
        self.close(None, True)
        self.save_log()

    def save_log(self):
        # データフレームをcsvにして保存
        print("output logging...")
        file_path = self.logger.save_to_csv(self.logger.df)
        print("log output '%s'"%(file_path))

def main():
    s = 'BTCUSDT'
    bot = Bot(symbol=s,margin_type='CROSSED',levarage=20)
    while True:
        try:
            bot.excute()
            time.sleep(0.5)
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