import gevent.monkey
gevent.monkey.patch_all()

import os
from datetime import datetime
from flask import Flask, render_template, url_for, redirect, flash, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from alembic import op
import sqlalchemy as sa
from functools import wraps
import time
from flask_socketio import SocketIO, send, emit
from flask.cli import AppGroup
import logging
from flask import jsonify
from flask_wtf.csrf import generate_csrf

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s]: %(message)s')
app.config['SECRET_KEY'] = 'your_secret_key_here'
# Initialize SocketIO with your Flask app
socketio = SocketIO(app, async_mode='gevent', logger=True, engineio_logger=True)

if os.environ.get('FLASK_ENV') == 'production':
    user = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASSWORD')
    host = os.environ.get('DB_HOST')
    db_name = os.environ.get('DB_NAME')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{user}:{password}@{host}/{db_name}'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///users.db')

class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.is_admin = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

def create_tables():
    with app.app_context():
        db.create_all()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False, default='member')
    notes = db.relationship('Note', backref='author', lazy=True)
    groups = db.relationship('Group', backref='owner', lazy=True)
    members = db.relationship('Member', backref='user', lazy=True)

    def __init__(self, name, email, password, role='member'):
        self.name = name
        self.email = email
        self.password = password
        self.role = role

    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_id(self):
        return str(self.id)

class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=True)

class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.relationship('Note', backref='group', lazy=True)

class Member(UserMixin, db.Model):
    __tablename__ = 'members'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    notes = db.relationship('Note', backref='member', lazy=True)

    def __repr__(self):
        return f"Member('{self.name}', '{self.email}')"
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_id(self):
        return f"member_{str(self.id)}"

def upgrade():
    op.add_column('members', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='False'))

def downgrade():
    op.drop_column('members', 'is_admin')

@socketio.on('connect')
def test_connect():
    print("Client connected via WebSocket")
    emit('note_update', {'data': 'Connected'})

@app.route('/update_note', methods=['POST'])
@login_required
def update_note():
    note_id = request.form['note_id']
    note_content = request.form['note_content']
    
    # Update the note in the database
    note = Note.query.get(note_id)
    if note:
        note.content = note_content
        db.session.commit()

        # Emit the "note_update" event with the updated data
        socketio.emit('note_update', {'note_id': note_id, 'note_content': note_content})

    return redirect(url_for('dashboard'))


@socketio.on('some_event')
def handle_some_event(data):
    # Handle the event and broadcast the updated data to all connected clients
    socketio.emit('update_notes', updated_data)


@login_manager.user_loader
def load_user(user_id):
    if user_id.startswith("member_"):
        member_id = int(user_id.split("_")[1])
        return Member.query.get(member_id)
    else:
        return User.query.get(int(user_id))
    
@login_manager.unauthorized_handler
def unauthorized():
    flash("Please log in to access this page.", "danger")
    return redirect(url_for('login'))

@app.route('/')
def home():
    return redirect(url_for('login'))

