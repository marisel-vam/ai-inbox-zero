# 🚀 Quick Start Guide - AI Inbox Zero Enterprise

Get up and running in **5 minutes**!

---

## ⚡ Prerequisites

- Python 3.8 or higher
- Gmail account
- Groq API account (free tier available)

---

## 📦 Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Step 2: Get API Keys

### **Groq API Key**

1. Visit https://console.groq.com
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

### **Gmail API Credentials**

1. Go to https://console.cloud.google.com
2. Create a new project (or select existing)
3. Enable Gmail API:
   - Go to "APIs & Services" > "Enable APIs and Services"
   - Search for "Gmail API"
   - Click "Enable"
4. Create OAuth credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app"
   - Download the credentials
   - Rename to `credentials.json` and place in project root

---

## ⚙️ Step 3: Configure Environment

Create a `.env` file in the project root:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here

# Optional (with defaults)
FLASK_SECRET_KEY=your-secret-key-here
USER_NAME=Your Name
DATABASE_PATH=inbox_zero.db
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
MAX_EMAILS=20
```

---

## 🚀 Step 4: Run the Application

```bash
python enterprise_app.py
```

You should see:

```
======================================================================
AI INBOX ZERO - ENTERPRISE EDITION
======================================================================
Flask Debug Mode: False
Host: 127.0.0.1
Port: 5000
Database: inbox_zero.db
Max Emails: 20
AI Model: llama-3.3-70b-versatile
...
✅ All services initialized successfully
🌐 Starting server on 127.0.0.1:5000
```

---

## 🌐 Step 5: Access the Application

Open your browser and navigate to:

```
http://localhost:5000
```

**First time only:** You'll be redirected to Gmail OAuth consent screen. Grant the required permissions.

---

## 🎯 Step 6: Scan Your Inbox

1. Click the **"Scan Inbox"** button in the header
2. Watch the real-time progress updates
3. View your categorized emails with AI-generated replies
4. Take actions: Send, Archive, or Delete

---

## 🎨 Explore the Features

### **Dashboard**
- View email statistics
- See category breakdown
- Track time saved
- Quick access to recent emails

### **Emails**
- Filter by category (Important, Personal, Newsletter, Spam)
- Filter by priority (High, Medium, Low)
- Search emails by sender or subject
- View AI-generated replies
- Take quick actions

### **Auto-Pilot**
- Configure automated email management
- Auto-archive newsletters
- Auto-delete spam
- Auto-reply to important emails (optional)

### **Settings**
- Customize your name for email signatures
- Adjust max emails per scan
- Enable/disable auto-draft creation

---

## 💡 Tips for First Use

1. **Start Small**: Begin with 10-20 emails on your first scan
2. **Review AI Replies**: Check AI-generated replies before sending
3. **Use Auto-Pilot Carefully**: Test with auto-archive first before enabling auto-reply
4. **Monitor Analytics**: Check the analytics view to see email patterns
5. **Customize Settings**: Adjust preferences to match your workflow

---

## 🔧 Troubleshooting

### **"GROQ_API_KEY not found"**
- Ensure `.env` file exists in project root
- Verify the key is correctly set without quotes
- Restart the application

### **"credentials.json not found"**
- Download from Google Cloud Console
- Ensure file is named exactly `credentials.json`
- Place in project root directory

### **"Port 5000 already in use"**
- Change port in `.env`:
  ```env
  FLASK_PORT=8000
  ```
- Or kill the process using port 5000

### **Gmail Authentication Failed**
1. Delete `token.json` file
2. Restart the application
3. Complete OAuth flow again

### **WebSocket Connection Error**
- Check browser console for details
- Ensure no proxy/firewall blocking WebSockets
- Try refreshing the page

---

## 🎓 Next Steps

1. **Customize AI Behavior**: Edit prompts in `ai_agent.py`
2. **Adjust Rate Limits**: Modify settings in `config.py`
3. **Explore Analytics**: View trends and insights
4. **Set Up Auto-Pilot**: Automate routine email management
5. **Configure Preferences**: Tailor the app to your needs

---

## 📚 Useful Commands

### **Start Application**
```bash
python enterprise_app.py
```

### **Check Configuration**
```bash
python config.py
```

### **Run Tests** (if available)
```bash
pytest tests/
```

### **Format Code**
```bash
black .
```

### **Lint Code**
```bash
flake8 .
```

---

## 🆘 Need Help?

- Check `ENTERPRISE_README.md` for detailed documentation
- Review `enterprise_inbox.log` for error details
- Inspect browser console for frontend errors
- Verify all dependencies are installed: `pip list`

---

## ✅ Verification Checklist

Before reporting issues, ensure:

- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with `GROQ_API_KEY`
- [ ] `credentials.json` downloaded and placed in root
- [ ] Gmail API enabled in Google Cloud Console
- [ ] Port 5000 (or custom) is available
- [ ] Internet connection active

---

## 🎉 Success!

If you see the dashboard with email statistics, you're all set!

**Happy email management! 📧✨**

---

## 📊 Typical First Scan Timeline

- **Authentication**: 30 seconds (first time only)
- **Fetching 20 emails**: 2-5 seconds
- **AI Analysis**: 10-20 seconds (parallel processing)
- **Draft Creation**: 5-10 seconds
- **Total**: ~1 minute for first scan

---

## 🔐 Security Notes

- Never commit `.env` file to version control
- Keep `token.json` private
- Rotate API keys periodically
- Use strong `FLASK_SECRET_KEY` in production
- Enable 2FA on your Gmail account

---

**Ready to achieve Inbox Zero? Let's go! 🚀**
