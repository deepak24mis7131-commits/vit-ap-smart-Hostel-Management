import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-demo-secret-before-deploying")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///hostel_demo.db").replace("postgres://", "postgresql://")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_no = db.Column(db.String(20), unique=True, nullable=False)
    block = db.Column(db.String(40), nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    occupied = db.Column(db.Integer, nullable=False, default=0)

class Allocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("room.id"), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    student = db.relationship("User")
    room = db.relationship("Room")

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    details = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Open")
    student = db.relationship("User")

class MessSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    plan = db.Column(db.String(40), nullable=False)
    status = db.Column(db.String(20), default="Active")
    student = db.relationship("User")

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            user = db.session.get(User, session["user_id"])
            if not user or user.role not in roles:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator

@app.context_processor
def inject_user():
    user = db.session.get(User, session["user_id"]) if session.get("user_id") else None
    return {"current_user": user}

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 6:
            flash("Enter your name, a valid email and a password of at least 6 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password), role="student")
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = db.session.get(User, session["user_id"])
    if user.role == "admin":
        stats = {
            "students": User.query.filter_by(role="student").count(),
            "rooms": Room.query.count(),
            "pending": Allocation.query.filter_by(status="Pending").count(),
            "complaints": Complaint.query.filter_by(status="Open").count()
        }
        return render_template("admin.html", stats=stats, rooms=Room.query.order_by(Room.block, Room.room_no).all(),
                               allocations=Allocation.query.order_by(Allocation.id.desc()).all(),
                               complaints=Complaint.query.order_by(Complaint.id.desc()).all())
    if user.role == "warden":
        return render_template("warden.html",
            allocations=Allocation.query.order_by(Allocation.id.desc()).all(),
            complaints=Complaint.query.order_by(Complaint.id.desc()).all())
    allocation = Allocation.query.filter_by(student_id=user.id).order_by(Allocation.id.desc()).first()
    complaints = Complaint.query.filter_by(student_id=user.id).order_by(Complaint.id.desc()).all()
    mess = MessSubscription.query.filter_by(student_id=user.id).order_by(MessSubscription.id.desc()).first()
    rooms = Room.query.all()
    return render_template("student.html", allocation=allocation, complaints=complaints, mess=mess, rooms=rooms)

@app.route("/allocation/request", methods=["POST"])
@role_required("student")
def request_allocation():
    room = db.session.get(Room, request.form.get("room_id", type=int))
    if not room or room.occupied >= room.capacity:
        flash("That room is unavailable. Please choose another room.", "error")
    elif Allocation.query.filter_by(student_id=session["user_id"], status="Pending").first() or Allocation.query.filter_by(student_id=session["user_id"], status="Approved").first():
        flash("You already have a pending or approved allocation.", "error")
    else:
        db.session.add(Allocation(student_id=session["user_id"], room_id=room.id))
        db.session.commit()
        flash("Room request submitted to the warden.", "success")
    return redirect(url_for("dashboard"))

@app.route("/allocation/<int:allocation_id>/<action>", methods=["POST"])
@role_required("warden", "admin")
def update_allocation(allocation_id, action):
    allocation = db.session.get(Allocation, allocation_id)
    if not allocation or allocation.status != "Pending" or action not in ("approve", "reject"):
        flash("This request cannot be updated.", "error")
    elif action == "approve":
        if allocation.room.occupied >= allocation.room.capacity:
            flash("Room is full. Reject this request or select another room.", "error")
        else:
            allocation.status = "Approved"
            allocation.room.occupied += 1
            db.session.commit()
            flash("Room request approved.", "success")
    else:
        allocation.status = "Rejected"
        db.session.commit()
        flash("Room request rejected.", "success")
    return redirect(url_for("dashboard"))

@app.route("/complaint", methods=["POST"])
@role_required("student")
def add_complaint():
    subject = request.form.get("subject", "").strip()
    details = request.form.get("details", "").strip()
    if subject and details:
        db.session.add(Complaint(student_id=session["user_id"], subject=subject, details=details))
        db.session.commit()
        flash("Complaint submitted.", "success")
    else:
        flash("Please complete both complaint fields.", "error")
    return redirect(url_for("dashboard"))

@app.route("/complaint/<int:complaint_id>/<action>", methods=["POST"])
@role_required("warden", "admin")
def update_complaint(complaint_id, action):
    complaint = db.session.get(Complaint, complaint_id)
    if complaint and action in ("resolve", "reopen"):
        complaint.status = "Resolved" if action == "resolve" else "Open"
        db.session.commit()
        flash("Complaint status updated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/mess", methods=["POST"])
@role_required("student")
def subscribe_mess():
    plan = request.form.get("plan", "")
    if plan not in ("Breakfast + Lunch + Dinner", "Lunch + Dinner", "Dinner Only"):
        flash("Choose a valid mess plan.", "error")
    else:
        db.session.add(MessSubscription(student_id=session["user_id"], plan=plan))
        db.session.commit()
        flash("Mess plan saved.", "success")
    return redirect(url_for("dashboard"))

@app.route("/room/add", methods=["POST"])
@role_required("admin")
def add_room():
    room_no = request.form.get("room_no", "").strip()
    block = request.form.get("block", "").strip()
    capacity = request.form.get("capacity", type=int)
    if room_no and block and capacity and capacity > 0 and not Room.query.filter_by(room_no=room_no).first():
        db.session.add(Room(room_no=room_no, block=block, capacity=capacity))
        db.session.commit()
        flash("Room added.", "success")
    else:
        flash("Enter unique room number, block and a positive capacity.", "error")
    return redirect(url_for("dashboard"))

@app.cli.command("init-db")
def init_db():
    """Create demo tables, sample rooms and demo accounts."""
    db.create_all()
    demos = [
        ("Demo Admin", "admin@vitap.demo", "Admin@123", "admin"),
        ("Demo Warden", "warden@vitap.demo", "Warden@123", "warden"),
        ("Demo Student", "student@vitap.demo", "Student@123", "student"),
    ]
    for name, email, password, role in demos:
        if not User.query.filter_by(email=email).first():
            db.session.add(User(name=name, email=email, password_hash=generate_password_hash(password), role=role))
    if Room.query.count() == 0:
        db.session.add_all([
            Room(room_no="A-101", block="A Block", capacity=3, occupied=1),
            Room(room_no="A-102", block="A Block", capacity=2, occupied=0),
            Room(room_no="B-201", block="B Block", capacity=3, occupied=2),
            Room(room_no="B-202", block="B Block", capacity=2, occupied=0),
        ])
    db.session.commit()
    print("Demo database initialized. See README for demo credentials.")

if __name__ == "__main__":
    app.run(debug=True)
