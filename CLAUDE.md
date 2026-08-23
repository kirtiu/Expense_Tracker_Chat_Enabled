# CLAUDE.md

Agentic AI Expense Tracker — OpenAI-powered Flask app with Claude Code integration for development workflow.

---

## 🚀 Quick Start

### Setup & Run

Always use venv to avoid conflicts:

```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Install/update dependencies
pip install -r requirements.txt

# Set OpenAI API key (in .env file)
notepad .env
# Add: OPENAI_API_KEY=sk-...

# Run dev server
flask run
```

**Access:** http://127.0.0.1:5000  
**Demo account:** `admin@example.com` / `password123`  
**Note:** Restart server after editing `app.py`

---

## 🏗️ Architecture

### Core Stack
- **Backend:** Flask + SQLAlchemy (SQLite)
- **Frontend:** Vanilla JS + glassmorphism CSS
- **AI:** OpenAI API (gpt-4o-mini) with function calling
- **Auth:** Session-based (`session['user_id']`)

### Database Models
- **`User`** — email, password, owns expenses (cascade delete)
- **`Expense`** — title, amount, category, date (YYYY-MM-DD), note, user_id

### API Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Redirect to signin |
| `/signin` | GET/POST | Login |
| `/signup` | GET/POST | Register |
| `/dashboard` | GET | View expenses (sortable) |
| `/add` | POST | Form-based expense add |
| `/edit/<id>` | POST | Form-based expense edit |
| `/delete/<id>` | POST | Delete expense |
| `/chat` | POST | **Agentic AI chat endpoint** |
| `/signout` | GET | Logout |

### Agentic Tools (OpenAI Function Calling)

Eight tools available to Claude via `/chat`:

```python
1. add_expense(title, amount, category, date?, note?, confirm?)
   - Checks for duplicates (current month, 70% match threshold)
   - Asks user confirmation if duplicate found
   - Validates amount > 0, category in CATEGORIES

2. list_expenses(limit?, category?)
   - Returns user's expenses (date-sorted DESC)
   - Optional category filter

3. delete_expense(expense_id)
   - Removes expense by ID
   - Validates ownership

4. summarize_spending(period)
   - period: 'all_time' | 'this_month' | 'this_week'
   - Returns total + breakdown by category

5. suggest_category(title)
   - AI-powered keyword matching for 6 categories
   - Returns top matching category for expense title

6. search_expenses(keywords?, category?, min_amount?, max_amount?, start_date?, end_date?, limit?)
   - Advanced search with multiple filters
   - keywords: search in title/note (case-insensitive substring match)
   - category: filter by category
   - min_amount/max_amount: filter by amount range (₹)
   - start_date/end_date: filter by date range (YYYY-MM-DD format)
   - limit: max results (default 50)
   - Returns matching expenses sorted by date DESC
   - Example: "Find food expenses over ₹500 from August"

7. set_budget(category, limit_amount, period?)
   - Set spending limit for a category
   - category: one of the 7 categories
   - limit_amount: monthly/all-time limit in ₹
   - period: 'monthly' (default) or 'all_time'
   - Returns confirmation with budget details
   - Example: "Set budget of 5000 for Food"

8. get_budget_status(category?)
   - Check spending vs budget limits
   - category: specific category to check (optional)
   - Returns spending, limit, remaining, percentage used, and status
   - Alerts when budget exceeded (100%+) or near limit (80%+)
   - Example: "Show budget status"
```

### Frontend Chat Widget

**Location:** `templates/dashboard.html` (bottom-right 💬 button)

- Messages sent to `/chat` with conversation history
- Frontend tracks `chatHistory` (user + assistant messages)
- Claude handles multi-turn conversations
- Conversation state persists during session

### Key Design Patterns

1. **Session Auth Guard:** All protected routes check `'user_id' in session`
2. **Sorting via URL:** Dashboard uses `url_for('dashboard', sort=col, order=...)` links (not JS)
3. **Duplicate Detection:** Fuzzy matching (fuzzywuzzy) on expense titles, same month only
4. **Tool Calling Loop:** Agentic pattern—send message → Claude decides tool → execute → return result → Claude responds

---

## 🛠️ Available Claude Code Skills

### Use `/code-review` for pull requests

```bash
/code-review <branch|PR#>        # Low-effort review
/code-review medium <branch>     # Medium-effort review
/code-review high <branch>       # Deep review with suggestions
/code-review ultra <PR#>         # Multi-agent cloud review (billed)
```

**When to use:**
- Before pushing to main
- After major feature additions
- After refactoring

---

### Use `/run` to test the app

```bash
/run
```

- Launches dev server
- Opens browser to http://127.0.0.1:5000
- Good for smoke testing changes

---

### Use `claude-api` skill for OpenAI/Claude API questions

```bash
/claude-api
```

Reference for:
- Model pricing and capabilities
- Tool use patterns
- Token counting
- Streaming best practices

---

## 🧪 Testing Strategy

### Unit Tests (pytest)

Create `tests/` folder with test files:

```bash
# Run all tests
.\venv\Scripts\pytest.exe

# Run single file
.\venv\Scripts\pytest.exe tests/test_tools.py

# Run with coverage
.\venv\Scripts\pytest.exe --cov=app tests/
```

**Key test areas:**
- Tool functions (add/list/delete/summarize)
- Duplicate detection logic
- Authentication (session checks)
- Database operations

---

### Manual Testing via Chat

Test agentic tools by typing in the chat widget:

