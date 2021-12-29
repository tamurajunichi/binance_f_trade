class Manager(object):
    def __init__(self, lev, maker_fee, taker_fee):
        self.lev = lev
        self.signal = 0
        self.pos_side = None
        self.mfee = maker_fee*0.01
        self.tfee = taker_fee*0.01
        self.orders = {}

    def calc_qty(self, balance, price, signal):
        # 注文量の計算
        if signal == 1:
            fee = self.mfee
        elif signal == -1:
            fee = self.tfee
        else:
            return 0
        balance = float(balance)
        price = float(price)
        # 現在の価格とウォレットから注文に必要なbtc量を計算(手数料いらんかも)
        qty = (balance * self.lev) / price
        fee = price * qty * fee
        qty = ((balance-fee) * self.lev) / price
        # TODO: 破産確率を元に出す
        qty = qty * 0.8
        return qty

    def buy(self, qty, interface):
        # 買い注文
        self.pos_side = "LONG"
        order_info = interface.order(side="BUY", qty=qty)
        self.orders[order_info.orderId] = order_info
        return order_info.orderId

    def sell(self, qty, interface):
        # 売り注文
        self.pos_side = "SHORT"
        order_info = interface.order(side="SELL", qty=qty)
        self.orders[order_info.orderId] = order_info
        return order_info.orderId

    @staticmethod
    def _pnl(qty, entry, lev, close):
        imr = 1/lev
        initial_margin = qty * entry * imr
        pnl = (close - entry) * qty
        roe = pnl/initial_margin
        return pnl, roe

    def calc_upnl(self, pos):
        qty = float(pos.positionAmt)
        mark = float(pos.markPrice)
        entry = float(pos.entryPrice)
        self.entry = entry
        lev = float(pos.leverage)

        pnl, roe = self._pnl(qty, entry, lev, mark)
        roe = abs(roe)
        return pnl, roe

    def calc_pnl(self, qty, close):
        pnl, roe = self._pnl(qty, self.entry, self.lev, close)
        return pnl

    def calc_risk(self, roe):
        if roe < 0:
            roe = abs(roe)
            threshold = 10.0
            if threshold < roe:
                stop_loss = True
            else:
                stop_loss = False
        else:
            stop_loss = False

        return stop_loss

    def open_position(self, balance, price, signal, interface):
        qty = self.calc_qty(balance, price, signal)
        activate = False
        orderid = None
        if signal == 1:
            orderid = self.buy(qty,interface)
            activate = True
        elif signal == -1:
            orderid = self.sell(qty,interface)
            activate = True

        return activate

    def close_position(self, pos, signal, risk, interface):
        qty = float(pos.positionAmt)
        activate = True
        if qty != 0.0:
            # riskの時
            # open position -> buy or sell -> self.posside -> risk on -> close position
            if risk:
                if self.pos_side == "LONG":
                    orderid = self.buy(qty, interface)
                elif self.pos_side == "SHORT":
                    orderid = self.sell(qty, interface)
                activate = False
            # signal使う時
            # open position -> activate on -> calling close_position with signal at every a minutes -> signal 1 or -1 -> close position 
            else:
                if signal == 1:
                    orderid = self.buy(qty,interface)
                    activate =  False
                elif signal == -1:
                    orderid = self.sell(qty,interface)
                    activate =  False
                else:
                    pass
            if not activate:
                avg_price = self.check_order(interface, orderid)
                pnl = self.calc_pnl(qty, avg_price)
            else:
                pnl = None
            return activate, pnl

    def check_order(self, interface, orderid):
        order_info = interface.get_order(orderid)
        avg_price = order_info.avgPrice
        return avg_price