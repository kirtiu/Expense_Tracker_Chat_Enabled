from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import csv
from io import StringIO, BytesIO
from openai import OpenAI
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from fpdf import FPDF

load_dotenv()

app = Flask(__name__)
app.secret_key = 'expense_tracker_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'expenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

CATEGORIES = ['Food', 'Transport', 'Shopping', 'Health', 'Entertainment', 'Bills', 'Other']

openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_expense",
            "description": "Add a new expense to the user's tracker. Will check for similar expenses in current month and ask for confirmation if found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Expense title (e.g., 'Lunch', 'Gas')"},
                    "amount": {"type": "number", "description": "Amount in rupees"},
                    "category": {"type": "string", "enum": CATEGORIES, "description": "Expense category"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format (defaults to today if not provided)"},
                    "note": {"type": "string", "description": "Optional notes about the expense"},
                    "confirm": {"type": "boolean", "description": "Set to true after asking user about duplicates"}
                },
                "required": ["title", "amount", "category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_expenses",
            "description": "List expenses for the user, optionally filtered by category",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Maximum number of expenses to return (default 10)"},
                    "category": {"type": "string", "description": "Filter by category (optional)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_expense",
            "description": "Delete an expense by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "expense_id": {"type": "integer", "description": "The ID of the expense to delete"}
                },
                "required": ["expense_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_spending",
            "description": "Get a summary of spending by category and total",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["all_time", "this_month", "this_week"], "description": "Time period for summary"}
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_category",
            "description": "Suggest the best category for an expense based on its title",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "The expense title or description (e.g., 'flight to Delhi', 'lunch')"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_expenses",
            "description": "Advanced search for expenses with multiple filters (date range, amount range, category, keywords)",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {"type": "string", "description": "Search keywords to find in title or notes (optional)"},
                    "category": {"type": "string", "description": "Filter by category (optional)"},
                    "min_amount": {"type": "number", "description": "Minimum amount in rupees (optional)"},
                    "max_amount": {"type": "number", "description": "Maximum amount in rupees (optional)"},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format (optional)"},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format (optional)"},
                    "limit": {"type": "integer", "description": "Maximum number of results to return (default 50)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_budget",
            "description": "Set a spending budget for a category",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORIES, "description": "Budget category"},
                    "limit_amount": {"type": "number", "description": "Monthly limit amount in rupees"},
                    "period": {"type": "string", "enum": ["monthly", "all_time"], "description": "Budget period (default: monthly)"}
                },
                "required": ["category", "limit_amount"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": "Get spending status against budgets",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Specific category to check (optional, checks all if not specified)"}
                }
            }
        }
    }
]


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


class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    limit_amount = db.Column(db.Float, nullable=False)
    period = db.Column(db.String(20), default='monthly')  # 'monthly' or 'all_time'
    created_at = db.Column(db.String(20), default=lambda: datetime.now().strftime('%Y-%m-%d'))


# ── Init DB & seed default user ──────────────────────────────────────────────

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@example.com').first():
        db.session.add(User(email='admin@example.com', password='password123'))
        db.session.commit()


# ── Export Functions ────────────────────────────────────────────────────────

def generate_csv_export(expenses):
    """Generate CSV data for expenses"""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Amount (Rs)', 'Category', 'Date', 'Note'])
    for exp in expenses:
        writer.writerow([exp.title, f'{exp.amount:.2f}', exp.category, exp.date, exp.note])
    return output.getvalue()


