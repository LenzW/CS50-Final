from flask import Flask, render_template, url_for, redirect, request, session, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, func
from sqlalchemy.pool import NullPool
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import joinedload

engine = create_engine('sqlite:///../final/User.db', echo=True, poolclass=NullPool)

app = Flask(__name__, static_folder="static")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../final/User.db'
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    liked_quotes = db.relationship('LikedQuote', backref='user', lazy=True)

    def __init__(self, email, password):
        self.email = email
        self.password = password

    def __repr__(self):
        return f"<User {self.email}>"

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    liked_by_users = db.relationship('LikedQuote', backref='quote', lazy=True)

    def __init__(self, content):
        self.content = content

    def __repr__(self):
        return f"<Quote {self.id}>"

class LikedQuote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    quote_id = db.Column(db.Integer, db.ForeignKey(Quote.id), nullable=False)

    def __init__(self, user_id, quote_id):
        self.user_id = user_id
        self.quote_id = quote_id

    def __repr__(self):
        return f"<LikedQuote {self.id}>"
    
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

def get_random_quote():
    quote = Quote.query.order_by(func.random()).first()
    return quote if quote else None


@app.route("/index")
def index():
    quote = get_random_quote()
    return render_template("index.html", quote=quote)

@app.route("/home", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        user_id = session.get("user_id")
        if not user_id:
            flash("Bitte melde dich an, um ein Zitat zu liken.")
            return redirect(url_for("login"))

        content_id = request.form["content_id"]

        quote = Quote.query.get(content_id)
        if not quote:
            flash("Zitat nicht gefunden.")
            return redirect(url_for("home"))

        liked_quote = LikedQuote.query.filter_by(user_id=user_id, quote_id=content_id).first()
        if liked_quote:
            db.session.delete(liked_quote)
            flash("Zitat erfolgreich entfernt.")
        else:
            new_liked_quote = LikedQuote(user_id=user_id, quote_id=content_id)
            db.session.add(new_liked_quote)
            flash("Zitat erfolgreich geliked.")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Beim Liken des Zitats ist ein Fehler aufgetreten.")
            print(e)

        return redirect(url_for("home"))
    else:
        quote = Quote.query.options(joinedload(Quote.liked_by_users)).order_by(func.random()).first()
        user_id = session.get("user_id", None)
        liked_quote = LikedQuote.query.filter_by(user_id=user_id, quote_id=quote.id).first() if user_id else None

        if quote:
            if user_id:
                liked_quote = LikedQuote.query.filter_by(user_id=user_id, quote_id=quote.id).first()
            return render_template("home.html", quote=quote, liked_quote=liked_quote)
        else:
            flash("No quotes found.")
            return redirect(url_for("index"))


@app.route("/redirect_home")
def redirect_home():
    return redirect(url_for('home'))


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        password_repeat = request.form["password_repeat"]

        if password != password_repeat:
            flash("Passwords do not match. Please try again.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        try:
            new_user = User(email=email, password=password_hash)
            db.session.add(new_user)
            db.session.commit()
        except:
            flash("Email already exists")

        session["user_id"] = new_user.id
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login successful.")
            return redirect(url_for("home"))
    else:
        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")


@app.route("/liked")
def liked():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in to view liked quotes.")
        return redirect(url_for("login"))
    liked_quotes = LikedQuote.query.filter_by(user_id=user_id).all()
    return render_template("liked.html", liked_quotes=liked_quotes)


@app.route("/logout", methods=["POST", "GET"])
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))


@app.route("/agb", methods=["POST", "GET"])
def agb():
    return render_template("agb.html")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
