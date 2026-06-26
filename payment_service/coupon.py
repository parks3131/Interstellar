def apply_coupon(cart_total: float, coupon_code: str) -> float:
    coupons = {"SAVE10": 0.10, "SAVE20": 0.20}
    discount = coupons.get(coupon_code, 0)
    return cart_total * (1 - discount)
