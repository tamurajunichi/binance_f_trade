import os
from contextlib import redirect_stdout

from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *
from binance.client import Client

import os
import pandas as pd
from datetime import datetime

# バイナンス先物取引のインターフェースクラス
# binance_f -> interface.py -> info
class BinanceInterface(object):
    def __init__(self, symbol):
        _api_key = os.environ.get('BINANCE_API_KEY')
        _api_secret = os.environ.get('BINANCE_API_SECRET')
        self.req = RequestClient(api_key=_api_key, secret_key=_api_secret, url='https://fapi.binance.com')
        #self.client = Client(_api_key, _api_secret)
        self.symbol = symbol
        # api呼び出し回数
        self.count = 0

    def _get_market_precision(self):
        # オーダーに必要な桁数をもらう
        market_data = self.req.get_exchange_information()
        precision = 3
        for market in market_data.symbols:
            if market.symbol == self.symbol:
                precision = market.quantityPrecision
                break
        return precision

    def _round_to_precision(self, qty, precision):
        # オーダーを出すのに桁数合わせ
        new_qty = "{:0.0{}f}".format(qty , precision)
        return float(new_qty)

    def _convert_qty(self, qty):
        # 注文量の桁数を変換
        precision = self._get_market_precision()
        qty = self._round_to_precision(qty,precision)
        return qty

    def order(self, type='MARKET', side='BUY', position_side='BOTH', qty=1.0):
        with redirect_stdout(open(os.devnull, 'w')):
            qty = self._convert_qty(qty)
            res = self.req.post_order(
                symbol=self.symbol,
                ordertype=type,
                side=side,
                positionSide=position_side,
                quantity=str(qty)
            )
        return res

    def _convert_candle(self,candles):
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

    def _to_dataframe(self,ot,o, h, l, c, v, ct):
        df = pd.DataFrame()
        df['Open Time'] = ot
        df['Open'] = o
        df['High'] = h
        df['Low'] = l
        df['Close'] = c
        df['Volume'] = v
        df['Close Time'] = ct
        return df

    def get_ohlcv_df(self, interval, limit):
        # ローソク足を直近からlimitの数だけ取ってくる
        with redirect_stdout(open(os.devnull, 'w')):
            candles = self.req.get_candlestick_data(symbol=self.symbol, interval=interval,limit=limit)
        ot, o, h, l, c, v, ct = self._convert_candle(candles)
        df = self._to_dataframe(ot, o, h, l, c, v, ct)
        return df

    def change_levarage(self, levarage):
        with redirect_stdout(open(os.devnull, 'w')):
            res = self.req.change_initial_leverage(symbol=self.symbol, leverage=levarage)
        return res

    def change_margin_type(self, margin_type):
        with redirect_stdout(open(os.devnull, 'w')):
            try:
                res = self.req.change_margin_type(symbol=self.symbol, marginType=margin_type)
            except Exception as e:
                print("Error:",e)
                res = None
        return res

    def _get_positions(self):
        # 今のポジションを全て取ってくる
        with redirect_stdout(open(os.devnull, 'w')):
            positions = self.req.get_position_v2()
        return positions

    def get_specific_positon(self):
        # BTCUSDT市場で持ってるポジションをとる
        positions = self._get_positions()
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
        with redirect_stdout(open(os.devnull, 'w')):
            price = self.req.get_mark_price(self.symbol)
        return price.markPrice

    def get_symbol_price(self):
        # 現在のBTC価格
        with redirect_stdout(open(os.devnull, 'w')):
            price = self.req.get_symbol_price_ticker(self.symbol)
        return price[0].price

    def get_futures_balance(self, _asset = "USDT"):
        # ウォレットにあるUSDTを取ってくる
        with redirect_stdout(open(os.devnull, 'w')):
            balances = self.req.get_balance()
        asset_balance = 0
        for balance in balances:
            if balance.asset == _asset:
                asset_balance = balance.balance
                break
        return asset_balance

    def get_time(self):
        with redirect_stdout(open(os.devnull, 'w')):
            time = self.req.get_servertime()
        return time

    def get_all_orders(self):
        with redirect_stdout(open(os.devnull, 'w')):
            orders =  self.req.get_all_orders(self.symbol)
        return orders   

    def get_order(self, id):
        #with redirect_stdout(open(os.devnull, 'w')):
        order = self.req.get_order(self.symbol,id)
        return order 

# TODO: バックテスト用のインターフェース
class BacktestInterface(object):
    pass

if __name__ == "__main__":
    bi = BinanceInterface("BTCUSDT")
    res = bi.order(qty=0.001)
    print(res.orderId)
    o = bi.get_all_orders()
    o= bi.get_order(o[-1].orderId)
    print(o.avgPrice)
    print(datetime.fromtimestamp(o.updateTime/1000))