def generate_pdf_export(expenses, stats):
    """Generate PDF report for expenses"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Courier', 'B', 16)
    pdf.cell(0, 10, 'Expense Report', ln=True, align='C')

    # Stats section
    pdf.set_font('Courier', 'B', 12)
    pdf.cell(0, 10, 'Summary', ln=True)
    pdf.set_font('Courier', '', 10)
    pdf.cell(0, 8, f"Total Expenses: Rs {stats['total']:.2f}", ln=True)
    pdf.cell(0, 8, f"Average Expense: Rs {stats['average']:.2f}", ln=True)
    pdf.cell(0, 8, f"Highest Expense: Rs {stats['highest']:.2f}", ln=True)
    pdf.cell(0, 8, f"Total Count: {stats['count']}", ln=True)

    # By category breakdown
    category_totals = {}
    for exp in expenses:
        if exp.category not in category_totals:
            category_totals[exp.category] = 0
        category_totals[exp.category] += exp.amount

    pdf.set_font('Courier', 'B', 12)
    pdf.cell(0, 10, 'By Category', ln=True)
    pdf.set_font('Courier', '', 10)
    for cat, total in sorted(category_totals.items()):
        pdf.cell(0, 8, f"{cat}: Rs {total:.2f}", ln=True)

    # Expenses table
    pdf.set_font('Courier', 'B', 12)
    pdf.cell(0, 10, 'Expenses', ln=True)
    pdf.set_font('Courier', '', 9)

    # Table header
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 7, 'Date', border=1, fill=True)
    pdf.cell(50, 7, 'Title', border=1, fill=True)
    pdf.cell(30, 7, 'Category', border=1, fill=True)
    pdf.cell(30, 7, 'Amount', border=1, fill=True)
    pdf.ln()

    # Table rows
    for exp in sorted(expenses, key=lambda x: x.date, reverse=True)[:30]:
        pdf.cell(40, 7, exp.date, border=1)
        pdf.cell(50, 7, exp.title[:25], border=1)
        pdf.cell(30, 7, exp.category, border=1)
        pdf.cell(30, 7, f'Rs {exp.amount:.2f}', border=1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')


# ── Tool Functions ──────────────────────────────────────────────────────────

def suggest_category(title):
    """Use fuzzy matching to suggest category based on title"""
    title_lower = title.lower()

    # Category keywords mapping
    category_keywords = {
        'Food': ['lunch', 'dinner', 'breakfast', 'coffee', 'meal', 'food', 'restaurant', 'pizza', 'burger', 'snack', 'eat', 'grocery'],
        'Transport': ['taxi', 'uber', 'bus', 'train', 'flight', 'gas', 'petrol', 'bike', 'car', 'transport', 'commute', 'travel', 'metro', 'auto'],
        'Shopping': ['clothes', 'shirt', 'pants', 'shoes', 'shopping', 'buy', 'store', 'mall', 'dress', 'wear', 'purchase'],
        'Health': ['doctor', 'hospital', 'medicine', 'health', 'clinic', 'medical', 'pharmacy', 'drug', 'pill', 'vaccine'],
        'Entertainment': ['movie', 'cinema', 'game', 'play', 'show', 'concert', 'entertainment', 'ticket', 'music', 'sports'],
        'Bills': ['bill', 'electricity', 'water', 'internet', 'phone', 'rent', 'subscription', 'phone bill', 'utility'],
    }

    best_match = 'Other'
    best_score = 0

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in title_lower:
                score = len(keyword)  # Longer matches are better
                if score > best_score:
                    best_score = score
                    best_match = category

    return {'suggested_category': best_match, 'title': title}


def check_duplicate_expense(title, category=None):
    """Check for similar expenses in current month"""
    if 'user_id' not in session:
        return None

    current_month = datetime.now().strftime('%Y-%m')
    month_expenses = Expense.query.filter_by(user_id=session['user_id']).filter(
        Expense.date.startswith(current_month)
    ).all()

    duplicates = []
    for exp in month_expenses:
        similarity = fuzz.token_set_ratio(title.lower(), exp.title.lower())
        if similarity >= 70:  # 70% match threshold
            duplicates.append({
                'id': exp.id,
                'title': exp.title,
                'amount': float(exp.amount),
                'category': exp.category,
                'date': exp.date
            })

    return duplicates if duplicates else None


def add_expense_tool(title, amount, category, date=None, note='', confirm=False):
    """Add expense for the current user"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    try:
        amount = float(amount)
        if amount <= 0:
            return {'error': 'Amount must be positive'}
    except ValueError:
        return {'error': 'Invalid amount'}

    if category not in CATEGORIES:
        return {'error': f'Invalid category. Must be one of: {", ".join(CATEGORIES)}'}

    # Check for duplicates only on first attempt
    if not confirm:
        duplicates = check_duplicate_expense(title, category)
        if duplicates:
            dup_list = '\n'.join([f"  • {d['title']}: ₹{d['amount']} on {d['date']}" for d in duplicates])
            return {
                'duplicate_found': True,
                'message': f'Found similar expense(s) this month:\n{dup_list}\n\nStill want to add {title} for ₹{amount}?',
                'duplicates': duplicates,
                'title': title,
                'amount': amount,
                'category': category,
                'date': date,
                'note': note
            }

    # Add the expense
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
    return {'success': True, 'message': f'Added {title} for ₹{amount:.2f} on {date}', 'expense_id': expense.id}


