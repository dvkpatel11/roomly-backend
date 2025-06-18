# 🏠 Roomly Backend API

> **Modern Household Management System for Roommates**

A comprehensive FastAPI backend powering the Roomly roommate management platform. Built with Python, FastAPI, and SQLAlchemy to handle everything from expense splitting to chore coordination.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg?style=flat&logo=FastAPI)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=flat&logo=python)](https://python.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red.svg?style=flat)](https://sqlalchemy.org)

## 🎯 **Core Features**

### 💰 **Financial Management**

- **Expense Tracking** - One-time expenses with receipt uploads and custom splitting
- **Recurring Bills** - Automated bill tracking with payment reminders
- **Payment Dashboard** - Real-time payment status and debt tracking
- **Split Calculations** - Equal, usage-based, and custom ratio splitting

### 📋 **Task & Chore Management**

- **Rotating Schedules** - Fair chore distribution with automated rotation
- **Point System** - Gamified accountability with task completion scoring
- **Photo Proof** - Visual confirmation of completed tasks
- **Smart Reminders** - Automated notifications for overdue tasks

### 📅 **Calendar & Events**

- **Shared Calendar** - Household events with color-coded categories
- **Event Planning** - House parties, maintenance, and group activities
- **RSVP System** - Guest management with head counts and dietary restrictions
- **Schedule Coordination** - Optional personal calendar sharing

### 🏡 **Household Operations**

- **Guest Management** - Registration, approval workflow, and overnight tracking
- **Communication Hub** - Announcements, polls, and house decisions
- **Dashboard Analytics** - Household health scores and activity feeds
- **Smart Notifications** - Customizable alerts via email, push, and in-app

### 🛒 **Simple Resource Management**

- **Shopping Lists** - Collaborative grocery coordination
- **Task Assignment** - Designated shoppers and cost tracking

## 🚀 **Quick Start**

### Prerequisites

- Python 3.8 or higher
- pip package manager
- Git

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd roomly-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 🌐 **Access Points**

- **API Documentation**: http://localhost:8000/docs
- **Interactive API**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📁 **Project Structure**

```
roomly-backend/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # Database connection and session management
│   ├── models/                 # SQLAlchemy data models
│   │   ├── user.py            # User accounts & authentication
│   │   ├── household.py       # Household management
│   │   ├── expense.py         # One-time expenses
│   │   ├── bill.py            # Recurring bills & payments
│   │   ├── task.py            # Tasks & chores with point system
│   │   ├── event.py           # Events & calendar items
│   │   ├── guest.py           # Guest management & tracking
│   │   ├── announcement.py    # House bulletin board
│   │   ├── poll.py            # House decision voting
│   │   ├── notification.py    # Smart notifications
│   │   ├── rsvp.py            # Event RSVP tracking
│   │   ├── user_schedule.py   # Personal calendar sharing
│   │   └── shopping_list.py   # Grocery coordination
│   ├── routers/               # API route handlers
│   │   ├── auth.py           # Authentication & user management
│   │   ├── dashboard.py      # Dashboard data aggregation
│   │   ├── expenses.py       # Expense management
│   │   ├── bills.py          # Recurring bill management
│   │   ├── tasks.py          # Task & chore coordination
│   │   ├── calendar.py       # Calendar & scheduling
│   │   ├── guests.py         # Guest registration & approval
│   │   ├── communications.py # Announcements & polls
│   │   ├── notifications.py  # Notification management
│   │   ├── shopping.py       # Shopping list coordination
│   │   └── households.py     # Household settings
│   ├── schemas/              # Pydantic models for API
│   │   ├── user.py          # User data validation
│   │   ├── expense.py       # Expense schemas
│   │   ├── bill.py          # Bill schemas
│   │   ├── task.py          # Task schemas
│   │   └── dashboard.py     # Dashboard response models
│   ├── services/             # Business logic layer
│   │   ├── dashboard_service.py      # Dashboard data aggregation
│   │   ├── expense_service.py        # Expense splitting logic
│   │   ├── billing_service.py        # Recurring bill automation
│   │   ├── task_service.py           # Task rotation & scoring
│   │   ├── notification_service.py   # Smart notification logic
│   │   ├── scheduling_service.py     # Calendar conflict resolution
│   │   ├── communication_service.py  # Announcement & poll logic
│   │   ├── guest_service.py          # Guest approval workflow
│   │   └── shopping_service.py       # Shopping coordination
│   └── utils/                # Utility functions
│       ├── security.py       # JWT & password hashing
│       ├── helpers.py        # Common utilities
│       └── email.py          # Email notification utilities
├── tests/                    # Test suite
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
└── README.md                # This file
```

## 🔧 **Configuration**

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=sqlite:///./roomly.db

# Security
SECRET_KEY=your-super-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Email (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Development
DEBUG=True
```

### Database Configuration

**SQLite (Development)**

```python
DATABASE_URL=sqlite:///./roomly.db
```

**PostgreSQL (Production)**

```python
DATABASE_URL=postgresql://user:password@localhost/roomly
```

## 📚 **API Documentation**

### Authentication

```http
POST /api/auth/login
POST /api/auth/register
```

### Dashboard

```http
GET /api/dashboard/summary          # Household overview
GET /api/dashboard/financial-overview
GET /api/dashboard/task-summary
```

### Expenses & Bills

```http
# One-time Expenses
POST /api/expenses/                 # Create expense
GET /api/expenses/                  # List expenses
PUT /api/expenses/{id}              # Update expense
DELETE /api/expenses/{id}           # Delete expense

# Recurring Bills
POST /api/bills/                    # Create recurring bill
GET /api/bills/upcoming             # Get upcoming bills
POST /api/bills/{id}/payments       # Record payment
```

### Tasks & Chores

```http
POST /api/tasks/                    # Create task
GET /api/tasks/                     # List tasks
PUT /api/tasks/{id}/complete        # Mark complete
GET /api/tasks/leaderboard          # Point standings
```

### Events & Calendar

```http
POST /api/calendar/events           # Create event
GET /api/calendar/events            # List events
POST /api/calendar/events/{id}/rsvp # RSVP to event
```

### Guest Management

```http
POST /api/guests/                   # Register guest
GET /api/guests/pending-approval    # Pending approvals
PUT /api/guests/{id}/approve        # Approve guest
```

### Communications

```http
POST /api/communications/announcements  # Post announcement
GET /api/communications/announcements   # Get announcements
POST /api/communications/polls          # Create poll
POST /api/communications/polls/{id}/vote # Vote on poll
```

For complete API documentation, visit `/docs` when the server is running.

## 🧪 **Testing**

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_expenses.py -v
```

## 🛠️ **Development Workflow**

### Adding New Features

1. **Create the Model** (`app/models/`)

   - Define SQLAlchemy model with relationships
   - Add to `models/__init__.py`

2. **Create Schemas** (`app/schemas/`)

   - Define Pydantic models for validation
   - Include Create, Update, and Response schemas

3. **Create Router** (`app/routers/`)

   - Define API endpoints
   - Add to `main.py` router includes

4. **Create Service** (`app/services/`)

   - Implement business logic
   - Handle complex operations and calculations

5. **Write Tests** (`tests/`)
   - Unit tests for services
   - Integration tests for endpoints

### Database Migrations

```bash
# Install Alembic (included in requirements.txt)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new feature"

# Apply migration
alembic upgrade head
```

### Code Style

```bash
# Install development tools
pip install black isort flake8

# Format code
black app/
isort app/

# Check style
flake8 app/
```

## 🔒 **Security Features**

- **JWT Authentication** - Secure token-based authentication
- **Password Hashing** - bcrypt for secure password storage
- **Input Validation** - Pydantic schemas prevent injection attacks
- **CORS Configuration** - Controlled cross-origin requests
- **Rate Limiting** - Built-in FastAPI rate limiting (configurable)

## 🚀 **Deployment**

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Environment

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UnicornWorker --bind 0.0.0.0:8000
```

## 📊 **Performance Considerations**

- **Database Indexing** - Optimized queries on frequently accessed fields
- **Connection Pooling** - SQLAlchemy connection pooling for scalability
- **Async Operations** - FastAPI async support for high concurrency
- **Caching Strategy** - Redis integration ready for session and data caching

## 🔮 **Roadmap**

### Phase 1: Core Features ✅

- [x] User authentication and households
- [x] Expense and bill management
- [x] Task coordination with point system
- [x] Basic dashboard and notifications

### Phase 2: Enhanced Features 🚧

- [ ] Advanced notification delivery (email, push)
- [ ] Calendar integration (Google Calendar, Apple Calendar)
- [ ] Payment app integration (Venmo, PayPal)
- [ ] Photo upload for receipts and task proof

### Phase 3: Advanced Features 📋

- [ ] Mobile app API optimization
- [ ] Advanced analytics and reporting
- [ ] Machine learning for spending insights
- [ ] Third-party integrations (smart home, IoT)

### Phase 4: Scale & Performance 🚀

- [ ] Multi-household support for property managers
- [ ] Advanced caching and performance optimization
- [ ] Microservices architecture consideration
- [ ] Real-time features with WebSockets

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup for Contributors

```bash
# Fork and clone your fork
git clone https://github.com/your-username/roomly-backend.git
cd roomly-backend

# Set up development environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Set up pre-commit hooks
pre-commit install

# Run tests to ensure everything works
pytest
```

## 📝 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💬 **Support**

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/your-username/roomly-backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/roomly-backend/discussions)

## 🙏 **Acknowledgments**

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [SQLAlchemy](https://sqlalchemy.org/) for powerful ORM capabilities
- [Pydantic](https://pydantic.dev/) for data validation
- [Uvicorn](https://uvicorn.org/) for ASGI server implementation

---

**Built with ❤️ for modern roommates who deserve better household management tools.**
