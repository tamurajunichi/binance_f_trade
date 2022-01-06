class Manager(object):
    def __init__(self, lev, maker_fee, taker_fee):
        self.lev = lev
        self.signal = 0
        self.pos_side = None
        self.pos = None
        self.mark = 0
        self.longmark = 0
        self.shortmark = 1000000
        self.trailing_line = 0
        self.mfee = maker_fee*0.01
        self.tfee = taker_fee*0.01
        self.orders = {}
        self.active = False

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
        # pnlとroeの計算
        imr = 1/lev
        initial_margin = qty * entry * imr
        pnl = (close - entry) * qty
        roe = pnl/initial_margin
        return pnl, roe

    def calc_upnl(self, pos):
        # upnlの計算
        # posの保存
        self.pos = pos
        # 計算に必要なものをポジション情報から取得する
        qty = float(pos.positionAmt)
        mark = float(pos.markPrice)
        entry = float(pos.entryPrice)
        # エントリーした価格は確定pnlで使用するためメンバ変数に保存
        self.entry = entry
        self.mark = mark
        lev = float(pos.leverage)

        pnl, roe = self._pnl(qty, entry, lev, mark)
        roe = abs(roe)
        return pnl, roe

    def calc_pnl(self, qty, close):
        # 確定pnlの計算
        pnl, roe = self._pnl(qty, self.entry, self.lev, close)
        return pnl

    def calc_risk(self, roe):
        # トレイリングストップのラインを見る
        stop_loss = self.trailing_stop()
        if stop_loss:
            print("Trailing stop!!, mark price: %s trailing line: %s"%(self.mark,self.trailing_line))
            return stop_loss

        # 損切りラインの設定
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
    
    def trailing_stop(self):
        self.calc_trailing_line()
        if self.pos_side == "LONG":
            if self.trailing_line > self.mark:
                return True
        elif self.pos_side == "SHORT":
            if self.trailing_line < self.mark:
                return True
        else:
            pass
        return False

    def calc_trailing_line(self):
        # トレイリングストップするためのラインを設定
        if self.pos_side == "LONG":
            # shortで使用するmarkpriceの初期化
            self.shortmark = 10000000
            if self.longmark < self.mark:
                self.longmark = self.mark
                self.trailing_line = self.mark - 50
        elif self.pos_side == "SHORT":
            # longで使用するmarkpriceの初期化
            self.longmark = 0
            if self.shortmark > self.mark:
                self.shortmark = self.mark
                self.trailing_line = self.mark + 50
        else:
            pass

    def open_position(self, balance, price, signal, interface):
        # ポジションを持つ
        qty = self.calc_qty(balance, price, signal)
        orderid = None
        if signal == 1:
            orderid = self.buy(qty,interface)
            self.active = True
        elif signal == -1:
            orderid = self.sell(qty,interface)
            self.active = True
        print("open position {} order id : {}".format(signal,orderid))

    def close_position(self, pos, signal, risk, interface):
        # ポジションを閉じる
        qty = float(pos.positionAmt)
        pnl = 0
        orderid = None
        # open position -> buy or sell -> self.posside -> risk on -> close position
        # 損切、トレイリングストップの時
        if risk:
            if self.pos_side == "LONG":
                orderid = self.sell(qty, interface)
                self.active = False
            elif self.pos_side == "SHORT":
                orderid = self.buy(qty, interface)
                self.active = False
        # open position -> activate on -> calling close_position with signal at every a minutes -> signal 1 or -1 -> close position 
        # 通常時
        else:
            if signal == 1:
                orderid = self.buy(qty,interface)
                self.active = False
            elif signal == -1:
                orderid = self.sell(qty,interface)
                self.active = False
            else:
                pass
        print("close position {} order id : {}".format(signal,orderid))
        # ポジションを閉じた時に注文価格から確定pnlの計算
        if signal == 1 or signal == -1 or signal == None:
            avg_price = self.get_exit_price(interface, orderid)
            pnl = self.calc_pnl(qty, avg_price)
        return pnl

    @staticmethod
    def get_exit_price(interface, orderid):
        # ポジションを閉じた時の注文から注文時の価格を取得する（pnl計算で使用）
        order_info = interface.get_order(orderid)
        avg_price = order_info.avgPrice
        return avg_price

    def check_order(self, interface, orderid):
        # 注文が通ったか確認
        order_info = interface.get_order(orderid)
