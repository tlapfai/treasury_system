# Treasury System

* Abstract class
* Cashflows
* PL report
* VaR

IRTermStructure
-add ccy
-limit its attr. rates
-ModelMultipleChoiceField

https://www.w3schools.com/css/css3_flexbox.asp

<!DOCTYPE html>
<html lang="en">
    <head>
        <title>Screen Size</title>
        <style>
            #container {
                display: flex;
                flex-wrap: wrap;
            }

            #container > div {
                background-color: green;
                font-size: 20px;
                margin: 20px;
                padding: 20px;
                width: 200px;
            }
        </style>
    </head>
    <body>
        <div id="container">
            <div>Some text 1!</div>
            <div>Some text 2!</div>
            <div>Some text 3!</div>
            <div>Some text 4!</div>
            <div>Some text 5!</div>
            <div>Some text 6!</div>
            <div>Some text 7!</div>
            <div>Some text 8!</div>
            <div>Some text 9!</div>
            <div>Some text 10!</div>
            <div>Some text 11!</div>
            <div>Some text 12!</div>
        </div>
    </body>
</html>





import QuantLib as ql
import numpy as np
import pandas as pd

rev_date = ql.Date(17,11,2021)
ql.Settings.instance().evaluationDate = rev_date

ty = ql.VanillaSwap.Receiver
calendar = ql.UnitedStates()
effective_date = ql.Date(19,11,2021)
swap_tenor = ql.Period('2y')
maturity = calendar.advance(effective_date, swap_tenor)

#----trade end--------

#----USD 42 ois START-----
yts_handle_ois = ql.RelinkableYieldTermStructureHandle()

cv_df = pd.read_csv('usdoiscurve.csv' ,index_col = 'Term')
cv = cv_df.drop(columns=['Shift','Shifted Rate','Zero Rate','Discount'])
cv['Market Rate'] = cv['Market Rate'] * 0.01

helpers = ql.RateHelperVector()
index = ql.OvernightIndex('USD EFFR', 1, ql.USDCurrency(), ql.UnitedStates(), ql.Actual365Fixed(), yts_handle_ois)
simple_quote = []

for term, data in cv.iterrows():
    term = term.replace(' ','')
    if term == '1D':
        simple_quote.append( ql.SimpleQuote(float(data['Market Rate'])) )
        helpers.append( ql.DepositRateHelper(ql.QuoteHandle(simple_quote[-1]), index) )
        #index.addFixing(rev_date, float(data['Market Rate']))
    else:
        simple_quote.append( ql.SimpleQuote(float(data['Market Rate'])) )
        helpers.append( ql.OISRateHelper(2, ql.Period(term), ql.QuoteHandle(simple_quote[-1]), index) )

#print('USD OIS')
#[print(x.value()) for x in simple_quote]

ois_curve = ql.PiecewiseLogLinearDiscount(rev_date, helpers, ql.Actual365Fixed())

yts_handle_ois.linkTo(ois_curve)
#----USD 42 ois END-------

#----USD 23 START-----
yts_handle_usd = ql.RelinkableYieldTermStructureHandle()

cv_df = pd.read_csv('curve.csv' ,index_col = 'Term')
cv = cv_df.drop(columns=['Shift','Shifted Rate','Zero Rate','Discount'])
cv['Market Rate'] = cv['Market Rate'] * 0.01

helpers2 = ql.RateHelperVector()
index_libor = ql.USDLibor(ql.Period('3m'), yts_handle_usd)
simple_quote_swap = []

for term, data in cv.iterrows():
    term = term.replace(' ','')
    if term == '3MO':
        simple_quote_swap.append( ql.SimpleQuote(float(data['Market Rate'])) )
        helpers2.append( ql.DepositRateHelper(ql.QuoteHandle(simple_quote_swap[-1]), index_libor) )
    elif term[:2] == 'ED':
        simple_quote_swap.append( ql.SimpleQuote((1.0-float(data['Market Rate']))*100) )
        helpers2.append( ql.FuturesRateHelper(ql.QuoteHandle(simple_quote_swap[-1]), ql.IMM.date(term[-2:]), index_libor) )
    elif term[-2:] == 'YR':
        simple_quote_swap.append( ql.SimpleQuote(float(data['Market Rate'])) ) 
        swapIndex = ql.UsdLiborSwapIsdaFixAm(ql.Period(term.replace('YR','y')))
        helpers2.append( ql.SwapRateHelper(ql.QuoteHandle(simple_quote_swap[-1]), 
                                            swapIndex, 
                                            ql.QuoteHandle(), 
                                            ql.Period(), 
                                            yts_handle_ois
                                            )
                        )
#print('USD LIBOR')
#[print(x.value()) for x in simple_quote_swap]

usd_curve = ql.PiecewiseLogLinearDiscount(rev_date, helpers2, ql.Actual365Fixed())

yts_handle_usd.linkTo(usd_curve)
#----USD 23 END-------


engine = ql.DiscountingSwapEngine(yts_handle_ois)

n = 1e9
fixedSchedule = ql.MakeSchedule(effective_date, maturity, ql.Period('6M'), calendar=ql.UnitedStates(), rule=ql.DateGeneration.Forward)
floatSchedule = ql.MakeSchedule(effective_date, maturity, ql.Period('3M'), calendar=ql.UnitedStates(), rule=ql.DateGeneration.Forward)

fixed_rate = 0.32527*0.01
my_swap = ql.VanillaSwap(ty, n, fixedSchedule, fixed_rate, ql.Thirty360(), floatSchedule, index_libor, 0, ql.Actual360())
my_swap.setPricingEngine(engine)

fairRate = my_swap.fairRate()
npv = my_swap.NPV()

with open("result.txt", "w") as f:
    f.write(f"Fair swap rate: {fairRate:.4%}\n")
    f.write(f"Swap NPV: {npv:,.2f}\n")
    
    for i in range(2):
        f.write(f"leg {str(i)}\n")
        for cf in list(my_swap.leg(i)):
            f.write(f"{cf.date().ISO()},{cf.amount():.2f},{ois_curve.discount(cf.date()):.16f}\n")

    f.write("===========BPV============\n")
    for i in range(len(simple_quote_swap)):
        simple_quote_swap[i].setValue(simple_quote_swap[i].value() + 0.0001)
        f.write(f"{cv.index[i]} {my_swap.NPV() - npv:,.2f}\n")
        simple_quote_swap[i].setValue(simple_quote_swap[i].value() - 0.0001)
