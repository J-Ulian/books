import os, requests

from flask import Flask, request, session, redirect, render_template, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():

    try:
        if session["user_id"]:
            return redirect("/search")
    except:
        return redirect("/login")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user id
    session.clear()

    # User reached route via POST
    if request.method == "POST":
        
        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)
        
        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                           {"username": request.form.get("username")}).fetchall()

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        session["user_id"] = rows[0]["id"]

        return redirect("/")        


    elif request.method == "GET":
        return render_template("login.html")
    else:
        return apology("something went terribly wrong")


@app.route("/logout")
def logout():
    """Log user out"""

    session.clear()

    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()

    # User reached route via GET
    if request.method == "GET":
        return render_template("register.html")

    # User reached route via POST
    if request.method == "POST":
        # Make sure username is unique
        name = request.form.get("username")
        if db.execute("SELECT * FROM users where username = :username", {"username": name}).rowcount == 1:
            return apology("username is already taken")
        elif not request.form.get("username"):
            return apology("must provide username", 403)
        elif not request.form.get("password"):
            return apology("must provide password", 403)
        elif not request.form.get("passwordcontrol"):
            return apology("must confirm password", 403)
        elif request.form.get("password") != request.form.get("passwordcontrol"):
            return apology("must match password", 403)
        db.execute ("INSERT INTO users (username, hash) VALUES (:name, :hash)",
                {"name": name, "hash": generate_password_hash(request.form.get("password"))})
        db.commit()
        return render_template("registred.html")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    # User reached route via GET
    if request.method == "GET":
        return render_template("search.html")

    # User reached route via POST(regular expressions)
    if request.method == "POST":
        if not request.form.get("isbn") and not request.form.get("title") and not request.form.get("author"):
            return apology("must provide something", 403)
        elif request.form.get("isbn") and not request.form.get("title") and not request.form.get("author"):           
            books = db.execute("SELECT * FROM books WHERE isbn LIKE :isbn",
                                {"isbn":"%" + request.form.get("isbn") + "%"}).fetchall()
            if len(books) < 1:
                return apology("incorrect isbn")
            else:
                return render_template("searchresult.html", books = books)
            
        elif request.form.get("title") and not request.form.get("isbn") and not request.form.get("author"):
            books = db.execute("SELECT * FROM books WHERE LOWER (title) LIKE LOWER (:title)",
                                {"title":"%" + request.form.get("title") + "%"}).fetchall()
            if len(books) < 1:
                return apology("incorrect title")
            else:
                return render_template("searchresult.html", books = books)
            
        elif request.form.get("author") and not request.form.get("title") and not request.form.get("isbn"):
            books = db.execute("SELECT * FROM books WHERE LOWER (author) LIKE LOWER (:author)",
                                {"author":"%" + request.form.get("author") + "%"}).fetchall()
            if len(books) < 1:
                return apology("incorrect author")
            else:
                return render_template("searchresult.html", books = books)
            
        else:
            return apology("must provide only isbn or title or author")


@app.route("/search/<int:book_id>", methods=["GET", "POST"])
def book(book_id):
    """List details about a  book."""
    book = db.execute("SELECT * FROM books WHERE book_id = :book_id", {"book_id": book_id}).fetchone()
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).fetchall()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "c9HGXkvFeHw1DG0wSLeQ", "isbns": book.isbn})
    data = res.json()    
    rate_num = data["books"][0]["work_ratings_count"]    
    rate_avg = data["books"][0]["average_rating"]
    
    if request.method == "GET":
        return render_template("book.html", book=book, reviews=reviews, rate_num=rate_num, rate_avg=rate_avg)
    if request.method == "POST":
        if not request.form.get("review") or not request.form.get("rating"):
            return apology("must submit review and rating", 403)
        db.execute ("INSERT INTO reviews (review, book_id, user_id, rating) VALUES (:review, :book_id, :user_id, :rating)",
                {"review": request.form.get("review"), "book_id": book_id, "user_id": session["user_id"], "rating": request.form.get("rating")})
        db.commit()
        reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book_id}).fetchall()
        return render_template("book.html", book=book, reviews=reviews, rate_num=rate_num, rate_avg=rate_avg)

@app.route("/api/<isbn>")
def book_api(isbn):
    """Return details about a book."""

    # Make sure book exists.
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
    if book is None:
        return jsonify({"error": "Invalid ISBN"}), 404

    # Get rating information.
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "c9HGXkvFeHw1DG0wSLeQ", "isbns": book.isbn})
    data = res.json()    
    rate_num = data["books"][0]["work_ratings_count"]    
    rate_avg = data["books"][0]["average_rating"]
    
    return jsonify({
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": isbn,
        "review_count": rate_num,
        "average_score": rate_avg
    })

    

