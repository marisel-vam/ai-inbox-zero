"""
PREMIUM AI INBOX ZERO - Beautiful UI + Smart AI
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template_string, redirect, url_for, session
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')

# Storage
EMAIL_CACHE = {}
CACHE_FILE = 'email_cache.json'

gmail_service = GmailService()
email_analyzer = EmailAnalyzer()

def load_cache():
    global EMAIL_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                EMAIL_CACHE = json.load(f)
        except:
            EMAIL_CACHE = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMAIL_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Cache save error: {e}")

load_cache()

# PREMIUM HTML TEMPLATE
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Inbox Zero - Your Intelligent Email Assistant</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #dc2626;
            --primary-dark: #991b1b;
            --primary-light: #fef2f2;
            --secondary: #0ea5e9;
            --success: #10b981;
            --warning: #f59e0b;
            --bg: #fafafa;
            --card: #ffffff;
            --text: #1f2937;
            --text-light: #6b7280;
            --border: #e5e7eb;
            --shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            --shadow-lg: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #fef2f2 0%, #fff 50%, #f0f9ff 100%);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }

        /* Navbar */
        .navbar {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border);
            padding: 1rem 0;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .navbar-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 1.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .nav-actions {
            display: flex;
            gap: 0.75rem;
            align-items: center;
        }

        .btn {
            padding: 0.625rem 1.25rem;
            border-radius: 0.75rem;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.875rem;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
            border: none;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(220, 38, 38, 0.4);
        }

        .btn-secondary {
            background: white;
            color: var(--text);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: var(--bg);
            border-color: var(--primary);
        }

        .btn-danger {
            background: white;
            color: var(--primary);
            border: 1px solid #fecaca;
        }

        .btn-danger:hover {
            background: var(--primary-light);
        }

        /* Container */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        /* Hero Section */
        .hero {
            text-align: center;
            padding: 3rem 0;
            animation: fadeIn 0.6s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hero-title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            font-size: 1.25rem;
            color: var(--text-light);
            margin-bottom: 2rem;
            font-weight: 400;
        }

        /* Stats Dashboard */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
            animation: slideUp 0.6s ease-out 0.2s both;
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stat-card {
            background: var(--card);
            padding: 2rem;
            border-radius: 1.25rem;
            border: 1px solid var(--border);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            transform: scaleX(0);
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow);
            border-color: var(--primary);
        }

        .stat-card:hover::before {
            transform: scaleX(1);
        }

        .stat-icon {
            width: 3rem;
            height: 3rem;
            border-radius: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }

        .stat-icon.primary { background: var(--primary-light); }
        .stat-icon.success { background: #d1fae5; }
        .stat-icon.warning { background: #fef3c7; }
        .stat-icon.info { background: #dbeafe; }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--text);
            line-height: 1;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: var(--text-light);
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Email Cards */
        .emails-section {
            animation: slideUp 0.6s ease-out 0.4s both;
        }

        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }

        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--text);
        }

        .email-grid {
            display: grid;
            gap: 1.5rem;
        }

        .email-card {
            background: var(--card);
            border-radius: 1.25rem;
            padding: 2rem;
            border: 1px solid var(--border);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .email-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, var(--primary), var(--secondary));
            transform: scaleY(0);
            transition: transform 0.3s;
        }

        .email-card:hover {
            transform: translateX(5px);
            box-shadow: var(--shadow);
            border-color: var(--primary);
        }

        .email-card:hover::before {
            transform: scaleY(1);
        }

        .email-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            gap: 1rem;
        }

        .email-meta {
            flex: 1;
        }

        .sender {
            color: var(--primary);
            font-weight: 600;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .subject {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.75rem;
            line-height: 1.4;
        }

        .badge {
            padding: 0.375rem 0.875rem;
            border-radius: 0.75rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            white-space: nowrap;
        }

        .badge-Important { 
            background: linear-gradient(135deg, #fee2e2, #fecaca);
            color: var(--primary-dark);
            border: 1px solid #fca5a5;
        }
        .badge-Newsletter { 
            background: linear-gradient(135deg, #d1fae5, #a7f3d0);
            color: #065f46;
            border: 1px solid #6ee7b7;
        }
        .badge-Personal { 
            background: linear-gradient(135deg, #dbeafe, #bfdbfe);
            color: #1e40af;
            border: 1px solid #93c5fd;
        }
        .badge-Spam { 
            background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
            color: #4b5563;
            border: 1px solid #d1d5db;
        }

        .ai-response {
            background: linear-gradient(135deg, #fafafa, #f3f4f6);
            border-radius: 1rem;
            padding: 1.5rem;
            margin: 1.5rem 0;
            border-left: 4px solid var(--primary);
            position: relative;
        }

        .ai-response::before {
            content: '🤖';
            position: absolute;
            top: -12px;
            left: 16px;
            background: white;
            padding: 0 8px;
            font-size: 1.25rem;
        }

        .ai-label {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.75rem;
        }

        .ai-text {
            color: var(--text);
            line-height: 1.8;
            white-space: pre-wrap;
            font-size: 0.9375rem;
        }

        .email-actions {
            display: flex;
            gap: 0.75rem;
            flex-wrap: wrap;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border);
        }

        /* Loading States */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(5px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            animation: fadeIn 0.3s;
        }

        .loading-content {
            text-align: center;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin: 0 auto 1.5rem;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 0.5rem;
        }

        .loading-subtext {
            color: var(--text-light);
            font-size: 0.875rem;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 5rem 2rem;
            animation: fadeIn 0.6s ease-out;
        }

        .empty-icon {
            font-size: 5rem;
            margin-bottom: 1.5rem;
            opacity: 0.5;
        }

        .empty-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1rem;
            color: var(--text);
        }

        .empty-text {
            font-size: 1.125rem;
            color: var(--text-light);
        }

        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: white;
            padding: 1rem 1.5rem;
            border-radius: 1rem;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 1rem;
            animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: 1001;
        }

        @keyframes slideInRight {
            from { transform: translateX(400px); }
            to { transform: translateX(0); }
        }

        .toast-success { border-left: 4px solid var(--success); }
        .toast-error { border-left: 4px solid var(--primary); }
        .toast-info { border-left: 4px solid var(--secondary); }

        /* Responsive */
        @media (max-width: 768px) {
            .hero-title { font-size: 2rem; }
            .hero-subtitle { font-size: 1rem; }
            .stats-grid { grid-template-columns: 1fr 1fr; }
            .navbar-content { flex-direction: column; gap: 1rem; }
            .nav-actions { width: 100%; justify-content: center; }
        }

        /* Utilities */
        .pulse {
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar">
        <div class="navbar-content">
            <div class="logo">
                <span>⚡</span>
                <span>AI Inbox Zero</span>
            </div>
            <div class="nav-actions">
                <a href="/scan" class="btn btn-primary">
                    <span>🔄</span>
                    <span>Scan Inbox</span>
                </a>
                <a href="/clear" class="btn btn-secondary">
                    <span>🗑️</span>
                    <span>Clear</span>
                </a>
                <a href="/logout" class="btn btn-danger">
                    <span>👋</span>
                    <span>Logout</span>
                </a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container">
        {% if scanning %}
        <div class="loading-overlay">
            <div class="loading-content">
                <div class="spinner"></div>
                <div class="loading-text">Analyzing Your Emails</div>
                <div class="loading-subtext">AI is processing {{ total_emails }} emails in parallel...</div>
            </div>
        </div>
        {% endif %}

        <!-- Hero Section -->
        <div class="hero">
            <h1 class="hero-title">Your Intelligent Email Assistant</h1>
            <p class="hero-subtitle">AI-powered inbox management that actually works</p>
        </div>

        <!-- Stats Dashboard -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon primary">📧</div>
                <div class="stat-value">{{ stats.total }}</div>
                <div class="stat-label">Total Emails</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon primary">⚠️</div>
                <div class="stat-value">{{ stats.important }}</div>
                <div class="stat-label">Important</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon info">👤</div>
                <div class="stat-value">{{ stats.personal }}</div>
                <div class="stat-label">Personal</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon success">📰</div>
                <div class="stat-value">{{ stats.newsletter }}</div>
                <div class="stat-label">Newsletters</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon warning">🚫</div>
                <div class="stat-value">{{ stats.spam }}</div>
                <div class="stat-label">Spam</div>
            </div>
        </div>

        <!-- Emails Section -->
        <div class="emails-section">
            {% if not emails %}
            <div class="empty-state">
                <div class="empty-icon">✨</div>
                <h2 class="empty-title">Inbox Zero Achieved!</h2>
                <p class="empty-text">You're all caught up. Time to relax! 🎉</p>
            </div>
            {% else %}
            <div class="section-header">
                <h2 class="section-title">📬 Recent Emails ({{ emails|length }})</h2>
            </div>
            <div class="email-grid">
                {% for email in emails %}
                <div class="email-card">
                    <div class="email-header">
                        <div class="email-meta">
                            <div class="sender">
                                <span>👤</span>
                                <span>{{ email.sender[:50] }}</span>
                            </div>
                            <h3 class="subject">{{ email.subject }}</h3>
                        </div>
                        <span class="badge badge-{{ email.category }}">{{ email.category }}</span>
                    </div>

                    {% if email.reply and email.reply != "No reply needed" %}
                    <div class="ai-response">
                        <div class="ai-label">AI-Generated Reply</div>
                        <div class="ai-text">{{ email.reply }}</div>
                    </div>
                    {% endif %}

                    <div class="email-actions">
                        {% if email.reply and email.reply != "No reply needed" %}
                        <a href="/send/{{ email.id }}" class="btn btn-primary">
                            <span>🚀</span>
                            <span>Send Reply</span>
                        </a>
                        {% endif %}
                        <a href="/archive/{{ email.id }}" class="btn btn-secondary">
                            <span>📦</span>
                            <span>Archive</span>
                        </a>
                        <a href="/delete/{{ email.id }}" class="btn btn-secondary">
                            <span>🗑️</span>
                            <span>Delete</span>
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
    </div>

    {% if success_message %}
    <div class="toast toast-success">
        <span style="font-size: 1.5rem;">✅</span>
        <span style="font-weight: 600;">{{ success_message }}</span>
    </div>
    <script>
        setTimeout(() => {
            document.querySelector('.toast').style.animation = 'slideInRight 0.3s reverse';
            setTimeout(() => document.querySelector('.toast').remove(), 300);
        }, 3000);
    </script>
    {% endif %}
</body>
</html>
"""

