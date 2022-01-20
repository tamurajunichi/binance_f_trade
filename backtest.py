import pandas as pd

column_name = [
    "Open Time",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Close Time",
    "Quote asset volume",
    "Number of trades",
    "Taker base volume",
    "Taker quote volume",
    "ignored"
]

class Order(object):
    def __init__(self, status, orderId, side, qty, price):
        self.status = status
        self.orderId = orderId
        self.avgPrice = price
        self.side = side
        self.qty = qty
        self.price = price

class Position(object):
    def __init__(self,qty,price):
        self.positionAmt = qty
        self.markPrice = price
        self.entryPrice = price
        self.leverage = 20

class Backtest(object):
    def __init__(self):
        symbol = "BTCUSDT"
        candle = "1m"
        y= "2021"
        m="11".zfill(2)
        file_dir = "future_klines/%s/%s/"%(symbol,candle)
        file_name = "%s-%s-%s-%s"%(symbol,candle,y,m)
        self.df = pd.read_csv(file_dir+file_name+".csv",names=column_name)
        self.df_idx = 100
        self.tick = 0
        self.candle_tick = 0

        self.balance = 10
        self.tfee = 0.04*0.01
        self.fee = 0

        self.orders = []
        self.order_count = 0

        self.position = Position(0.0, 0.0)

    @staticmethod
    def _pnl(qty, entry, lev, close):
        # pnlとroeの計算
        imr = 1/lev
        initial_margin = qty * entry * imr
        pnl = (close - entry) * qty
        roe = pnl/initial_margin
        return pnl, roe


    def post_order(self, symbol=None, ordertype="LIMIT",side=None, positionSide="BOTH", qty=0, timeInForce="GTC", price=0):
        # もらったオーダーの処理
        o = Order(status="FILLED", orderId=self.order_count, side=side, qty=qty, price=price)
        self.order_count+=1
        self.orders.append(o)

        # balanceから手数料を引く
        cost = price*qty
        self.fee = cost*self.tfee
        self.balance -= self.fee

        # positionを保存
        if self.order_count % 2 == 0:
            # ポジションを閉じたときの計算
            pnl,roe = self._pnl(qty=qty, entry=self.position.entryPrice, lev=20, close=price)
            self.balance += pnl
            # ポジションを初期化
            self.position = Position(0.0, price)
        else:
            self.position = Position(qty, price)

        # オーダーオブジェクトを返す
        return o

    def get_candlestick_data(self, symbol=None, interval=None, limit=None):
        # dfを渡す
        df = self.df[["Open Time", "Open", "High", "Low", "Close", "Volume", "Close Time"]].copy()
        idx = self.df_idx+self.tick
        df = df[idx-100:idx]

        # 内部は足ごとに4tick状態を持つ
        column = "Close"
        if self.candle_tick == 0:
            column = "Open"
        elif self.candle_tick == 1:
            column = "High"
        elif self.candle_tick == 2:
            column = "Low"
        elif self.candle_tick == 3:
            pass
        df.loc[idx-1,"Close"] = df.loc[idx-1,column]

        # 足tickを1進める
        self.candle_tick += 1
        if self.candle_tick == 3:
            self.candle_tick = 0
            self.tick += 1
        return df

    def get_position(self):
        pos = self.position
        return pos

    def get_symbol_price_ticker(self,symbol=None):
        df = self.df[["Open Time", "Open", "High", "Low", "Close", "Volume", "Close Time"]].copy()
        idx = self.df_idx+self.tick

        # 内部は足ごとに4tick状態を持つ
        column = "Close"
        if self.candle_tick == 0:
            column = "Open"
        elif self.candle_tick == 1:
            column = "High"
        elif self.candle_tick == 2:
            column = "Low"
        elif self.candle_tick == 3:
            pass
        df.loc[idx-1,"Close"] = df.loc[idx-1,column]

        price = df.loc[idx,"Close"]
        return price

    def get_balance(self):
        balance = self.balance
        return balance

    def get_servertime(self):
        idx = self.df_idx+self.tick
        time = self.df.loc[idx,"Open Time"]
        return time

    def get_order(self, symbol=None, oid=0):
        return self.orders[oid]

def main():
    bt = Backtest()
    df = bt.get_candlestick_data()
    print(df)

if __name__ == "__main__":
    main()