class Manager(object):
    def __init__(self, lev):
        self.lev = lev
        self.signal = 0
        self.pos_side = None
        self.active_pos = False

    def calc_qty(self, balance, price, signal):
        # バイナンスの手数料,maker=0.04% taker=0.02%
        if signal == 1:
            fee = 0.0004
        elif signal == -1:
            fee = 0.0002
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
        self.pos_side = "LONG"
        interface.order(side="BUY", qty=qty)

    def sell(self, qty, interface):
        self.pos_side = "SHORT"
        interface.order(side="SELL", qty=qty)

    def calc_profit(self, pos, balance):
        # 最新の終値を読み取る
        qty = float(pos.positionAmt)
        mark = float(pos.markPrice)
        entry = float(pos.entryPrice)
        lev = float(pos.leverage)
        imr = 1/lev
        upnl = float(pos.unrealizedProfit)
        blance = float(balance)

        initial_margin = qty * entry * imr
        pnl = (mark - entry) * qty
        roe = pnl/initial_margin
        self.roe = roe
        if pnl < 0:
            roe *= -1
        return pnl, roe

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
        if signal == 1:
            self.buy(qty,interface)
            return True
        elif signal == -1:
            self.sell(qty,interface)
            return True
        else:
            return False

    def close_position(self, pos, signal, risk, interface):
        qty = float(pos.positionAmt)
        if qty != 0.0:
            activate = True
            # riskの時
            if risk:
                if self.pos_side == "LONG":
                    self.buy(qty, interface)
                elif self.pos_side == "SHORT":
                    self.sell(qty, interface)
                activate = False
            # signal使う時
            else:
                if signal == 1:
                    self.buy(interface)
                    activate =  False
                elif signal == -1:
                    self.sell(interface)
                    activate =  False
                else:
                    pass
            return activate