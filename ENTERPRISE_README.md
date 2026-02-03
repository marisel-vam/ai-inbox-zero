# AI Inbox Zero - Enterprise Edition 🚀

> **Modern, production-grade email management powered by AI**

A complete rewrite of AI Inbox Zero with an enterprise-grade user interface, advanced features, and rock-solid architecture built on FastAPI and modern web technologies.

---

## ✨ What's New in Enterprise Edition

### 🎨 **Enterprise-Grade UI**
- **Modern Design System**: Professional interface with Inter font family, smooth animations, and polished micro-interactions
- **Sidebar Navigation**: Intuitive navigation with Dashboard, Emails, Analytics, Auto-Pilot, and Settings
- **Responsive Layout**: Works seamlessly on desktop, tablet, and mobile devices
- **Real-time Updates**: WebSocket integration for live status updates during email processing
- **Toast Notifications**: Non-intrusive feedback system for all user actions

### 🔥 **Advanced Features**

#### **Smart Dashboard**
- Real-time statistics display
- Category breakdown (Important, Personal, Newsletter, Spam)
- Priority insights (High, Medium, Low)
- Time saved calculation
- Recent emails quick view

#### **Powerful Email Management**
- Advanced filtering by category, priority, and reply status
- Real-time search across sender and subject
- Batch operations support
- Individual email actions (Send, Archive, Delete)
- AI-generated reply preview
- Email metadata badges

#### **Auto-Pilot Mode**
- Automated email management based on AI categorization
- Configurable actions:
  - Auto-archive newsletters
  - Auto-delete spam
  - Auto-reply to important emails (with caution mode)
- One-click execution with detailed feedback

#### **Analytics Dashboard**
- 30-day email processing trends
- Category distribution visualization
- Time saved metrics
- Processing history

#### **Settings & Preferences**
- Customizable user name for email signatures
- Adjustable max emails per scan (10-100)
- Auto-draft toggle
- Persistent preferences stored in database

### 🏗️ **Technical Excellence**

#### **Backend (FastAPI)**
- **Async/Await**: Modern asynchronous Python for optimal performance
- **RESTful API**: Clean, documented endpoints
- **WebSocket Support**: Real-time bidirectional communication
- **Connection Manager**: Handles multiple WebSocket clients
- **Background Tasks**: Non-blocking email processing
- **ThreadPoolExecutor**: Parallel AI analysis for speed
- **Comprehensive Error Handling**: Graceful degradation and detailed logging
- **Health Check Endpoint**: `/api/health` for monitoring

#### **Database Layer**
- **SQLite with WAL mode**: Enhanced concurrency
- **Connection pooling**: Efficient resource management
- **Retry logic**: Handles database locks gracefully
- **Indexed queries**: Fast data retrieval
- **Analytics tracking**: Historical data for insights

#### **AI Integration**
- **Groq API**: Fast LLM inference with Llama 3.3 70B
- **Rate limiting**: Prevents API throttling
- **Fallback mechanisms**: Continues working if AI fails
- **Enhanced prompts**: Better categorization and reply generation
- **Context-aware replies**: Uses email content for intelligent responses

---

## 📋 Full Feature List

### ✅ **Core Functionality** (100% Feature Parity)
- [x] Gmail API integration
- [x] OAuth2 authentication
- [x] Fetch unread emails
- [x] AI-powered email analysis and categorization
- [x] Priority detection
- [x] Intelligent reply generation
- [x] Draft creation in Gmail
- [x] Send email replies
- [x] Archive emails
- [x] Delete emails
- [x] Mark as read
- [x] Email caching
- [x] Database persistence
- [x] Analytics tracking

### 🎯 **New Enterprise Features**
- [x] Modern single-page application (SPA)
- [x] WebSocket real-time updates
- [x] Advanced search and filtering
- [x] Batch operations API
- [x] Auto-pilot automation mode
- [x] Customizable preferences
- [x] Toast notification system
- [x] Loading states and progress indicators
- [x] Responsive mobile layout
- [x] Health check endpoint
- [x] Comprehensive error handling
- [x] Connection manager for WebSockets
- [x] Background task processing
- [x] Category and priority badges
- [x] Time saved calculations

---

## 🚀 Getting Started

### Prerequisites

```bash
Python 3.8+
Gmail API credentials
Groq API key
```

### Installation

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables** (`.env`):
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   FLASK_SECRET_KEY=your_secret_key_here
   USER_NAME=Your Name
   DATABASE_PATH=inbox_zero.db
   ```

3. **Set up Gmail credentials**:
   - Download `credentials.json` from Google Cloud Console
   - Place it in the project root

### Running the Enterprise Edition

```bash
python enterprise_app.py
```

The application will start on `http://127.0.0.1:5000`

Access the modern UI at: `http://127.0.0.1:5000/`

---

## 📁 Project Structure

```
ai-inbox-zero/
├── enterprise_app.py          # Main FastAPI application
├── enterprise_ui.html          # Modern SPA frontend
├── gmail_service.py            # Gmail API wrapper
├── ai_agent.py                 # Groq AI integration
├── db_manager.py               # Database layer
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── credentials.json            # Gmail OAuth credentials
├── token.json                  # Gmail OAuth token (auto-generated)
├── inbox_zero.db              # SQLite database (auto-created)
└── enterprise_inbox.log        # Application logs
```

---

## 🔌 API Endpoints