def list_expenses_tool(limit=10, category=None):
    """List expenses for the current user"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    query = Expense.query.filter_by(user_id=session['user_id']).order_by(Expense.date.desc())
    if category:
        query = query.filter_by(category=category)
    expenses = query.limit(limit).all()

    return {
        'expenses': [
            {
                'id': e.id,
                'title': e.title,
                'amount': float(e.amount),
                'category': e.category,
                'date': e.date,
                'note': e.note
            }
            for e in expenses
        ]
    }


def delete_expense_tool(expense_id):
    """Delete an expense"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    expense = Expense.query.filter_by(id=expense_id, user_id=session['user_id']).first()
    if not expense:
        return {'error': f'Expense with ID {expense_id} not found'}

    db.session.delete(expense)
    db.session.commit()
    return {'success': True, 'message': f'Deleted expense: {expense.title}'}


def summarize_spending_tool(period='this_month'):
    """Summarize spending by category"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    if period == 'this_month':
        current_month = datetime.now().strftime('%Y-%m')
        expenses = [e for e in expenses if e.date.startswith(current_month)]
    elif period == 'this_week':
        from datetime import timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        expenses = [e for e in expenses if e.date >= week_ago]

    total = sum(e.amount for e in expenses)
    category_totals = {}
    for cat in CATEGORIES:
        cat_total = sum(e.amount for e in expenses if e.category == cat)
        if cat_total > 0:
            category_totals[cat] = cat_total

    return {
        'period': period,
        'total': float(total),
        'by_category': category_totals
    }


def search_expenses_tool(keywords=None, category=None, min_amount=None, max_amount=None,
                         start_date=None, end_date=None, limit=50):
    """Advanced search for expenses with multiple filters"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    query = Expense.query.filter_by(user_id=session['user_id'])

    # Filter by keywords (title or note)
    if keywords:
        keywords_lower = keywords.lower()
        query = query.filter(
            (Expense.title.ilike(f'%{keywords_lower}%')) |
            (Expense.note.ilike(f'%{keywords_lower}%'))
        )

    # Filter by category
    if category and category in CATEGORIES:
        query = query.filter_by(category=category)

    # Filter by amount range
    if min_amount is not None:
        query = query.filter(Expense.amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Expense.amount <= max_amount)

    # Filter by date range
    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    expenses = query.order_by(Expense.date.desc()).limit(limit).all()

    if not expenses:
        return {'expenses': [], 'count': 0, 'message': 'No expenses found matching your criteria.'}

    return {
        'expenses': [
            {
                'id': e.id,
                'title': e.title,
                'amount': float(e.amount),
                'category': e.category,
                'date': e.date,
                'note': e.note
            }
            for e in expenses
        ],
        'count': len(expenses)
    }


