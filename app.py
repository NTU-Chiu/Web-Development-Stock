import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    total_property_value = 0
    results_list = []

    results = (db.execute("""SELECT symbol, SUM(shares) FROM history
                     WHERE user_id = ? AND transaction_type = ? GROUP BY symbol""", session["user_id"], "buy"))

    for i in range(len(results)):
        # 股票數量=(買-賣)
        net_shares = (db.execute("""SELECT SUM(shares) FROM history
                WHERE user_id = ? AND symbol = ? AND transaction_type = ? """, session["user_id"], results[i]["symbol"], "buy"))[0]["SUM(shares)"] - \
            int(
            (db.execute("""SELECT SUM(shares) FROM history
                WHERE user_id = ? AND symbol = ? AND transaction_type = ? """, session["user_id"], results[i]["symbol"], "sell"))[0]["SUM(shares)"]
            or 0)
        # 檢查是否還有股票
        if net_shares > 0:
            temp_dict = {}
            temp_dict["symbol"] = results[i]["symbol"]
            temp_dict["price"] = (lookup(results[i]["symbol"]))["price"]
            temp_dict["shares"] = net_shares
            temp_dict["stock_value"] = temp_dict["price"] * temp_dict["shares"]

            total_property_value = total_property_value + temp_dict["stock_value"]

            # 使用usd function 轉成字串
            temp_dict["stock_value"] = usd(temp_dict["stock_value"])
            results_list.append(temp_dict)

    cash = int((db.execute("""SELECT cash FROM users
                    WHERE id = ?""", session["user_id"]))[0]["cash"] or 0)
    total_property_value = total_property_value + cash
    return render_template("index.html", results=results_list, cash=usd(cash), total_property_value=usd(total_property_value))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("must provide stock symbol", 400)
        elif not request.form.get("shares"):
            return apology("must provide the number of shares", 400)
        else:
            # print(request.form.get("symbol"), request.form.get("shares"))
            result = lookup(request.form.get("symbol"))
            if result is None:
                return apology("this stock symbol does not exist", 400)
            else:
                symbol = result["symbol"]
                price = result["price"]  # result.price AttributeError: 'dict' object has no attribute 'symbol'
                shares = request.form.get("shares")
            try:
                shares = float(request.form.get("shares"))
            except ValueError:
                return apology("must provide integer number", 400)

            if shares < 1 or int(shares) != shares:
                return apology("must provide integer number", 400)
            else:
                cash_before = (db.execute(""" SELECT cash from users WHERE id = ?
                """, session["user_id"]))[0]["cash"]
                # print(cash_before, price, shares)
                cash_after = cash_before - (price * shares)
                # 現金不足
                if cash_after < 0:
                    return apology("cash not enough", 400)
                else:
                    db.execute("""INSERT INTO history (user_id, symbol, price, shares, time, transaction_type, cash_before, cash_after)
                        VALUES (?, ?, ?, ?, DATETIME('now'), ?, ?, ?)
                        """, session["user_id"], symbol, usd(price), shares, "buy", cash_before, cash_after)
                    db.execute("""UPDATE users SET cash = ?
                                WHERE id = ?""", cash_after, session["user_id"])
                    return redirect("/")  # index.html
    else:
        return render_template("buy.html")


@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    if request.method == "POST":
        money = float(request.form.get("money"))
        cash = db.execute("""SELECT cash FROM users
                          WHERE id = ?""", session["user_id"])[0]["cash"]
        db.execute("""UPDATE users SET cash = ?
                   WHERE id = ?""", money + cash, session["user_id"])
        return redirect("/")
    else:
        return render_template("deposit.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    results = db.execute("""SELECT * FROM history
                         WHERE user_id = ?""", session["user_id"])
    return render_template("history.html", results=results)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]  # session 不太懂

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        result = lookup(request.form.get("symbol"))
        if result is None:
            return apology("this stock symbol does not exist", 400)
        else:
            result["price"] = usd(result["price"])
            return render_template("quoted.html", result=result)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        elif not request.form.get("password"):
            return apology("must provide password", 400)
        else:
            username = request.form.get("username")
            if len(db.execute("SELECT * FROM users WHERE username = ?", username)) != 0:
                return apology("user is already registered", 400)
            password = request.form.get("password")
            password_var = request.form.get("confirmation")
            if password == password_var:
                db.execute("""INSERT INTO users (username, hash)
                VALUES (?, ?)""", username, generate_password_hash(password))
                return redirect("/login")
            else:
                return apology("Password Varification Failed", 400)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        symbol = request.form.get("symbol")
        shares = float(request.form.get("shares"))
        net_shares = (db.execute("""SELECT SUM(shares) FROM history
                        WHERE user_id = ? AND symbol = ? AND transaction_type = ? """, session["user_id"], symbol, "buy"))[0]["SUM(shares)"] - \
            int(
            (db.execute("""SELECT SUM(shares) FROM history
                        WHERE user_id = ? AND symbol = ? AND transaction_type = ? """, session["user_id"], symbol, "sell"))[0]["SUM(shares)"]
            or 0)  # TypeError: unsupported operand type(s) for -: 'int' and 'NoneType' --> int(value or 0)
        if net_shares - shares < 0:
            return apology("not enought shares", 400)

        else:
            price = (lookup(symbol))["price"]
            cash_before = (db.execute(""" SELECT cash from users
                                    WHERE id = ?""", session["user_id"]))[0]["cash"]
            cash_after = cash_before + shares * price
            db.execute("""INSERT INTO history (user_id, symbol, price, shares, time, transaction_type, cash_before, cash_after)
                VALUES (?, ?, ?, ?, DATETIME('now'), ?, ?, ?)
                """, session["user_id"], symbol, usd(price), shares, "sell", cash_before, cash_after)
            db.execute("""UPDATE users SET cash = ?
                        WHERE id = ?""", cash_after, session["user_id"])
            # print(db.execute("""SELECT * FROM history WHERE user_id = ?""", session["user_id"]))
            # print(db.execute("""SELECT * FROM users WHERE id = ?""", session["user_id"]))
            return redirect("/")

    else:
        results_buy = (db.execute("""SELECT symbol, SUM(shares) FROM history
                        WHERE user_id = ? AND transaction_type = ? GROUP BY symbol""", session["user_id"], "buy"))
        results_sell = (db.execute("""SELECT symbol, SUM(shares) FROM history
                        WHERE user_id = ? AND transaction_type = ? GROUP BY symbol""", session["user_id"], "sell"))

        symbols = []
        for i in range(len(results_buy)):
            # 股票數量=(買-賣)
            net_shares = results_buy[i]["SUM(shares)"] - \
                next((this["SUM(shares)"] for this in results_sell if this["symbol"] == results_buy[i]["symbol"]), 0)
            if net_shares > 0:
                symbols.append(results_buy[i]["symbol"])
        return render_template("sell.html", symbols=symbols)
