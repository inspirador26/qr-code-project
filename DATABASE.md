# Database Design

Merchant

↓

Offer

↓

Coupon

↓

Wallet Object

↓

Redeemed

---

Relationships

Merchant

1 -----> Many Offers

Offer

1 -----> Many Coupons

Coupon

1 -----> One Wallet Object

Merchant

1 -----> One Wallet OfferClass

---

Business Rules

QR codes never contain coupon IDs.

QR codes reference Offers.

Coupon IDs are generated after a scan.

Coupons may only be redeemed once.

OfferClasses are merchant templates.

OfferObjects represent individual coupons.

Database is the source of truth.

APIs never trust client state.

---

Future Schema

offers

max_issued

max_redemptions

issued_count

redeemed_count

This allows coupon issuance limits and redemption limits to be managed independently.