def set_budget_tool(category, limit_amount, period='monthly'):
    """Set a budget limit for a category"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    if category not in CATEGORIES:
        return {'error': f'Invalid category. Must be one of: {", ".join(CATEGORIES)}'}

    try:
        limit_amount = float(limit_amount)
        if limit_amount <= 0:
            return {'error': 'Budget limit must be positive'}
    except ValueError:
        return {'error': 'Invalid amount'}

    # Check if budget already exists for this category
    existing_budget = Budget.query.filter_by(
        user_id=session['user_id'],
        category=category,
        period=period
    ).first()

    if existing_budget:
        existing_budget.limit_amount = limit_amount
        db.session.commit()
        return {
            'success': True,
            'message': f'Updated {period} budget for {category}: ₹{limit_amount:.2f}'
        }
    else:
        budget = Budget(
            user_id=session['user_id'],
            category=category,
            limit_amount=limit_amount,
            period=period
        )
        db.session.add(budget)
        db.session.commit()
        return {
            'success': True,
            'message': f'Set {period} budget for {category}: ₹{limit_amount:.2f}'
        }


def get_budget_status_tool(category=None):
    """Get current spending status against budgets"""
    if 'user_id' not in session:
        return {'error': 'Not authenticated'}

    budgets = Budget.query.filter_by(user_id=session['user_id']).all()

    if not budgets:
        return {'budgets': [], 'message': 'No budgets set yet.'}

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    current_month = datetime.now().strftime('%Y-%m')

    result = []
    for budget in budgets:
        if category and budget.category != category:
            continue

        # Calculate spending
        if budget.period == 'monthly':
            spending = sum(e.amount for e in expenses if e.category == budget.category and e.date.startswith(current_month))
        else:
            spending = sum(e.amount for e in expenses if e.category == budget.category)

        remaining = budget.limit_amount - spending
        percentage = (spending / budget.limit_amount * 100) if budget.limit_amount > 0 else 0
        status = 'OK' if spending <= budget.limit_amount else 'EXCEEDED'

        result.append({
            'category': budget.category,
            'period': budget.period,
            'limit': float(budget.limit_amount),
            'spent': float(spending),
            'remaining': float(remaining),
            'percentage': round(percentage, 1),
            'status': status
        })

    return {'budgets': result}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route('/chat', methods=['POST'])
def chat():
    """Handle agent chat with tool calling"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.json
    user_message = data.get('message', '').strip()
    history = data.get('history', [])

    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    history.append({'role': 'user', 'content': user_message})

    messages = history.copy()

    while True:
        response = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=messages,
            tools=TOOLS,
            tool_choice='auto'
        )

        assistant_message = response.choices[0].message

        msg_dict = {
            'role': 'assistant',
            'content': assistant_message.content
        }
        if assistant_message.tool_calls:
            msg_dict['tool_calls'] = [
                {
                    'id': tc.id,
                    'type': 'function',
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments
                    }
                }
                for tc in assistant_message.tool_calls
            ]
        messages.append(msg_dict)

        if response.choices[0].finish_reason == 'tool_calls':
            tool_results = []
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == 'add_expense':
                    result = add_expense_tool(**tool_args)
                elif tool_name == 'list_expenses':
                    result = list_expenses_tool(**tool_args)
                elif tool_name == 'delete_expense':
                    result = delete_expense_tool(**tool_args)
                elif tool_name == 'summarize_spending':
                    result = summarize_spending_tool(**tool_args)
                elif tool_name == 'suggest_category':
                    result = suggest_category(**tool_args)
                elif tool_name == 'search_expenses':
                    result = search_expenses_tool(**tool_args)
                elif tool_name == 'set_budget':
                    result = set_budget_tool(**tool_args)
                elif tool_name == 'get_budget_status':
                    result = get_budget_status_tool(**tool_args)
                else:
                    result = {'error': f'Unknown tool: {tool_name}'}

                tool_results.append({
                    'tool_call_id': tool_call.id,
                    'role': 'tool',
                    'content': json.dumps(result)
                })

            messages.extend(tool_results)
        else:
            break

    final_response = assistant_message.content or 'No response generated'

    history.append({'role': 'assistant', 'content': final_response})

    return jsonify({
        'response': final_response,
        'history': history
    })


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

    # Advanced search filters
    keywords = request.args.get('keywords', '').strip()
    category_filter = request.args.get('category', '').strip()
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    # Build query
    query = Expense.query.filter_by(user_id=session['user_id'])

    # Apply filters
    if keywords:
        keywords_lower = keywords.lower()
        query = query.filter(
            (Expense.title.ilike(f'%{keywords_lower}%')) |
            (Expense.note.ilike(f'%{keywords_lower}%'))
        )

    if category_filter and category_filter in CATEGORIES:
        query = query.filter_by(category=category_filter)

    try:
        if min_amount:
            query = query.filter(Expense.amount >= float(min_amount))
        if max_amount:
            query = query.filter(Expense.amount <= float(max_amount))
    except ValueError:
        pass

    if start_date:
        query = query.filter(Expense.date >= start_date)
    if end_date:
        query = query.filter(Expense.date <= end_date)

    # Apply sorting
    sort_col_map = {
        'date': Expense.date,
        'amount': Expense.amount,
        'title': Expense.title,
        'category': Expense.category,
    }
    sort_col = sort_col_map.get(sort_by, Expense.date)
    sort_expr = sort_col.desc() if order == 'desc' else sort_col.asc()
    user_expenses = query.order_by(sort_expr).all()

    total = sum(e.amount for e in user_expenses)

    current_month = datetime.now().strftime('%Y-%m')
    monthly_total = sum(e.amount for e in user_expenses if e.date.startswith(current_month))

    category_totals = {}
    for cat in CATEGORIES:
        cat_total = sum(e.amount for e in user_expenses if e.category == cat)
        if cat_total > 0:
            category_totals[cat] = cat_total

    today = datetime.now().strftime('%Y-%m-%d')

    # Get budget status
    budgets = Budget.query.filter_by(user_id=session['user_id']).all()
    current_month = datetime.now().strftime('%Y-%m')
    budget_status = {}
    budget_alerts = []

    for budget in budgets:
        if budget.period == 'monthly':
            spending = sum(e.amount for e in user_expenses if e.category == budget.category and e.date.startswith(current_month))
        else:
            spending = sum(e.amount for e in user_expenses if e.category == budget.category)

        remaining = budget.limit_amount - spending
        percentage = (spending / budget.limit_amount * 100) if budget.limit_amount > 0 else 0
        status = 'OK' if spending <= budget.limit_amount else 'EXCEEDED'

        budget_status[budget.category] = {
            'limit': float(budget.limit_amount),
            'spent': float(spending),
            'remaining': float(remaining),
            'percentage': round(percentage, 1),
            'status': status
        }

        # Create alerts for exceeded or near-limit budgets
        if status == 'EXCEEDED':
            budget_alerts.append({
                'category': budget.category,
                'type': 'danger',
                'message': f'Budget exceeded for {budget.category}! Spent ₹{spending:.2f} of ₹{budget.limit_amount:.2f}'
            })
        elif percentage >= 80:
            budget_alerts.append({
                'category': budget.category,
                'type': 'warning',
                'message': f'{budget.category} budget at {percentage:.0f}%. Only ₹{remaining:.2f} remaining.'
            })

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
        order=order,
        budget_status=budget_status,
        budget_alerts=budget_alerts
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