def process_email(email):
    """Process email with enhanced AI"""
    email_id = email['id']
    
    if email_id in EMAIL_CACHE:
        cached = EMAIL_CACHE[email_id]
        return {
            'id': email_id,
            'sender': email['sender'],
            'subject': email['subject'],
            'category': cached.get('category', 'Unknown'),
            'reply': cached.get('reply', 'No reply needed'),
            'cached': True
        }
    
    try:
        logger.info(f"⚡ Analyzing: {email['subject'][:50]}")
        ai_result = email_analyzer.analyze_email(
            email['sender'],
            email['subject'],
            email.get('snippet', '')
        )
        
        EMAIL_CACHE[email_id] = {
            'category': ai_result.get('category', 'Unknown'),
            'reply': ai_result.get('reply', 'No reply needed'),
            'sender': email['sender'],
            'subject': email['subject'],
            'timestamp': datetime.now().isoformat()
        }
        
        if ai_result.get('needs_reply'):
            try:
                gmail_service.create_draft_reply(
                    email['sender'],
                    email['subject'],
                    ai_result['reply']
                )
            except:
                pass
        
        return {
            'id': email_id,
            'sender': email['sender'],
            'subject': email['subject'],
            'category': ai_result.get('category', 'Unknown'),
            'reply': ai_result.get('reply', 'No reply needed'),
            'cached': False
        }
    except Exception as e:
        logger.error(f"Error processing email: {e}")
        return None

