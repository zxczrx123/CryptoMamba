
def buy_sell_smart(today, pred, balance, shares, risk=5):
    diff = pred * risk / 100
    if today > pred + diff:
        balance += shares * today
        shares = 0
    elif today > pred:
        factor = (today - pred) / diff
        balance += shares * factor * today
        shares *= (1 - factor)
    elif today > pred - diff:
        factor = (pred - today) / diff
        shares += balance * factor / today
        balance *= (1 - factor)
    else:
        shares += balance / today
        balance = 0
    return balance, shares

def buy_sell_smart_w_short_v1(today, pred, balance, shares, risk=5, max_n_btc=0.002):
    diff = pred * risk / 100
    if today < pred - diff:
        shares += balance / today
        balance = 0
    elif today < pred:
        factor = (pred - today) / diff
        shares += balance * factor / today
        balance *= (1 - factor)
    elif today < pred + diff:
        if shares > 0:
            factor = (today - pred) / diff
            balance += shares * factor * today
            shares *= (1 - factor)
    else:
        balance += (shares + max_n_btc) * today
        shares = -max_n_btc
    return balance, shares

def buy_sell_smart_w_short(today, pred, balance, shares, initial_value=None, risk=5, max_n_btc=0.002, fee_rate=0.001, slippage=0.0005, stop_loss=0.008, take_profit=0.016):
    """
    加入止损、止盈机制和 initial_value 初始化的交易策略函数。

    参数:
    - today: 当前市场价格。
    - pred: 预测的未来价格。
    - balance: 当前现金余额。
    - shares: 当前持有的资产数量（正数为多头，负数为空头）。
    - initial_value: 初始持仓价值，默认为 None（首次调用时初始化）。
    - risk: 风险参数，控制交易的激进程度，默认值为5。
    - max_n_btc: 最大允许做空的资产数量，默认值为0.002。
    - fee_rate: 手续费率，默认值为0.001（0.1%）。
    - slippage: 滑点率，默认值为0.0005（0.05%）。
    - stop_loss: 止损比例，默认值为0.05（5%）。
    - take_profit: 止盈比例，默认值为0.10（10%）。
    """
    diff = pred * risk / 100

    # 考虑滑点调整实际成交价格
    def get_actual_price(price, is_buy):
        if is_buy:
            return price * (1 + slippage)  # 买入时价格上浮
        else:
            return price * (1 - slippage)  # 卖出时价格下浮

    # 考虑手续费调整交易成本
    def apply_fee(cost, is_buy):
        return cost * (1 + fee_rate) if is_buy else cost * (1 - fee_rate)

    # 初始化 initial_value（如果是首次开仓）
    if initial_value is None:
        initial_value = shares * today  # 初始持仓价值

    # 计算当前持仓的盈亏比例
    if shares != 0:
        current_value = shares * today
        pnl = (current_value - initial_value) / initial_value  # 盈亏比例

        # 止损逻辑
        if pnl <= -stop_loss:
            actual_price = get_actual_price(today, is_buy=False)
            revenue = shares * actual_price
            revenue_with_fee = apply_fee(revenue, is_buy=False)
            balance += revenue_with_fee
            shares = 0
            initial_value = 0  # 平仓后重置 initial_value
            return balance, shares, initial_value  # 返回更新后的 initial_value

        # 止盈逻辑
        if pnl >= take_profit:
            actual_price = get_actual_price(today, is_buy=False)
            revenue = shares * actual_price
            revenue_with_fee = apply_fee(revenue, is_buy=False)
            balance += revenue_with_fee
            shares = 0
            initial_value = 0  # 平仓后重置 initial_value
            return balance, shares, initial_value  # 返回更新后的 initial_value

    # 原策略逻辑
    if today < pred - diff:
        # 买入操作
        actual_price = get_actual_price(today, is_buy=True)
        cost = balance / actual_price
        cost_with_fee = apply_fee(cost, is_buy=True)
        shares += cost_with_fee
        balance = 0
        initial_value = shares * today  # 更新 initial_value
    elif today < pred:
        # 部分买入操作
        actual_price = get_actual_price(today, is_buy=True)
        factor = (pred - today) / diff
        cost = balance * factor / actual_price
        cost_with_fee = apply_fee(cost, is_buy=True)
        shares += cost_with_fee
        balance *= (1 - factor)
        initial_value = shares * today  # 更新 initial_value
    elif today < pred + diff:
        if shares > 0:
            # 卖出操作
            actual_price = get_actual_price(today, is_buy=False)
            factor = (today - pred) / diff
            revenue = shares * factor * actual_price
            revenue_with_fee = apply_fee(revenue, is_buy=False)
            balance += revenue_with_fee
            shares *= (1 - factor)
            initial_value = shares * today  # 更新 initial_value
    else:
        # 卖出全部并做空
        actual_price = get_actual_price(today, is_buy=False)
        revenue = (shares + max_n_btc) * actual_price
        revenue_with_fee = apply_fee(revenue, is_buy=False)
        balance += revenue_with_fee
        shares = -max_n_btc
        initial_value = shares * today  # 更新 initial_value

    return balance, shares, initial_value  # 返回更新后的 initial_value

def buy_sell_vanilla(today, pred, balance, shares, tr=0.001):
    tmp = abs((pred - today) / today)
    if tmp < tr:
        return balance, shares
    if pred > today:
        shares += balance / today
        balance = 0
    else:
        balance += shares * today
        shares = 0
    return balance, shares


def trade(data, time_key, timstamps, targets, preds, balance=100, mode='smart_v2', risk=5, y_key='Close'):
    balance_in_time = [balance]
    shares = 0
    initial_value = None
    for ts, target, pred in zip(timstamps, targets, preds):
        today = data[data[time_key] == int(ts - 60 * 60)].iloc[0][y_key]
        assert round(target, 2) == round(data[data[time_key] == int(ts)].iloc[0][y_key], 2)
        if mode == 'smart':
            balance, shares = buy_sell_smart(today, pred, balance, shares, risk=risk)
        if mode == 'smart_w_short':
            # balance, shares = buy_sell_smart_w_short_v1(today, pred, balance, shares, risk=risk, max_n_btc=0.002)
            balance, shares, initial_value = buy_sell_smart_w_short(today, pred, balance, shares, risk=risk, max_n_btc=0.002, initial_value=initial_value)
        elif mode == 'vanilla':
            balance, shares = buy_sell_vanilla(today, pred, balance, shares)
        elif mode == 'no_strategy':
            shares += balance / today
            balance = 0
        balance_in_time.append(shares * today + balance)

    balance += shares * targets[-1]
    return balance, balance_in_time