import time

class Manager(object):
    def __init__(self, lev, maker_fee, taker_fee):
        self.lev = lev
        self.signal = 0
        self.pos_side = None
        self.pos = None
        self.mark = 0
        self.longmark = 0
        self.shortmark = float('inf')
        self.trailing_line = 0
        self.trailing_diff = 1000
        # takerとmakerどっちになるかが分からない
        self.mfee = maker_fee*0.01
        self.tfee = taker_fee*0.01
        self.fee = 0
        self.cfee = 0
        self.orders = {}
        self.active = False

    def calc_qty(self, balance, price, signal):
        # 注文量の計算

        balance = float(balance)
        price = float(price)

        # 現在価格とウォレットから注文に必要なbtcの注文量を計算
        qty = (balance * self.lev) / price
        qty = qty * 0.8

        return qty
    
    def calc_fee(self, price, qty, interface):
        qty = abs(qty)
        qty = interface.convert_qty(qty)
        price = abs(price)
        price = interface.convert_price(price)
        cost = price*qty
        self.fee = cost*self.tfee
        self.cfee += self.fee
        print("price:%s, qty:%s, fee:%s"%(price,qty,self.fee))

    def buy(self, qty, price, interface):
        # 買い注文
        self.pos_side = "LONG"
        order = interface.order(side="BUY", qty=qty, price=price)
        orderid = order.orderId
        # 指値が成功するまで注文する
        while True:
            order = interface.get_order(orderid)
            status = order.status
            if status == "NEW":
                result = interface.cancel_order(orderid)
                price = interface.get_symbol_price()
                order = interface.order(side="BUY", qty=qty, price=price)
                orderid = order.orderId
            elif status == "FILLED":
                break
            time.sleep(0.2)
        print("filled order")
        self.orders[orderid] = order
        return orderid

    def sell(self, qty, price, interface):
        # 売り注文
        self.pos_side = "SHORT"
        order = interface.order(side="SELL", qty=qty, price=price)
        orderid = order.orderId
        # 指値が成功するまで注文する
        while True:
            order = interface.get_order(orderid)
            status = order.status
            if status == "NEW":
                result = interface.cancel_order(orderid)
                price = interface.get_symbol_price()
                order = interface.order(side="SELL", qty=qty, price=price)
                orderid = order.orderId
            elif status == "FILLED":
                break
            time.sleep(0.2)
        print("filled order")
        self.orders[orderid] = order
        return orderid

    def open_position(self, balance, price, signal, interface):
        # ポジションを持つ
        qty = self.calc_qty(balance, price, signal)
        fee = self.calc_fee(price, qty, interface)
        orderid = None
        if signal == 1:
            orderid = self.buy(qty, price, interface)
            self.active = True
        elif signal == -1:
            orderid = self.sell(qty, price, interface)
            self.active = True
        print("open position {} order id : {}, fee :{}".format(signal,orderid,self.fee))

    def close_position(self, pos, signal, risk, interface):
        # ポジションを閉じる
        qty = float(pos.positionAmt)
        price = interface.get_symbol_price()
        fee = self.calc_fee(price, qty, interface)
        pnl = 0
        orderid = None
        # open position -> buy or sell -> self.posside -> risk on -> close position
        # 損切、トレイリングストップの時
        if risk:
            if self.pos_side == "LONG":
                orderid = self.sell(qty, price, interface)
                self.active = False
            elif self.pos_side == "SHORT":
                orderid = self.buy(qty, price, interface)
                self.active = False
        # open position -> activate on -> calling close_position with signal at every a minutes -> signal 1 or -1 -> close position 
        # 通常時
        else:
            if signal == 1:
                orderid = self.buy(qty, price, interface)
                self.active = False
            elif signal == -1:
                orderid = self.sell(qty, price, interface)
                self.active = False
            else:
                pass
        print("close position {} order id : {}".format(signal,orderid))
        # ポジションを閉じた時に注文価格から確定pnlの計算
        if signal == 1 or signal == -1 or signal == None:
            avg_price = interface.get_exit_price(orderid)
            pnl = self.calc_pnl(qty, avg_price)
        return pnl

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
        # ポジション保存
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
        return pnl-self.fee, roe

    def calc_pnl(self, qty, close):
        # 確定pnlの計算
        pnl, roe = self._pnl(qty, self.entry, self.lev, close)
        # 手数料
        pnl = pnl - self.cfee
        self.cfee = 0
        return pnl

    def calc_risk(self, roe):
        # 損切の計算をする
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
        # トレイリングストップのラインを見て損切or利食いさせるか判断
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
            self.shortmark = float('inf')
            if self.longmark < self.mark:
                self.longmark = self.mark
                self.trailing_line = self.mark - self.trailing_diff
        elif self.pos_side == "SHORT":
            # longで使用するmarkpriceの初期化
            self.longmark = 0
            if self.shortmark > self.mark:
                self.shortmark = self.mark
                self.trailing_line = self.mark + self.trailing_diff
        else:
            pass

    def check_order(self, interface, orderid):
        # 注文が通ったか確認
        order_info = interface.get_order(orderid)