### **Core Endpoints**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve main UI |
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Dashboard statistics |
| GET | `/api/emails` | List emails with filters |
| POST | `/api/scan` | Scan inbox and process emails |
| POST | `/api/auto-pilot` | Run auto-pilot automation |
| GET | `/api/analytics` | Get analytics data |
| GET | `/api/preferences` | Get user preferences |
| POST | `/api/preferences` | Save user preferences |
| POST | `/api/logout` | Logout and clear credentials |

### **Email Actions**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/email/{id}/send` | Send reply |
| POST | `/api/email/{id}/archive` | Archive email |
| POST | `/api/email/{id}/delete` | Delete email |
| POST | `/api/email/{id}/mark-read` | Mark as read |
| POST | `/api/batch` | Batch operations |

### **Real-time**

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/ws` | WebSocket for real-time updates |

---

## 🎨 UI Components

### **Views**
- **Dashboard**: Overview with stats and recent emails
- **Emails**: Full email list with advanced filtering
- **Analytics**: Visual insights and trends
- **Auto-Pilot**: Automation configuration
- **Settings**: User preferences and configuration

### **Features**
- Sidebar navigation with active state
- Search bar with real-time filtering
- Stat cards with hover effects
- Email cards with gradient accents
- Badge system for categories and priorities
- AI response preview boxes
- Action buttons with icons
- Toast notifications
- Modal dialogs
- Loading spinners
- Progress bars

---

## 🔐 Security

- OAuth2 authentication with Gmail
- Secure token storage
- Environment variable configuration
- No hardcoded credentials
- Session management
- HTTPS ready (configure reverse proxy)

---

## ⚙️ Configuration

All settings can be configured via `.env` file or `config.py`:

```python
FLASK_SECRET_KEY          # Session secret key
GROQ_API_KEY             # Groq API key for AI
DATABASE_PATH            # SQLite database path
USER_NAME                # Your name for email signatures
MAX_EMAILS_PER_SCAN      # Default: 20
AI_MODEL                 # Default: llama-3.3-70b-versatile
ENABLE_ANALYTICS         # Default: True
ENABLE_AUTO_DRAFT        # Default: True
```

---

## 🧪 Testing

Run the application in development mode:

```bash
python enterprise_app.py
```

Check health status:
```bash
curl http://localhost:5000/api/health
```

---

## 📊 Performance

- **Parallel Processing**: Up to 10 concurrent email analyses
- **WebSocket Updates**: Real-time progress tracking
- **Database Optimization**: WAL mode, indexed queries, connection pooling
- **Caching**: Reduces redundant API calls
- **Rate Limiting**: Prevents API throttling
- **Async Architecture**: Non-blocking operations

---

## 🆚 Comparison with Original Apps

| Feature | premium_app.py | app.py | **Enterprise Edition** |
|---------|---------------|--------|----------------------|
| Framework | Flask | FastAPI + HTMX | **FastAPI + Modern JS** |
| UI Quality | Good | Basic | **Enterprise-grade** |
| Real-time Updates | ❌ | ❌ | **✅ WebSockets** |
| Search & Filters | Basic | Basic | **Advanced** |
| Auto-Pilot | ❌ | ❌ | **✅ Full Control** |
| Analytics | Basic | Good | **Enhanced** |
| Settings UI | ❌ | ❌ | **✅ Complete** |
| Database | JSON Cache | JSON Cache | **SQLite with persistence** |
| Mobile Responsive | Partial | Partial | **Fully Responsive** |
| Batch Operations | ❌ | ❌ | **✅ API Support** |
| Health Monitoring | ❌ | ❌ | **✅ Endpoint** |

---

## 🛠️ Troubleshooting

### Gmail Authentication Issues
1. Ensure `credentials.json` is present
2. Delete `token.json` and re-authenticate
3. Check Gmail API is enabled in Google Cloud Console

### Database Locked Errors
- Enterprise edition uses WAL mode and retry logic
- If issues persist, delete `inbox_zero.db` to reset

### WebSocket Connection Failed
- Check firewall settings
- Ensure port 5000 is accessible
- Review browser console for errors

### AI Analysis Errors
- Verify `GROQ_API_KEY` is set correctly
- Check API rate limits
- Review logs in `enterprise_inbox.log`

---

## 🚢 Production Deployment

### Using Uvicorn

```bash
uvicorn enterprise_app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker (Example)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "enterprise_app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Nginx Reverse Proxy

```nginx
location / {
    proxy_pass http://localhost:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 📈 Roadmap

- [ ] Multi-account support
- [ ] Email templates
- [ ] Scheduled auto-pilot
- [ ] Advanced analytics charts
- [ ] Export functionality
- [ ] Dark mode toggle
- [ ] Email threading view
- [ ] Attachment handling
- [ ] Custom AI models
- [ ] Plugin system

---

## 🤝 Contributing

This is an enterprise upgrade maintaining full feature parity with the original AI Inbox Zero while adding professional-grade UI and advanced features.

---

## 📝 License

Same as original AI Inbox Zero project.

---

## 🙏 Credits

Built on top of the excellent AI Inbox Zero project, enhanced with enterprise-grade architecture and modern UX patterns.

**Technologies Used:**
- FastAPI - Modern async web framework
- SQLite - Reliable embedded database
- Groq API - Fast LLM inference
- Gmail API - Email integration
- WebSockets - Real-time communication
- Inter Font - Professional typography
- Font Awesome - Icon library

---

## 📞 Support

For issues, questions, or contributions, please refer to the main project repository.

---

**Made with ❤️ for productive email management**