def create_uncategorized_group(user_id):
    uncategorized_group = Group.query.filter_by(user_id=user_id, name="Uncategorized").first()
    if not uncategorized_group:
        uncategorized_group = Group(name="Uncategorized", user_id=user_id)
        db.session.add(uncategorized_group)
        db.session.commit()
    return uncategorized_group


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user:
            flash('Email address already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(name=name, email=email, password=hashed_password, role='admin')
        db.session.add(new_user)
        db.session.commit()

        # Create the Uncategorized group after registering the new admin
        create_uncategorized_group(new_user.id)

        flash('Registration successful, please log in')

        # Log out the current user before redirecting to the login page
        logout_user()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user is None:
            member = Member.query.filter_by(email=email).first()
            if member is None:
                flash('Login Unsuccessful. Please check your email and password', 'danger')
                return redirect(url_for('login'))
            elif member.check_password(password):
                print("Logging in as Member:", member)
                login_user(member)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        elif user.check_password(password):
            print("Logging in as User:", user)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check your email and password', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if isinstance(current_user, User):
        user_id = current_user.id
        members = current_user.members
    else:
        user_id = current_user.user.id
        members = Member.query.filter_by(user_id=user_id).all()

    if request.method == 'POST':
        note_content = request.form.get('content')
        group_id = request.form.get('group_id')

        if group_id == "":
            uncategorized_group = Group.query.filter_by(user_id=user_id, name="Uncategorized").first()
            group_id = uncategorized_group.id

        if isinstance(current_user, Member):
            member_id = current_user.id
            note_user_id = current_user.user_id
        else:
            member_id = current_user.members[0].id
            note_user_id = current_user.id

        new_note = Note(content=note_content, user_id=note_user_id, group_id=group_id, member_id=member_id)
        db.session.add(new_note)
        db.session.commit()
        flash('Note added successfully')
        socketio.emit('new_note', {
            'note_id': new_note.id,
            'note_content': new_note.content,
            'group_id': new_note.group_id,
            'member_name': new_note.member.name if new_note.member else 'Unknown',
            'date_created': new_note.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            'is_new': True
        }, namespace='/')
        logging.info(f"Emitted new_note event for note id {new_note.id} in namespace /")
         
        return redirect(url_for('dashboard'))

    if isinstance(current_user, User):
        members = current_user.members
    else:
        members = Member.query.filter_by(user_id=current_user.user.id).all()

    if not members:
        new_member = Member(name=current_user.name, email=current_user.email, password=current_user.password, user_id=current_user.id, is_admin=1)
        db.session.add(new_member)
        db.session.commit()
        members = [new_member]

    if isinstance(current_user, User):
        user_id = current_user.id
        member_user_ids = [member.user_id for member in members]
    else:
        user_id = current_user.user.id
        member_user_ids = []

    visible_user_ids = [user_id] + member_user_ids
    groups = Group.query.filter(Group.user_id.in_(visible_user_ids)).order_by(Group.name.asc()).all()

    # Check if "Uncategorized" group is in the groups list, if not add it
    uncategorized_group = None
    for group in groups:
        if group.name == "Uncategorized":
            uncategorized_group = group
            break

    if not uncategorized_group:
        uncategorized_group = Group(name="Uncategorized", user_id=user_id)
        db.session.add(uncategorized_group)
        db.session.commit()
        groups.append(uncategorized_group)

    group_ids = [group.id for group in groups]
    #notes = Note.query.filter((Note.group_id.in_(group_ids)) | (Note.group_id == None)).order_by(Note.date_created.desc()).all()
    notes = Note.query.filter((Note.group_id.in_(group_ids)) | (Note.group_id.is_(None))).order_by(Note.date_created.desc()).all()

    csrf_token = generate_csrf()
    return render_template('dashboard.html', notes=notes, groups=groups, members=members, csrf_token=csrf_token)
    
@socketio.on('new_note', namespace='/')
def test_new_note_event(data):
    logging.info(f"Received new_note event on the server: {data}")


@app.route('/groups', methods=['GET', 'POST'])
@login_required
def groups():
    if request.method == 'POST':
        group_name = request.form['group_name']

        if isinstance(current_user, User):
            creator_id = current_user.id
        else:
            creator_id = current_user.user.id

        new_group = Group(name=group_name, user_id=creator_id)
        db.session.add(new_group)
        db.session.commit()
        flash('Group added successfully')
         # Emit the new_group event
        socketio.emit('new_group', {'group_id': new_group.id, 'group_name': new_group.name})
        return redirect(url_for('groups'))

    if isinstance(current_user, User):
        user_id = current_user.id
        members = current_user.members
    else:
        user_id = current_user.user.id
        members = Member.query.filter_by(user_id=user_id).all()

    member_user_ids = [member.user_id for member in members]
    visible_user_ids = [user_id] + member_user_ids
    groups = Group.query.filter(Group.user_id.in_(visible_user_ids)).order_by(Group.name.asc()).all()

    # Check if "Uncategorized" group is in the groups list, if not add it
    uncategorized_group = None
    for group in groups:
        if group.name == "Uncategorized":
            uncategorized_group = group
            break

    if not uncategorized_group:
        uncategorized_group = Group(name="Uncategorized", user_id=user_id)
        db.session.add(uncategorized_group)
        db.session.commit()
        groups.append(uncategorized_group)

    return render_template('groups.html', groups=groups)


@app.route('/members', methods=['GET', 'POST'])
@login_required
def members():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='sha256')

        if len(current_user.members) >= 5:
            flash("You can only add up to 5 members.")
            return redirect(url_for('members'))

        new_member = Member(name=name, email=email, password=hashed_password, user_id=current_user.id)
        try:
            db.session.add(new_member)
            db.session.commit()
            flash('Member added successfully.')
        except IntegrityError:
            db.session.rollback()
            flash('This email address is already being used. Please use a different email address.', 'error')
        return redirect(url_for('members'))

    if isinstance(current_user, User):
        # The current user is an admin
        members = current_user.members
        return render_template('members.html', members=members, admin=True)
    else:
        # The current user is a member
        members = Member.query.filter_by(user_id=current_user.user.id).all()
        return render_template('members.html', members=members, admin=False)
    
