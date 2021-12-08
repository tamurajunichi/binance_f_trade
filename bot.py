from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *
from binance.client import Client
import os
from contextlib import redirect_stdout
import time
import numpy as np
import pandas as pd
import mplfinance as mpf
import datetime

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec
import graph

_api_key = os.environ.get('BINANCE_API_KEY')
_api_secret = os.environ.get('BINANCE_API_SECRET')

class Bot():
    def __init__(self,symbol,margin_type,levarage):
        self.req = RequestClient(api_key=_api_key, secret_key=_api_secret, url='https://fapi.binance.com')
        self.client = Client(_api_key, _api_secret)
        self.symbol = symbol
        self.margin = margin_type
        self.lev = levarage
        self.position = self.get_specific_positon()
        self.active_position = False
        self.order_side = 0
        self.long = []
        self.short = []
        self.initialize_futures(levarage=self.lev, margin_type=self.margin)
        self.df = None
        self.timestamp = 0
        self.first_step = True
        self.df_log_path = ""
        self.profit = 0

        self.count = 0

    def get_market_precision(self, _market="BTCUSDT"):

        market_data = self.req.get_exchange_information()
        precision = 3
        for market in market_data.symbols:
            if market.symbol == _market:
                precision = market.quantityPrecision
                break
        return precision

    def round_to_precision(self, qty, precision):
        # 注文を出すのに桁数合わせ
        new_qty = "{:0.0{}f}".format(qty , precision)
        return float(new_qty)

    def order(self, type='MARKET', side='BUY', position_side='BOTH', qty=1.0):
        res = self.req.post_order(
            symbol=self.symbol,
            ordertype=type,
            side=side,
            positionSide=position_side,
            quantity=str(qty)
        )
        return res

    def change_levarage(self, levarage):
        res = self.req.change_initial_leverage(symbol=self.symbol, leverage=levarage)
        return res

    def change_margin_type(self, margin_type):
        try:
            res = self.req.change_margin_type(symbol=self.symbol, marginType=margin_type)
        except Exception as e:
            print("Error:",e)
            res = None
        return res

    def calc_qty(self, side):
        # バイナンスの手数料,maker=0.04% taker=0.02%
        if side == 1:
            fee = 0.0004
        elif side == -1:
            fee = 0.0002

        # 現在の価格とウォレットから注文に必要なbtc量を計算(手数料いらんかも)
        price = self.get_symbol_price()
        balance = self.get_futures_balance()
        print('balance : ',balance)
        qty = (balance * self.lev) / price
        fee = price * qty * fee
        qty = ((balance-fee) * self.lev) / price
        return qty

    def initialize_futures(self, levarage, margin_type):
        # レバレッジとマージンタイプを変える
        print("initialize futures")
        self.change_levarage(levarage)
        self.change_margin_type(margin_type)

    def get_positions(self):
        # 今のポジションを全て取ってくる
        with redirect_stdout(open(os.devnull, 'w')):
            positions = self.req.get_position_v2()
        return positions

    def get_specific_positon(self):
        # BTCUSDT市場で持ってるポジションをとる
        positions = self.get_positions()
        for position in positions:
            if position.symbol == self.symbol:
                break
        return position
    
    def check_in_position(self):
        # 市場のポジションを持ってるか確認、確認した時にself.positionを最新に更新
        self.position = self.get_specific_positon()

        in_position = False

        if float(self.position.positionAmt) != 0.0:
            in_position = True

        return in_position

    def get_mark_price(self):
        # 現在のBTCのマーク価格
        price = self.req.get_mark_price(self.symbol)
        return price[0].price

    def get_symbol_price(self):
        # 現在のBTC価格
        price = self.req.get_symbol_price_ticker(self.symbol)
        return price[0].price

    def get_futures_balance(self, _asset = "USDT"):
        # ウォレットにあるUSDTを取ってくる
        balances = self.req.get_balance()
        asset_balance = 0
        for balance in balances:
            if balance.asset == _asset:
                asset_balance = balance.balance
                break
        return asset_balance

    def get_ohlcv(self, interval, limit):
        # ローソク足を直近からlimitの数だけ取ってくる
        candles = self.req.get_candlestick_data(symbol=self.symbol, interval=interval,limit=limit)
        return candles

    def convert_candle(self,candles):
        ot = []
        o = []
        h = []
        l = []
        c = []
        v = []
        ct = []
        for candle in candles:
            ot.append(int(candle.openTime))
            o.append(float(candle.open))
            h.append(float(candle.high))
            l.append(float(candle.low))
            c.append(float(candle.close))
            v.append(float(candle.volume))
            ct.append(int(candle.closeTime))
        return ot, o, h, l, c, v, ct

    def to_dataframe(self,ot,o, h, l, c, v, ct):
        df = pd.DataFrame()
        df['Open Time'] = ot
        df['Open'] = o
        df['High'] = h
        df['Low'] = l
        df['Close'] = c
        df['Volume'] = v
        df['Close Time'] = ct
        return df

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
        if len(self.long) > 0:
            for i in self.long:
                df.loc[df.index[i],['Long']] = 1.0
        ax_1.scatter(df.index, df["Long"].mask(df['Long'] == 1.0, df['Low']-20),marker="^",color="r",label="long")
        if len(self.short) > 0:
            for i in self.short:
                df.loc[df.index[i],['Short']] = 1.0
        ax_1.scatter(df.index, df["Short"].mask(df['Short'] == 1.0, df['High']+20),marker="v",color="b",label="short")
        ax_1.legend()
       
        ax_2.plot(df.index, df["Profit"], color = "y")
        plt.savefig('candle_mpl.png')
        self.save_df(df)

    def add_ema(self, df, n):
        # emaをデータフレーム入れて返す
        c_name = "ema"+str(n)
        df[c_name] = df["Close"].ewm(span=n).mean()
        return df

    def construct_df(self,limit):
        # ohlcv+αのデータフレームを作成
        candles = self.get_ohlcv(CandlestickInterval.MIN1, limit)
        self.timestamp = candles[-1].closeTime
        ot,o,h,l,c,v,ct = self.convert_candle(candles)
        df = self.to_dataframe(ot,o,h,l,c,v,ct)
        return df

    def open_position(self, side, test=True):
        if not test:
            # 1回目のopen orderのためにprev_positionをsideと逆に設定する
            # TODO: 改善
            if self.active_position == False:
                if side == 1:
                    self.prev_position = -1
                elif side == -1:
                    self.prev_position = 1

            #新しいposition用のqtyを計算
            qty = self.calc_qty(side)
            # 80%で取引する
            qty = qty * 0.8
            precision = self.get_market_precision()
            qty = self.round_to_precision(qty,precision)
            if side == 1 and self.prev_position == -1:
                res = self.order(side='BUY', qty=qty)
                print("OPEN LONG")
                self.active_position = True
                self.prev_position = 1
                self.save_position(side)
                self.position = self.get_specific_positon()
                self.oder_side = side

            elif side == -1 and self.prev_position == 1:
                res = self.order(side='SELL', qty=qty)
                print("OPEN SHORT")
                self.active_position = True
                self.prev_position = -1
                self.save_position(side)
                self.position = self.get_specific_positon()
                self.oder_side = side
            else:
                pass
        # test用
        else:
            # 1回目のopen orderのためにprev_positionをsideと逆に設定する
            if self.active_position == False:
                if side == 1:
                    self.prev_position = -1
                elif side == -1:
                    self.prev_position = 1

            if side == 1 and self.prev_position == -1:
                print("OPEN LONG")
                self.active_position = True
                self.prev_position = 1
                self.save_position(side)
            elif side == -1 and self.prev_position == 1:
                print("OPEN SHORT")
                self.active_position = True
                self.prev_position = -1
                self.save_position(side)
            else:
                pass

    def close_position(self, side, test=True):
        if not test:
            # positionからqtyを計算
            amt = self.position.positionAmt
            amt = abs(float(amt))
            # ショートのポジションは反転してるので直す
            precision = self.get_market_precision()
            amt = self.round_to_precision(amt,precision)

            profit = 0
            # side + prev_side を見ることでemaのゴールデンクロスが変わったところでpositionを抜ける
            if side == 1 and self.prev_position == -1:
                res = self.order(side='BUY', qty=amt)
                print("CLOSE SHORT")
                self.active_position = False
                self.calc_profit()
                self.order_side = 0
            elif side == -1 and self.prev_position == 1:
                res = self.order(side='SELL', qty=amt)
                print("CLOSE LONG")
                self.active_position = False
                self.calc_profit()
                self.order_side = 0
            else:
                pass

            # position精算チェック
            if self.active_position == False:
                in_position = self.check_in_position()
                if in_position:
                    print("close error : position amt ", self.position.positionAmt)
        # test用
        else:
            if side == 1 and self.prev_position == -1:
                print("CLOSE SHORT")
                self.active_position = False
            elif side == -1 and self.prev_position == 1:
                print("CLOSE LONG")
                self.active_position = False
            else:
                pass
    
    def save_position(self, side):
        # log保存用
        if side == 1:
            order_side = "LONG"
            self.long.append(self.df.index[-1])
        elif side == -1:
            order_side = "SHORT"
            self.short.append(self.df.index[-1])

    def excute(self):
        # TODO: botの停止処理
        # TODO: 初回エントリーをクロスでエントリーさせるようにする
        # TODO: 損失の許容範囲と損切り(暴落対策) 
        # TODO: レンジ相場の場合無駄にエントリーさせない
        # TODO: 利益率を出す → calc_profit
        # TODO: botのログを残すようにする → save_df 
        test = False
        # policyに従ってorder side決定(side=1:LONG side=-1:SHORT side=0:NOOP)
        signal = self.policy()

        # 次の足までの残り時間
        time_res = self.client.get_server_time()
        server_time = time_res['serverTime']
        wait_time = self.timestamp - server_time

        # 足が決まったらpositionとる
        if wait_time < 0:
            # 初回のposition
            if self.active_position == False:
                self.open_position(signal,test)
            # 2回目以降　positionを精算後に逆のpositionを持つ
            else:
                self.close_position(signal,test)
                self.open_position(signal,test)

    def policy(self):
    # ema(2)とema(5)のゴールデンクロス
    # ema(2)>ema(5)でLONG,ema(2)<ema(5)でSHORT
        signal = 0
        #　最初の実行時は100のohlcvをとる
        if self.first_step:
            df = self.construct_df(limit=100)
            self.df = df
            # long と　shortを追加
            self.df["Long"] = pd.Series()
            self.df["Short"] = pd.Series()
            self.df["Profit"] = 0
            self.initialize_log_name()
            self.first_step = False
        else:
            df = self.construct_df(limit=2)
            # 末尾を消去してから２つ新しいものを追加する(他に良い方法を求む)ことで新しい1mklineを追加していく
            self.df = self.df[:-1]
            # 分足完成ごとに足していく
            self.df = self.df.append(df,ignore_index=False).drop_duplicates(subset='Open Time').reset_index(drop=True)

        # emaを算出してdfに付け足す
        self.df = self.add_ema(self.df,3)
        self.df = self.add_ema(self.df,7)

        ema3 = self.df.loc[self.df.index[-1],["ema3"]][0]
        ema7 = self.df.loc[self.df.index[-1],["ema7"]][0]
        # long
        if ema3 > ema7:
            signal = 1
        # short
        elif ema3 < ema7:
            signal = -1

        # グラフの出力
        #self.tograph(self.df)
        self.tograph_mpl(self.df)
        return signal

    def  initialize_log_name(self):
        # savedfで使用するログのパスを作る
            dt_now = datetime.datetime.now()
            log_dir = 'df_log/'
            file_name = dt_now.strftime('%Y-%m-%d_%H:%M:%S')
            self.df_log_path = log_dir + file_name + '.csv'
    
    def save_df(self, df):
        # logで溜め込んだohlcvデータをcsvにする
        df.to_csv(self.df_log_path)

    def calc_profit(self):
        # ポジション終了時の損益の計算　closeする時に呼び出す
        entry_price = float(self.position.entryPrice)
        exit_price = float(self.get_symbol_price())
        qty = self.position.positionAmt
        qty = abs(float(qty))
        profit = ((1/entry_price)-(1/exit_price))*(entry_price*qty*self.oder_side)
        # usdtへ変換 
        profit = profit * exit_price
        self.profit += profit
        # 最新の足が完成するため-2
        self.df.loc[self.df.index[-2], ['Profit']]

    def calc_upnl(self):
        # マーク価格：先物の評価価格
        # インデックス価格：取引所間の現物の平均
        # uPNL:マーク価格利用した未実現損益
        if self.check_in_position:
            upnl = self.position.unRealizedProfit
        else:
            upnl = None
        return upnl


if __name__ == "__main__":
    bot = Bot(symbol='BTCUSDT',margin_type='CROSSED',levarage=20)
    while True:
        bot.excute()
        time.sleep(1)