```
# Add expense
"Add 500 for lunch today"
"Add 1000 for phone this month" (triggers duplicate check)

# List & filter
"Show my expenses"
"Show food expenses"

# Delete
"Delete my last expense"

# Summary
"How much did I spend this month?"
"Spending breakdown by category"
```

---

## 📁 Key Files & Their Roles

| File | Purpose |
|------|---------|
| `app.py` | Main Flask app, models, routes, agentic tools |
| `requirements.txt` | Dependencies (flask, openai, fuzzywuzzy, etc.) |
| `.env` | OpenAI API key (not committed) |
| `templates/signin.html` | Login form |
| `templates/signup.html` | Registration form |
| `templates/dashboard.html` | Main dashboard + chat widget |
| `expenses.db` | SQLite database (auto-created, not committed) |

---

## 🔄 Development Workflow (Claude Code Best Practices)

### Before Making Changes

1. **Read CLAUDE.md** (this file) for context
2. **Check git status** to see what's changed
3. **Understand the agentic pattern** — tools run in `/chat` route context

### Making a Change

1. **Edit files** using Edit tool (preserves context)
2. **Test locally** using `/run` or manual testing
3. **Review your changes** with `/code-review`
4. **Commit with clear message** referencing the feature

### Subagent Recommendations

#### For Code Review
```
When you're about to commit a feature, use:
/code-review medium <your-branch>
```
This catches issues with:
- Tool calling logic (confirm parameter, fuzzy matching)
- Session auth guards
- Database operations
- API request formatting

#### For Testing
```
When implementing a new tool feature, ask for help:
"Create comprehensive test cases for [feature]"
```
Good for:
- Edge case coverage
- Duplicate detection scenarios
- Tool parameter validation

#### For Bug Investigation
```
When debugging, spawn an agent:
"Debug this issue: [description]"
```
The agent can:
- Search code for related logic
- Check recent commits
- Suggest root causes

---

## 🎯 Common Tasks

### Add a New Tool

1. Add tool definition to `TOOLS` list (JSON schema)
2. Implement function (e.g., `my_tool_func()`)
3. Handle in `/chat` route `if tool_name == 'my_tool':`
4. Test via chat widget
5. Run `/code-review` before committing

### Modify a Tool

1. Update tool schema if parameters changed
2. Update function implementation
3. Test with `/run` (manual testing in chat)
4. Run `/code-review`

### Add Frontend Feature

1. Edit `templates/dashboard.html`
2. Update inline styles or JavaScript
3. Test with `/run` to see in browser
4. Run `/code-review` for JS quality

### Add Database Fields

1. Add column to `Expense` or `User` model in `app.py`
2. Database auto-migrates on `db.create_all()`
3. Update tools that reference the field
4. Test with `/run`

---

## 📊 Project Status

**Completed Features:**
- ✅ Agentic chat interface
- ✅ 8 tools (add/list/delete/summarize/suggest_category/search/set_budget/get_budget_status)
- ✅ Duplicate expense detection (70% fuzzy matching)
- ✅ Multi-turn conversation history
- ✅ Session-based authentication
- ✅ Expense sorting & filtering (form-based)
- ✅ Advanced search (UI filters + AI tool for natural language queries)
- ✅ Voice input (Web Speech API with real-time transcription)
- ✅ Charts/visualization (Chart.js doughnut + monthly trend bars)
- ✅ Smart categorization (AI-powered keyword matching)
- ✅ Export reports (PDF + CSV with stats and formatting)
- ✅ Budget alerts (spending limits, progress bars, auto-alerts at 80%/100%)


---

## 📋 Task Tracking

Track feature development progress:

| # | Feature | Status | Priority | Owner | ETA |
|---|---------|--------|----------|-------|-----|
| 1 | Voice Input 🎤 | Done | HIGH | Kirti | 2026-08-16 |
| 2 | Charts/Visualization 📊 | Done | HIGH | Kirti | 2026-08-16 |
| 3 | Smart Categorization 🧠 | Done | MEDIUM | Kirti | 2026-08-16 |
| 4 | Export Reports (PDF/CSV) 📄 | Done | MEDIUM | Kirti | 2026-08-19 |
| 5 | Advanced Search 🔍 | Done | MEDIUM | Kirti | 2026-08-19 |
| 6 | Budget Alerts ⚠️ | Done | MEDIUM | Kirti | 2026-08-21 |

**Legend:**
- Status: Not Started | In Progress | Testing | Done
- Priority: LOW | MEDIUM | HIGH | CRITICAL
- Owner: Who's working on it
- ETA: Target completion date

**How to Use:**
```bash
# Start a task
Task: "Build Voice Input feature"
Status: In Progress

# Complete a task
Status: Done
Commit: abc123def (with feature branch)
```

---

## 🔐 Security Notes

- **Passwords:** Currently plaintext (demo only; hash before production)
- **API Key:** Stored in `.env` (not committed)
- **Session:** Server-side via Flask session
- **SQLi:** Protected by SQLAlchemy ORM
- **XSS:** Jinja2 auto-escapes, chat widget escapes HTML

---

## 📚 References

- **Flask:** https://flask.palletsprojects.com/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **OpenAI API:** https://platform.openai.com/docs/
- **Claude Code Docs:** https://claude.ai/code
- **Fuzzywuzzy:** https://github.com/seatgeek/fuzzywuzzy

---

## 🚀 Next Steps

1. **Deploy** — Host on Railway, Heroku, or Fly.io

---

**Last Updated:** 2026-08-19  
**Maintainer:** Kirti Upadhyay (ukirti1911@gmail.com)