@app.route('/view_members', methods=['GET'])
@login_required
def view_members():
    if isinstance(current_user, User):
        members = current_user.members
    else:
        members = Member.query.filter_by(user_id=current_user.user.id).all()

    return render_template('view_members.html', members=members)

@app.route('/add_member', methods=['POST'])
@login_required
def add_member():
    if len(current_user.members) >= 5:
        flash('You can only add up to 5 members.')
        return redirect(url_for('dashboard'))

    member_name = request.form.get('member_name') # Add this line to get the member's name from the form
    if not member_name:
        flash('Please enter a name for the new member.')
        return redirect(url_for('dashboard'))
    member_email = request.form.get('member_email')
    member_password = request.form.get('password')
    
    existing_member = Member.query.filter_by(email=member_email).first()
    if existing_member:
        flash('This email is already registered as a member.')
        return redirect(url_for('dashboard'))

    new_member = Member(name=member_name, email=member_email, password=member_password, user_id=current_user.id) # Add the member's name to the constructor
    db.session.add(new_member)
    db.session.commit()
    flash('Member added successfully.')
    return redirect(url_for('dashboard'))

@app.route('/delete-member/<int:user_id>/<int:member_id>', methods=['POST'])
@login_required
def delete_member(user_id, member_id):
    if current_user.role == "admin":
        member = Member.query.get(member_id)
        if member.is_admin:
            flash('You cannot delete an admin user!')
        else:
            db.session.delete(member)
            db.session.commit()
            flash('Member deleted successfully')
    else:
        flash('You are not authorized to delete users!')
    return redirect(url_for('members', user_id=user_id))


@app.route('/delete_note/<int:note_id>', methods=['POST'])
@login_required
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    if note.user_id != current_user.id and (isinstance(current_user, Member) and note.user_id != current_user.user.id):
        abort(403)
    db.session.delete(note)
    db.session.commit()
    socketio.emit('delete_note', {'note_id': note.id})
    flash('Note deleted successfully')
    return redirect(url_for('dashboard'))


@app.route('/delete_group/<int:group_id>', methods=['GET', 'POST'])
@login_required
def delete_group(group_id):
    if not current_user.role == 'admin':
        abort(403)

    group = Group.query.get_or_404(group_id)

    if request.method == 'POST':
        if request.form.get('confirm') == 'yes':
            notes = Note.query.filter_by(group_id=group_id).all()

            if notes:
                flash('Cannot delete group, please delete notes assigned to this group first', 'error')
            else:
                db.session.delete(group)
                db.session.commit()
                flash('Group deleted successfully')

                # Emit group deleted event
                socketio.emit('group_deleted', {'group_id': group.id})
                logging.info(f"Emitted group_deleted event for group id {group.id}")

            return redirect(url_for('groups'))

    return render_template('delete_group.html', group=group)

@app.route('/eink-login', methods=['GET', 'POST'])
def eink_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user is None:
            member = Member.query.filter_by(email=email).first()
            if member is None:
                flash('Login Unsuccessful. Please check your email and password', 'danger')
                return redirect(url_for('eink_login'))
            elif member.check_password(password):
                print("Logging in as Member:", member)
                login_user(member)
                return redirect(url_for('eink'))
        elif user.check_password(password):
            print("Logging in as User:", user)
            login_user(user)
            return redirect(url_for('eink'))
        else:
            flash('Login Unsuccessful. Please check your email and password', 'danger')

    return render_template('eink_login.html')

@app.route('/eink')
@login_required
def eink():
    # Fetch the members associated with the current user
    if isinstance(current_user, User):
        members = current_user.members
    else:
        members = Member.query.filter_by(user_id=current_user.user.id).all()

    # Get the list of user IDs for which the current user is a member or admin
    user_id = current_user.id if isinstance(current_user, User) else current_user.user.id
    member_user_ids = [member.user_id for member in members]

    visible_user_ids = [user_id] + member_user_ids
    groups = Group.query.filter(Group.user_id.in_(visible_user_ids)).order_by(Group.name.asc()).all()

    # Render the eink.html template and pass the groups to it
    return render_template('eink.html', groups=groups)

if __name__ == "__main__":
    create_tables()
    socketio.run(app, host="0.0.0.0", port=5000)

