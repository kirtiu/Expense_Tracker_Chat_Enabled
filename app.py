from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'expense_tracker_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'expenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

CATEGORIES = ['Food', 'Transport', 'Shopping', 'Health', 'Entertainment', 'Bills', 'Other']


# ── Models ──────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    expenses = db.relationship('Expense', backref='owner', lazy=True, cascade='all, delete-orphan')


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Other')
    date = db.Column(db.String(20), nullable=False)
    note = db.Column(db.String(300), default='')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


# ── Init DB & seed default user ──────────────────────────────────────────────

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@example.com').first():
        db.session.add(User(email='admin@example.com', password='password123'))
        db.session.commit()


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('signin'))


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            session['user_email'] = user.email
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('signin.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not email or not password:
            flash('All fields are required.', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
        elif password != confirm:
            flash('Passwords do not match.', 'error')
        elif User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
        else:
            user = User(email=email, password=password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            session['user_email'] = user.email
            flash('Account created successfully! Welcome.', 'success')
            return redirect(url_for('dashboard'))

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    sort_by = request.args.get('sort', 'date')
    order = request.args.get('order', 'desc')

    sort_col_map = {
        'date': Expense.date,
        'amount': Expense.amount,
        'title': Expense.title,
        'category': Expense.category,
    }
    sort_col = sort_col_map.get(sort_by, Expense.date)
    sort_expr = sort_col.desc() if order == 'desc' else sort_col.asc()

    user_expenses = Expense.query.filter_by(user_id=session['user_id'])\
        .order_by(sort_expr).all()

    total = sum(e.amount for e in user_expenses)

    current_month = datetime.now().strftime('%Y-%m')
    monthly_total = sum(e.amount for e in user_expenses if e.date.startswith(current_month))

    category_totals = {}
    for cat in CATEGORIES:
        cat_total = sum(e.amount for e in user_expenses if e.category == cat)
        if cat_total > 0:
            category_totals[cat] = cat_total

    today = datetime.now().strftime('%Y-%m-%d')

    return render_template(
        'dashboard.html',
        user=session['user_email'],
        expenses=user_expenses,
        total=total,
        monthly_total=monthly_total,
        category_totals=category_totals,
        categories=CATEGORIES,
        now=today,
        sort_by=sort_by,
        order=order
    )


@app.route('/add', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    title = request.form.get('title', '').strip()
    amount = request.form.get('amount', '').strip()
    category = request.form.get('category', 'Other')
    date = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
    note = request.form.get('note', '').strip()

    if not title or not amount:
        flash('Title and amount are required.', 'error')
        return redirect(url_for('dashboard'))

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash('Please enter a valid amount.', 'error')
        return redirect(url_for('dashboard'))

    expense = Expense(
        title=title,
        amount=amount,
        category=category,
        date=date,
        note=note,
        user_id=session['user_id']
    )
    db.session.add(expense)
    db.session.commit()
    flash('Expense added successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/edit/<int:expense_id>', methods=['POST'])
def edit_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
    if not expense:
        flash('Expense not found.', 'error')
        return redirect(url_for('dashboard'))

    title = request.form.get('title', '').strip()
    amount = request.form.get('amount', '').strip()
    category = request.form.get('category', 'Other')
    date = request.form.get('date', expense.date)
    note = request.form.get('note', '').strip()

    if not title or not amount:
        flash('Title and amount are required.', 'error')
        return redirect(url_for('dashboard'))

    try:
        amount = float(amount)
        if amount <= 0:
            raise ValueError
    except ValueError:
        flash('Please enter a valid amount.', 'error')
        return redirect(url_for('dashboard'))

    expense.title = title
    expense.amount = amount
    expense.category = category
    expense.date = date
    expense.note = note
    db.session.commit()
    flash('Expense updated successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/delete/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
    if expense:
        db.session.delete(expense)
        db.session.commit()
        flash('Expense deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('signin'))


if __name__ == '__main__':
    app.run(debug=True)