@app.route('/export', methods=['GET'])
def export_expenses():
    """Export expenses as CSV or PDF"""
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    fmt = request.args.get('format', 'csv').lower()
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    if not expenses:
        flash('No expenses to export.', 'error')
        return redirect(url_for('dashboard'))

    # Calculate stats
    total = sum(e.amount for e in expenses)
    average = total / len(expenses) if expenses else 0
    highest = max(e.amount for e in expenses) if expenses else 0
    stats = {'total': total, 'average': average, 'highest': highest, 'count': len(expenses)}

    try:
        if fmt == 'csv':
            data = generate_csv_export(expenses)
            return send_file(
                BytesIO(data.encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name='expenses.csv'
            )
        elif fmt == 'pdf':
            data = generate_pdf_export(expenses, stats)
            return send_file(
                BytesIO(data),
                mimetype='application/pdf',
                as_attachment=True,
                download_name='expenses.pdf'
            )
        else:
            flash('Invalid format. Use csv or pdf.', 'error')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Export error: {str(e)}', 'error')
        return redirect(url_for('dashboard'))


@app.route('/chart-data', methods=['GET'])
def get_chart_data():
    """Get expense data formatted for charts"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    expenses = Expense.query.filter_by(user_id=session['user_id']).all()

    if not expenses:
        return jsonify({
            'by_category': {'labels': [], 'data': []},
            'by_month': {'labels': [], 'data': []},
            'stats': {'total': 0, 'average': 0, 'highest': 0, 'count': 0}
        })

    # 1. By Category (Pie Chart)
    category_totals = {}
    for cat in CATEGORIES:
        total = sum(e.amount for e in expenses if e.category == cat)
        if total > 0:
            category_totals[cat] = total

    by_category = {
        'labels': list(category_totals.keys()),
        'data': list(category_totals.values())
    }

    # 2. By Month (Bar/Line Chart)
    month_totals = {}
    for exp in expenses:
        month = exp.date[:7]  # YYYY-MM
        if month not in month_totals:
            month_totals[month] = 0
        month_totals[month] += exp.amount

    sorted_months = sorted(month_totals.keys())
    by_month = {
        'labels': sorted_months,
        'data': [month_totals[m] for m in sorted_months]
    }

    # 3. Statistics
    total = sum(e.amount for e in expenses)
    average = total / len(expenses) if expenses else 0
    highest = max(e.amount for e in expenses) if expenses else 0

    stats = {
        'total': round(total, 2),
        'average': round(average, 2),
        'highest': round(highest, 2),
        'count': len(expenses)
    }

    return jsonify({
        'by_category': by_category,
        'by_month': by_month,
        'stats': stats
    })


@app.route('/budget-status', methods=['GET'])
def get_budget_status():
    """Get budget status data"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    budgets = Budget.query.filter_by(user_id=session['user_id']).all()
    expenses = Expense.query.filter_by(user_id=session['user_id']).all()
    current_month = datetime.now().strftime('%Y-%m')

    budget_status = []
    for budget in budgets:
        if budget.period == 'monthly':
            spending = sum(e.amount for e in expenses if e.category == budget.category and e.date.startswith(current_month))
        else:
            spending = sum(e.amount for e in expenses if e.category == budget.category)

        remaining = budget.limit_amount - spending
        percentage = (spending / budget.limit_amount * 100) if budget.limit_amount > 0 else 0
        status = 'OK' if spending <= budget.limit_amount else 'EXCEEDED'

        budget_status.append({
            'category': budget.category,
            'limit': float(budget.limit_amount),
            'spent': float(spending),
            'remaining': float(remaining),
            'percentage': round(percentage, 1),
            'status': status
        })

    return jsonify({'budgets': budget_status})


@app.route('/signout')
def signout():
    session.clear()
    return redirect(url_for('signin'))


if __name__ == '__main__':
    app.run(debug=True)
