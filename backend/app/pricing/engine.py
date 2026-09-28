from decimal import Decimal, ROUND_HALF_UP

ROUNDING = {
    "NONE": None,
    "NEAREST_100": Decimal("100"),
    "NEAREST_1000": Decimal("1000"),
    "NEAREST_10000": Decimal("10000"),
    "NEAREST_100000": Decimal("100000"),
}

def money(v):
    return Decimal(str(v))

def calculate(purchase_price, exchange_rate, costs, margin_type, margin_value, rounding_method, rounding_value=None):
    pp = money(purchase_price) * money(exchange_rate)
    landed = pp + sum((money(x) for x in costs), Decimal("0"))
    margin = money(margin_value)
    if margin_type == "GROSS_MARGIN":
        if margin >= Decimal("1"):
            raise ValueError("GROSS_MARGIN must be less than 1")
        selling = landed / (Decimal("1") - margin)
    else:
        selling = landed * (Decimal("1") + margin)
    increment = money(rounding_value) if rounding_value else ROUNDING.get(rounding_method)
    final = selling
    if increment:
        final = (selling / increment).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * increment
    return pp, landed, selling, final, increment
