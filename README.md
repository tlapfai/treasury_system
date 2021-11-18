# Treasury System

* Abstract class
* Cashflows
* PL report
* VaR

* FXO -> FXOPT
* FXBAR
* FXSPOT
* FXFWD
* FXSWAP
* SWAP


IRTermStructure
-add ccy
-limit its attr. rates
-ModelMultipleChoiceField
* ql.Cashflows.npv()

https://www.w3schools.com/css/css3_flexbox.asp

combine two dict ==> dict1.update(dict2)

    yts_handle_usd = ql.RelinkableYieldTermStructureHandle()
    usd_curve = ql.PiecewiseLogLinearDiscount(rev_date, helpers2, ql.Actual365Fixed())
    yts_handle_usd.linkTo(usd_curve)
    def fun(x, y):
        return (x - y)
    comp_yts = ql.CompositeZeroYieldStructure(yts_handle_usd, yts_handle_ois, fun)
