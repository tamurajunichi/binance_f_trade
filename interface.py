import os
from contextlib import redirect_stdout

from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *
from binance.client import Client
from binance_f.exception.binanceapiexception import BinanceApiException

import os
import pandas as pd
from datetime import datetime
import time

from backtest import Backtest

# バイナンス先物取引のインターフェース
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

    def _get_market_qty_precision(self):
        # オーダーに必要な桁数をもらう
        with redirect_stdout(open(os.devnull, 'w')):
            market_data = self.req.get_exchange_information()
        precision = 3
        for market in market_data.symbols:
            if market.symbol == self.symbol:
                precision = market.quantityPrecision
                break
        return precision

    def _get_market_price_precision(self):
        # オーダーに必要な桁数をもらう
        with redirect_stdout(open(os.devnull, 'w')):
            market_data = self.req.get_exchange_information()
        precision = 2
        for market in market_data.symbols:
            if market.symbol == self.symbol:
                precision = market.pricePrecision
                break
        return precision

    def _round_to_precision(self, value, precision):
        # オーダーを出すのに桁数合わせ
        new_value = "{:0.0{}f}".format(value , precision)
        return float(new_value)

    def convert_qty(self, qty):
        # 注文量の桁数を変換
        precision = self._get_market_qty_precision()
        qty = self._round_to_precision(qty,precision)
        return qty

    def convert_price(self, price):
        # 注文量の桁数を変換
        precision = self._get_market_price_precision()
        price = self._round_to_precision(price,precision)
        return price

    def order(self, type='LIMIT', side='BUY', position_side='BOTH', qty=1.0 ,time_in_force='GTC', price=0):
        # 注文
        qty = abs(qty)
        qty = self.convert_qty(qty)
        price = abs(price)
        price = self.convert_price(price)
        # 注文に失敗したらもう一度post
        while True:
            try:
                with redirect_stdout(open(os.devnull, 'w')):
                    res = self.req.post_order(symbol=self.symbol, ordertype=type,side=side, positionSide=position_side, quantity=str(qty), timeInForce=time_in_force, price=str(price))
                break
            except BinanceApiException as e:
                print(e)
                time.sleep(0.2)
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
        # レバレッジの変更
        with redirect_stdout(open(os.devnull, 'w')):
            res = self.req.change_initial_leverage(symbol=self.symbol, leverage=levarage)
        return res

    def change_margin_type(self, margin_type):
        # マージンタイプ変更
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

    def get_futures_balance(self, asset = "USDT"):
        # ウォレットにあるUSDTを取ってくる
        with redirect_stdout(open(os.devnull, 'w')):
            balances = self.req.get_balance()
        asset_balance = 0
        for balance in balances:
            if balance.asset == asset:
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
        with redirect_stdout(open(os.devnull, 'w')):
            order = self.req.get_order(self.symbol,id)
        return order 

    def cancel_order(self, id):
        with redirect_stdout(open(os.devnull, 'w')):
            result = self.req.cancel_order(self.symbol, id)
        return result

# TODO: バックテスト用のインターフェース
class BacktestInterface(object):
    def __init__(self, symbol):
        self.symbol = symbol
        self.bt = Backtest()

    def order(self, ordertype='MARKET', side='BUY', position_side='BOTH', qty=1.0):
        # 注文を投げる
        res = self.bt.post_order(symbol=self.symbol, ordertype=ordertype,side=side, positionSide=position_side, quantity=qty)
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
        candles = self.bt.get_candlestick_data(symbol=self.symbol, interval=interval,limit=limit)
        ot, o, h, l, c, v, ct = self._convert_candle(candles)
        df = self._to_dataframe(ot, o, h, l, c, v, ct)
        return df

    def change_levarage(self, levarage):
        # レバレッジの変更
        pass

    def change_margin_type(self, margin_type):
        # マージンタイプ変更
        pass

    def get_specific_positon(self):
        # BTCUSDT市場で持ってるポジションをとる
        self.bt.get_position()
        return position
    
    def check_in_position(self):
        # 市場のポジションを持ってるか確認、確認した時にself.positionを最新に更新
        self.position = self.get_specific_positon()
        in_position = False
        if float(self.position.positionAmt) != 0.0:
            in_position = True
        return in_position

    def get_symbol_price(self):
        # 現在のBTC価格
        price = self.bt.get_symbol_price_ticker(self.symbol)
        return price

    def get_futures_balance(self, asset = "USDT"):
        # ウォレットにあるUSDTを取ってくる
        balances = self.bt.get_balance()
        return balances

    def get_time(self):
        time = self.bt.get_servertime()
        return time

    def get_order(self, id):
        order = self.bt.get_order(self.symbol,id)
        return order 


if __name__ == "__main__":
    bi = BinanceInterface("BTCUSDT")
    price = bi.get_symbol_price()
    balance = bi.get_futures_balance()
    signal = 1
    from manager import Manager
    import time
    m = Manager(20, 0.04*0.01, 0.02*0.01)
    qty = m.calc_qty(balance, price, signal)
    o = bi.order(qty=qty,price=price)
    oid = o.orderId
    while True:
        time.sleep(1)
        o_info = bi.get_order(oid)
        status = o_info.status
        if status == "NEW":
            result = bi.cancel_order(oid)
            o = bi.order(qty=qty,price=price)
            oid = o.orderId
        elif status == "FILLED":
            break
    print("filled order")