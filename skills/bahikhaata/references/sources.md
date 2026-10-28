# Sources and file formats

All raw files for a period go in `expense-log/raw/<start>_<end>/`. Dates are ISO (`2026-10-14` or `2026-10-14T09:12:00Z`).

## fold.csv / bank.csv: bank and card debits
```
id,date,account_id,source,merchant_name,narration,amount,effective_amount,category,excluded_from_cash_flow
```
- Only `date`, `narration` and `amount` are required. `merchant_name` and `category` help classification.
- Set `excluded_from_cash_flow` to `True` for self-transfers.
- UPI narrations like `UPI/P2M/<ref>/<PAYEE>/...` are parsed for the payee name.
- **Bank CSV fallback:** convert the user's statement (HDFC, ICICI, Axis, SBI exports all work) into these columns. Use debits only, with a positive amount. Leave the rest blank.

## emails.csv: receipts and card alerts from Gmail
```
email_id,date,sender,kind,merchant,order_id,items,amount,delivery_address,payment_method
```
- `kind` is one of `food`, `instamart`, `amazon`, `grocery`, `other` or `bank_alert`.
- `items` uses `2 X Item; Item x1 120`. For a mixed order, write each item with its price as `Item x1 <price>`, so a single shared item can be split out.
- `delivery_address` is the address from the receipt, if it has one. The build compares it with `home.keywords`.
- `bank_alert` rows are card-spend alerts. `payment_method` names the card (e.g. `Axis CC XX1234`).

| Source | What it gives | Blind spots |
|---|---|---|
| Fold (Fold Plus) | every bank/card debit | not what it was for; wallet top-ups are one lump |
| Bank CSV | the same, but manually, monthly | as above, plus it's only as fresh as the last export |
| Gmail | what was ordered; Swiggy/Instamart addresses | Zomato has no address; some merchants send no email |
| Instamart connector | addresses | roughly the last 15 days only |
| Swiggy connector | recent food orders | the 15 most recent only |
| Amazon "Request your data" export → `expense-log/raw/amazon/Order History.csv` | item names for card charges | no address; takes days to arrive |
| UPI Lite, cash | nothing | tell Claude directly |
