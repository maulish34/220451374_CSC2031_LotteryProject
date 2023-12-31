from datetime import datetime
import rsa
import pyotp
from flask import request
import bcrypt
from app import db, app
from flask_login import UserMixin, current_user
from cryptography.fernet import Fernet
import pickle


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # User authentication information.
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    pin_key = db.Column(db.String(32), nullable=False, default=pyotp.random_base32())

    # User information
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False, default="user")
    birthdate = db.Column(db.String(100), nullable=False)
    postcode = db.Column(db.String(100), nullable=False)
    registered_on = db.Column(db.DateTime(), nullable=False)
    current_login = db.Column(db.DateTime(), nullable=True)
    last_login = db.Column(db.DateTime(), nullable=True)
    current_ip = db.Column(db.String(100), nullable=True)
    last_ip = db.Column(db.String(100), nullable=True)
    total_logins = db.Column(db.String(100), nullable=False, default="0")
    draw_key = db.Column(db.BLOB, nullable=False, default=Fernet.generate_key())

    # generate keys for asymmetric encryption
    publicKey, privateKey = rsa.newkeys(512)
    private_key = db.Column(db.BLOB, nullable=False, default=pickle.dumps(privateKey))
    public_key = db.Column(db.BLOB, nullable=False, default=pickle.dumps(publicKey))

    # Define the relationship to Draw
    draws = db.relationship("Draw")

    def __init__(
        self,
        email,
        firstname,
        lastname,
        birthdate,
        phone,
        postcode,
        password,
        total_logins,
        role,
    ):
        self.email = email
        self.firstname = firstname
        self.lastname = lastname
        self.birthdate = birthdate
        self.phone = phone
        self.postcode = postcode
        self.password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        self.registered_on = datetime.now()
        self.current_login = None
        self.last_login = None
        self.current_ip = None
        self.last_ip = None
        self.total_logins = total_logins
        self.role = role

    def get_2fa_uri(self):
        return str(
            pyotp.totp.TOTP(self.pin_key).provisioning_uri(
                name=self.email, issuer_name="CSC2031 Lottery App"
            )
        )

    def verify_password(self, password):
        return bcrypt.checkpw(password.encode("utf-8"), self.password)

    def verify_pin(self, pin):
        return pyotp.TOTP(self.pin_key).verify(pin)

    def verify_postcode(self, postcode):
        return self.postcode == postcode


class Draw(db.Model):
    __tablename__ = "draws"

    id = db.Column(db.Integer, primary_key=True)

    # ID of user who submitted draw
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    # 6 draw numbers submitted
    numbers = db.Column(db.String(100), nullable=False)

    # Draw has already been played (can only play draw once)
    been_played = db.Column(db.BOOLEAN, nullable=False, default=False)

    # Draw matches with master draw created by admin (True = draw is a winner)
    matches_master = db.Column(db.BOOLEAN, nullable=False, default=False)

    # True = draw is master draw created by admin. User draws are matched to master draw
    master_draw = db.Column(db.BOOLEAN, nullable=False)

    # Lottery round that draw is used
    lottery_round = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, user_id, numbers, master_draw, lottery_round, draw_key):
        self.user_id = user_id

        # While using symmetric encryption
        # self.numbers = encrypt(numbers, draw_key)

        # While using asymmetric encryption
        self.numbers = rsa.encrypt(
            numbers.encode("utf-8"), pickle.loads(current_user.public_key)
        )

        self.been_played = False
        self.matches_master = False
        self.master_draw = master_draw
        self.lottery_round = lottery_round

    def view_draw(self, private_key):
        private_key = pickle.loads(private_key)
        return rsa.decrypt(self.numbers, private_key).decode("utf-8")


def encrypt(data, draw_key):
    return Fernet(draw_key).encrypt(bytes(data, "utf-8"))


def decrypt(data, draw_key):
    return Fernet(draw_key).decrypt(data).decode("utf-8")


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(
            email="admin@email.com",
            password="Admin1!",
            firstname="Alice",
            lastname="Jones",
            birthdate="11/11/2000",
            phone="0191-123-4567",
            postcode="NE1 4SP",
            total_logins="0",
            role="admin",
        )

        db.session.add(admin)
        db.session.commit()
