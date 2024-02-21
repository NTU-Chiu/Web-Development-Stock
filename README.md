# 網站製作：建立與登入帳號、查詢股價、買賣股票
This web using flask to setup a dynamic web program. The functions are buying, selling, searching stocks.
![finance_video](/finance_video.gif)

## Details
* Files: <br>
`app.py` : <br>
import `finance.db` and `helpers.py` and render html templates via Flask. <br><br>
`templates\` : <br>
contains all html templates  <br>
register, quote, buy, sell, history, etc. <br><br>
`helpers.py` : <br>
apology function, loop up stock price via Yahoo finance API, etc. <br><br>

* This work is based on the CS50 Week 9 probelm set:<br>
  https://cs50.harvard.edu/x/2024/psets/9/finance/