@app.route('/')
def home():
    emails = []
    stats = {'total': 0, 'important': 0, 'personal': 0, 'newsletter': 0, 'spam': 0}
    
    for email_id, data in list(EMAIL_CACHE.items())[:50]:
        emails.append({
            'id': email_id,
            'sender': data['sender'],
            'subject': data['subject'],
            'category': data['category'],
            'reply': data['reply']
        })
        stats['total'] += 1
        cat = data['category'].lower()
        if cat in stats:
            stats[cat] += 1
    
    success = session.pop('success_message', None)
    return render_template_string(
        HTML, 
        emails=emails, 
        stats=stats, 
        scanning=False,
        success_message=success
    )

@app.route('/scan')
def scan():
    logger.info("🚀 Starting premium scan...")
    raw_emails = gmail_service.fetch_unread_emails(max_results=20)
    
    if not raw_emails:
        session['success_message'] = "No new emails to process!"
        return redirect(url_for('home'))
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_email, email) for email in raw_emails]
        for future in as_completed(futures):
            future.result()
    
    save_cache()
    session['success_message'] = f"Successfully processed {len(raw_emails)} emails!"
    return redirect(url_for('home'))

@app.route('/send/<email_id>')
def send_reply(email_id):
    if email_id in EMAIL_CACHE:
        data = EMAIL_CACHE[email_id]
        try:
            gmail_service.send_email_reply(data['sender'], data['subject'], data['reply'])
            session['success_message'] = "Reply sent successfully!"
        except Exception as e:
            logger.error(f"Send error: {e}")
    return redirect(url_for('home'))

@app.route('/archive/<email_id>')
def archive(email_id):
    try:
        gmail_service.archive_email(email_id)
        if email_id in EMAIL_CACHE:
            del EMAIL_CACHE[email_id]
        save_cache()
        session['success_message'] = "Email archived!"
    except Exception as e:
        logger.error(f"Archive error: {e}")
    return redirect(url_for('home'))

@app.route('/delete/<email_id>')
def delete(email_id):
    try:
        gmail_service.delete_email(email_id)
        if email_id in EMAIL_CACHE:
            del EMAIL_CACHE[email_id]
        save_cache()
        session['success_message'] = "Email deleted!"
    except Exception as e:
        logger.error(f"Delete error: {e}")
    return redirect(url_for('home'))

@app.route('/clear')
def clear():
    global EMAIL_CACHE
    EMAIL_CACHE = {}
    save_cache()
    session['success_message'] = "Cache cleared!"
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    """Logout and clear credentials"""
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
        session['success_message'] = "Logged out successfully!"
        logger.info("User logged out")
    except Exception as e:
        logger.error(f"Logout error: {e}")
    return redirect(url_for('home'))

if __name__ == '__main__':
    logger.info("🚀 Starting AI Inbox Zero...")
    app.run(debug=True, port=5000)