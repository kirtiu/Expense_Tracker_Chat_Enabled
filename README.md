# 💰 AI-Powered Expense Tracker

An intelligent expense tracking application powered by Claude AI with natural language processing, budget alerts, and comprehensive analytics.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-2.0+-green)
![SQLite](https://img.shields.io/badge/SQLite-3-lightblue)
![OpenAI](https://img.shields.io/badge/OpenAI-API-black)
![License](https://img.shields.io/badge/License-MIT-green)

---

## 🚀 Features

### Core Functionality
- **🤖 Agentic AI Chat** - Interact with Claude AI to manage expenses naturally
- **💬 Multi-turn Conversations** - Maintain context across multiple messages
- **🎯 Smart Categorization** - AI automatically categorizes expenses
- **🔍 Advanced Search** - Filter by keywords, amounts, dates, and categories
- **⚠️ Budget Alerts** - Set spending limits and get warnings at 80%/100%

### Analytics & Insights
- **📊 Interactive Charts** - Doughnut chart for spending by category, monthly trends bar chart
- **📈 Spending Analytics** - Track totals by time period and category
- **📋 Expense Breakdown** - See detailed statistics and patterns
- **🎤 Voice Input** - Add expenses using voice commands

### Data Management
- **📥 Export Reports** - Download as PDF or CSV with formatted stats
- **🔐 Duplicate Detection** - AI detects and alerts on duplicate expenses (70% match threshold)
- **🗂️ Expense Organization** - Sort and filter expenses by multiple criteria
- **💾 Persistent Storage** - SQLite database with user sessions

### User Experience
- **🌙 Professional Dark Theme** - Dark navy background with blue accents
- **⚡ Auto-Refresh** - Dashboard updates automatically when expenses added via chat
- **📱 Responsive Design** - Works seamlessly on desktop and mobile
- **🎨 Glassmorphism UI** - Modern design with smooth interactions

---

## 🛠️ Tech Stack

### Backend
- **Framework:** Flask
- **ORM:** SQLAlchemy
- **Database:** SQLite
- **AI:** OpenAI API (GPT-4o-mini) with function calling

### Frontend
- **Language:** Vanilla JavaScript
- **Styling:** CSS3 with modern features
- **Charts:** Chart.js
- **UI:** Glassmorphism design pattern

### DevOps
- **Version Control:** Git & GitHub
- **Package Management:** pip
- **Virtual Environment:** venv

---

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)
- OpenAI API key (get from https://platform.openai.com/)

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/kirtiu/Expense_Tracker_Chat_Enabled.git
cd Expense_Tracker_Chat_Enabled
```

### 2. Create Virtual Environment
```powershell
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```
OPENAI_API_KEY=sk-your-api-key-here
```

### 5. Run the Application
```bash
flask run
```

Access the app at: **http://127.0.0.1:5000**

---

## 🎯 Usage

### Quick Start
1. **Sign Up:** Create a new account with email and password
2. **Add Expenses:** Use the form or chat with "Add ₹500 for lunch"
3. **View Dashboard:** See charts, analytics, and recent expenses
4. **Set Budgets:** Tell Claude "Set budget of 5000 for Food"
5. **Export:** Download reports as PDF or CSV

### Chat Examples

```
"Add 500 for lunch today"
→ AI adds expense automatically

"Show my food expenses"
→ Lists all food category expenses

"How much did I spend this month?"
→ Shows monthly total and breakdown

"Find expenses over 1000 from August"
→ Advanced search with filters

"Set budget of 5000 for Shopping"
→ Creates budget limit with alerts

"Delete my last expense"
→ Removes most recent expense
```

---

## 🏗️ Project Structure

```
expense-tracker/
├── app.py                    # Main Flask app + AI tools
├── requirements.txt          # Python dependencies
├── .env                      # API keys (not committed)
├── expenses.db              # SQLite database (auto-created)
├── templates/
│   ├── signin.html          # Login page
│   ├── signup.html          # Registration page
│   └── dashboard.html       # Main dashboard + chat widget
├── CLAUDE.md                # Development documentation
└── README.md                # This file
```

---

## 🤖 AI Tools (Function Calling)

The app exposes 8 tools to Claude AI:

| Tool | Purpose |
|------|---------|
| `add_expense()` | Add new expense with duplicate detection |
| `list_expenses()` | Retrieve expenses with optional filters |
| `delete_expense()` | Remove expense by ID |
| `summarize_spending()` | Get spending totals by period |
| `suggest_category()` | AI-powered category recommendation |
| `search_expenses()` | Advanced search with multiple filters |
| `set_budget()` | Create spending limits for categories |
| `get_budget_status()` | Check spending vs budget limits |

---

## 📊 Database Schema

### Users Table
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
)
```

### Expenses Table
```sql
CREATE TABLE expense (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(255) NOT NULL,
    amount FLOAT NOT NULL,
    category VARCHAR(50),
    date DATE,
    note TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
)
```

### Budgets Table
```sql
CREATE TABLE budget (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category VARCHAR(50) NOT NULL,
    limit_amount FLOAT NOT NULL,
    period VARCHAR(20) DEFAULT 'monthly',
    created_at TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
)
```

---

## 🎨 Design Features

### Color Scheme
- **Background:** Dark Navy (#0f1729 to #1a2844 gradient)
- **Cards:** Medium Blue (#1e3a5f)
- **Accents:** Dark Green (#059669)
- **Text:** Light Gray (#e2e8f0)

### Responsive Breakpoints
- **Desktop:** 1280px+
- **Tablet:** 768px - 1024px
- **Mobile:** < 768px

---

## 🚀 Deployment

### Quick Deploy to Railway

1. Push to GitHub
2. Connect repository to Railway
3. Set environment variables:
   - `OPENAI_API_KEY=your-key`
4. Deploy!

### Other Options
- **Render:** https://render.com
- **Heroku:** https://www.heroku.com
- **Fly.io:** https://fly.io
- **AWS:** https://aws.amazon.com

---

## 📝 Demo Credentials

**For testing purposes:**
- Email: `admin@example.com`
- Password: `password123`

⚠️ Change password after first login!

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🐛 Bug Reports & Feature Requests

Found a bug? Have a feature idea?

1. Check existing [Issues](https://github.com/kirtiu/Expense_Tracker_Chat_Enabled/issues)
2. [Create a new issue](https://github.com/kirtiu/Expense_Tracker_Chat_Enabled/issues/new) with:
   - Clear description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior

---

## 📚 Resources

- **Flask Documentation:** https://flask.palletsprojects.com/
- **SQLAlchemy ORM:** https://docs.sqlalchemy.org/
- **OpenAI API:** https://platform.openai.com/docs/
- **Chart.js:** https://www.chartjs.org/

---

## 👤 Author

**Kirti Upadhyay**
- Email: ukirti1911@gmail.com
- GitHub: [@kirtiu](https://github.com/kirtiu)

---

## ⭐ Show Your Support

If you found this project helpful, please give it a ⭐ on GitHub!

---

**Built with ❤️ using Flask, OpenAI, and Claude AI**
