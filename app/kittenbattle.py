import os

from datetime import datetime, time
from functools import wraps
from flask import *
from flask.ext.sqlalchemy import *
from sqlalchemy.sql import func
from sqlalchemy.exc import *
from werkzeug import generate_password_hash, check_password_hash

from PIL import Image, ImageOps
from slugify import slugify
from forms import *
from flask.ext.gravatar import Gravatar

app = Flask(__name__)
app.config.from_object('config')

db = SQLAlchemy(app)
gravatar = Gravatar(app, size=100)

@app.template_filter()
def timesince(dt, default="just now"):
    """
    Returns string representing "time since"
    """
    
    now = datetime.utcnow()
    diff = now - dt
    
    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s ago" % (period, singular if period == 1 else plural)

    return default

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(20))
    created = db.Column(db.DateTime)
    kittens = db.relationship('Kitten', backref='user', lazy='joined')

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password = generate_password_hash(password)
        self.created = datetime.utcnow()
        
    def check_password(self, password):
        return check_password_hash(self.password, password)        

    def __repr__(self):
        return '<User %r>' % self.username
    
class Kitten(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    slug = db.Column(db.String(50))
    created = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Float)
    won = db.Column(db.SmallInteger)
    lost = db.Column(db.SmallInteger)
    
    def __init__(self, name, user_id):
        self.name = name
        self.slug = slugify(self.name)
        self.user_id = user_id
        self.created = datetime.utcnow()
        self.rating = 1000
        self.won = 0
        self.lost = 0
        
    @property        
    def battles(self):
        """ Returns number of battles fought """
        return (self.won + self.lost)

    @property        
    def win_percentage(self):
        """ Returns winning percentage """
        try:
            return round((float(self.won) / float(self.battles)) * 100, 1)
        except ZeroDivisionError:
            return 0 

    @property        
    def lost_percentage(self):
        """ Returns losing percentage """
        try:
            return round((float(self.lost) / float(self.battles)) * 100, 1)
        except ZeroDivisionError:
            return 0 

    def update_rating(self, score, opponent):
        if score:
            self.won += 1
        else:
            self.lost += 1
        K0 = 15
        Q0 = 10 ** (float(self.rating) / 400)
        Q1 = 10 ** (float(opponent.rating) / 400)
        E0 = Q0 / (Q0 + Q1)
        self.rating += (K0 * (score - E0))
        
    @classmethod        
    def random(cls):
        return Kitten.query.order_by(func.random()).first()
    
    @classmethod        
    def byId(cls, kitten_id):
        return Kitten.query.get_or_404(kitten_id)
        


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.before_request
def before_request():
    try:
        g.user = session['user']
    except Exception:
        g.user = None            

@app.route('/')
def index():
    print dir(request)
    print request.user_agent
    kittens = Kitten.query.order_by('rating desc').limit(12).all()
    return render_template("index.html", kittens=kittens)

@app.route('/kitten/upload', methods=['GET', 'POST'])
@login_required
def upload():
    form = Upload_Form()
    
    if form.validate_on_submit():
        img_file = form.img_file.data
    
        kitten = Kitten(form.name.data, g.user)
        db.session.add(kitten)
        db.session.commit()
        
        size = (120, 120)
        upload_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/uploads')
        image = Image.open(img_file)
        thumb = ImageOps.fit(image, size, Image.ANTIALIAS)
        thumb.save(os.path.join(upload_folder, str(kitten.id)), 'png')
        flash('Upload was succesful!', 'success')
        return redirect(url_for('view_kitten', slug=kitten.slug, kitten_id = kitten.id))
            
    return render_template('upload.html', form=form)
 
@app.route('/kitten/<string:slug>/<int:kitten_id>')
@login_required
def view_kitten(slug, kitten_id):
    kitten = Kitten.byId(kitten_id)
    return render_template("view_kitten.html", kitten=kitten)

@app.route('/fight', methods=['POST', 'GET'])
@login_required
def kitten_fight():
    if request.method == 'GET':
        kitten1 = Kitten.random()
        kitten2 = Kitten.random()
        while kitten1.id == kitten2.id:
            kitten1 = Kitten.random()
            kitten2 = Kitten.random()
        return render_template("kitten_fight.html", kitten1=kitten1, kitten2=kitten2)
    
    if request.method == 'POST':
        winner = Kitten.byId(request.form['winner'])
        loser = Kitten.byId(request.form['loser'])
        winner.update_rating(1, loser)
        loser.update_rating(0, winner)
        db.session.commit()
        return redirect(url_for('kitten_fight'))

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user is None:
            flash('Login failed', 'error')
            return redirect(url_for('index'))
        
        if user.check_password(password):
            session['user'] = user.id
            flash('You are now logged in', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed wrong pw', 'error')
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    flash('You are now logged out', 'success')
    return redirect(url_for('index'))    

@app.route('/register', methods=['GET', 'POST'])
def user_register():
    form = Signup_Form()
    if form.validate_on_submit():
        try:
            user = User(form.username.data, form.email.data, form.password.data)
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        flash('Registration was successful! Please login...', 'success')
        return redirect(url_for('index'))
    return render_template("register.html", form=form)