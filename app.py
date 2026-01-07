import os
import time
import logging
from flask import Flask, render_template_string, redirect, url_for, jsonify, request
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from db_manager import DatabaseManager
from fast_scan import FastEmailScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize services
gmail_service = GmailService()
email_analyzer = EmailAnalyzer()
db = DatabaseManager()
fast_scanner = FastEmailScanner(max_workers=10)  # Process 10 emails at once

# --- ENHANCED UI TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Inbox Zero</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #fdf2f2, #fff1f2, #ffffff);
            --card-bg: #ffffff;
            --border-color: #fecaca;
            --accent-primary: #dc2626;
            --accent-secondary: #991b1b;
            --text-main: #1f2937;
            --text-muted: #6b7280;
            --success: #059669;
            --danger: #dc2626;
            --shadow-color: rgba(220, 38, 38, 0.1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }

        .top-nav { 
            width: 100%; max-width: 1000px; 
            display: flex; justify-content: space-between; 
            align-items: center; margin-bottom: 20px; 
        }
        
        .stats-quick { 
            display: flex; gap: 15px; 
            font-size: 0.85rem; color: var(--text-muted); 
        }
        
        .stat-item { 
            background: white; padding: 8px 15px; 
            border-radius: 20px; border: 1px solid var(--border-color); 
        }
        
        .stat-number { 
            font-weight: 700; color: var(--accent-primary); 
            margin-right: 4px; 
        }
        
        .nav-actions { display: flex; gap: 10px; }
        
        .nav-btn { 
            color: var(--accent-primary); text-decoration: none; 
            font-size: 0.9rem; font-weight: 600; 
            border: 1px solid var(--border-color); 
            padding: 8px 18px; border-radius: 30px; 
            transition: 0.3s; background: white; 
        }
        
        .nav-btn:hover { 
            background: var(--accent-primary); 
            color: white; 
            box-shadow: 0 4px 12px var(--shadow-color); 
        }
        
        .btn-danger:hover { background: #7f1d1d; border-color: #7f1d1d; }
        
        header { text-align: center; margin-bottom: 40px; }
        
        h1 { 
            font-size: 3.5rem; margin: 0; 
            background: linear-gradient(to right, #dc2626, #b91c1c); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            font-weight: 800; letter-spacing: -1px; 
        }
        
        .subtitle { 
            color: var(--text-muted); 
            font-size: 1.1rem; margin-top: 10px; 
            font-weight: 500; 
        }
        
        .scan-btn { 
            margin-top: 30px; 
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); 
            color: white; border: none; 
            padding: 16px 50px; font-size: 1.2rem; 
            font-weight: 600; border-radius: 50px; 
            cursor: pointer; text-decoration: none; 
            box-shadow: 0 10px 25px var(--shadow-color); 
            transition: transform 0.2s, box-shadow 0.2s; 
            display: inline-block; 
        }
        
        .scan-btn:hover { 
            transform: translateY(-3px); 
            box-shadow: 0 15px 35px rgba(220, 38, 38, 0.25); 
        }
        
        .scan-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading { 
            text-align: center; 
            padding: 60px 20px; 
            color: var(--text-muted); 
        }
        
        .spinner {
            border: 3px solid #f3f4f6;
            border-top: 3px solid var(--accent-primary);
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .email-list { 
            width: 100%; max-width: 1000px; 
            display: grid; gap: 25px; 
        }
        
        .email-card { 
            background: var(--card-bg); 
            border: 1px solid var(--border-color); 
            border-radius: 20px; padding: 30px; 
            transition: transform 0.2s; 
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
        }
        
        .email-card:hover { 
            transform: translateY(-4px); 
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.05); 
            border-color: var(--accent-primary); 
        }
        
        .card-header { 
            display: flex; 
            justify-content: space-between; 
            align-items: flex-start; 
            margin-bottom: 20px; 
        }
        
        .sender { 
            font-size: 0.85rem; 
            color: var(--accent-secondary); 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            font-weight: 700; 
        }
        
        .subject { 
            font-size: 1.4rem; 
            margin: 5px 0; 
            font-weight: 600; 
            color: #111827; 
        }
        
        .badge { 
            padding: 6px 14px; 
            border-radius: 12px; 
            font-size: 0.7rem; 
            font-weight: 700; 
            text-transform: uppercase; 
        }
        
        .badge-Important { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        .badge-Newsletter { background: #d1fae5; color: #065f46; border: 1px solid #a7f3d0; }
        .badge-Personal { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
        .badge-Spam { background: #f3f4f6; color: #4b5563; border: 1px solid #e5e7eb; }
        
        .badge-High { background: #fee2e2; color: #991b1b; }
        .badge-Medium { background: #fef3c7; color: #92400e; }
        .badge-Low { background: #f3f4f6; color: #4b5563; }
        
        .ai-box { 
            background: #f9fafb; 
            border-radius: 12px; 
            padding: 20px; 
            border-left: 4px solid var(--accent-primary); 
        }
        
        .ai-reply { 
            font-family: 'Courier New', monospace; 
            color: #374151; 
            line-height: 1.6; 
            white-space: pre-wrap; 
            font-size: 0.95rem; 
        }
        
        .actions { 
            margin-top: 25px; 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            border-top: 1px solid #f3f4f6; 
            padding-top: 20px; 
        }
        
        .btn-group { display: flex; gap: 10px; flex-wrap: wrap; }
        
        .btn { 
            padding: 10px 20px; 
            border-radius: 12px; 
            font-weight: 600; 
            text-decoration: none; 
            transition: 0.2s; 
            cursor: pointer; 
            border: none; 
            font-size: 0.9rem;
        }
        
        .btn-send { 
            background: var(--accent-primary); 
            color: white; 
            box-shadow: 0 4px 6px var(--shadow-color); 
        }
        
        .btn-send:hover { 
            transform: scale(1.02); 
            background: var(--accent-secondary); 
        }
        
        .btn-archive { 
            background: white; 
            color: #4b5563; 
            border: 1px solid #d1d5db; 
        }
        
        .btn-archive:hover { 
            background: #f3f4f6; 
            border-color: #9ca3af; 
            color: #111827; 
        }
        
        .btn-delete { 
            background: white; 
            color: #dc2626; 
            border: 1px solid #fecaca; 
        }
        
        .btn-delete:hover { 
            background: #fef2f2; 
            border-color: #dc2626; 
        }
        
        .status-msg { 
            font-size: 0.9rem; 
            color: var(--success); 
            font-weight: 700; 
        }
        
        .cache-badge { 
            font-size: 0.7rem; 
            background: #e5e7eb; 
            padding: 3px 8px; 
            border-radius: 4px; 
            color: #6b7280; 
            font-weight: 600; 
        }
        
        .fallback-badge {
            font-size: 0.7rem;
            background: #fef3c7;
            padding: 3px 8px;
            border-radius: 4px;
            color: #92400e;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .empty-state { 
            text-align: center; 
            padding: 80px 20px; 
            color: var(--text-muted); 
        }
        
        .empty-state-icon { 
            font-size: 4rem; 
            margin-bottom: 20px; 
        }
        
        .error-message {
            background: #fef2f2;
            border: 1px solid #fecaca;
            color: #991b1b;
            padding: 20px;
            border-radius: 12px;
            margin: 20px auto;
            max-width: 600px;
            text-align: center;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 2.5rem; }
            .top-nav { flex-direction: column; gap: 15px; }
            .stats-quick { flex-wrap: wrap; justify-content: center; }
            .actions { flex-direction: column; gap: 15px; }
            .btn-group { width: 100%; justify-content: center; }
        }
    </style>
</head>
<body>
    <div class="top-nav">
        <div class="stats-quick">
            <div class="stat-item">
                <span class="stat-number">{{ stats.total or 0 }}</span>
                <span>Processed</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{{ stats.replies or 0 }}</span>
                <span>Sent</span>
            </div>
            <div class="stat-item">
                <span class="stat-number">{{ stats.archived or 0 }}</span>
                <span>Archived</span>
            </div>
        </div>
        <div class="nav-actions">
            <a href="/analytics" class="nav-btn">📊 Analytics</a>
            <a href="/clear_cache" class="nav-btn" onclick="return confirm('Clear all history?')">🧹 Clear History</a>
            <a href="/logout" class="nav-btn btn-danger" onclick="return confirm('Logout and clear credentials?')">Logout</a>
        </div>
    </div>

    <header>
        <h1>AI Inbox Zero</h1>
        <div class="subtitle">Intelligent Email Command Center</div>
        <button onclick="scanEmails()" class="scan-btn" id="scanBtn">⚡ Scan Inbox</button>
    </header>

    <div class="container">
        {% if error %}
        <div class="error-message">
            <strong>Error:</strong> {{ error }}
        </div>
        {% endif %}
        
        <div id="loadingDiv" class="loading" style="display: none;">
            <div class="spinner"></div>
            <p>Analyzing your emails with AI...</p>
        </div>
        
        {% if not emails and not error %}
        <div class="empty-state">
            <div class="empty-state-icon">✅</div>
            <h2>All Clear!</h2>
            <p style="font-size: 1.2rem; margin-top: 10px;">Inbox Zero achieved.</p>
        </div>
        {% endif %}
        
        <div class="email-list">
            {% for email in emails %}
            <div class="email-card" id="email-{{ email.id }}">
                <div class="card-header">
                    <div>
                        <div class="sender">{{ email.sender }}</div>
                        <h2 class="subject">{{ email.subject }}</h2>
                    </div>
                    <div style="display: flex; gap: 8px; flex-direction: column; align-items: flex-end;">
                        <span class="badge badge-{{ email.category }}">{{ email.category }}</span>
                        {% if email.priority %}
                        <span class="badge badge-{{ email.priority }}">{{ email.priority }}</span>
                        {% endif %}
                    </div>
                </div>
                
                <div class="ai-box">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 8px;">
                        <span style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">
                            {{ "No Reply Needed" if not email.needs_reply else "Suggested Reply" }}
                        </span>
                        <div>
                            {% if email.from_cache %}
                            <span class="cache-badge">Cached</span>
                            {% endif %}
                            {% if email.is_fallback %}
                            <span class="fallback-badge">Fallback</span>
                            {% endif %}
                        </div>
                    </div>
                    <div class="ai-reply">{{ email.reply }}</div>
                </div>

                <div class="actions">
                    <div class="btn-group">
                        <a href="/archive/{{ email.id }}" class="btn btn-archive" onclick="return confirm('Archive this email?')">📦 Archive</a>
                        <a href="/delete/{{ email.id }}" class="btn btn-delete" onclick="return confirm('Move to trash?')">🗑️ Delete</a>
                    </div>

                    {% if email.needs_reply %}
                        {% if email.sent %}
                            <span class="status-msg">✓ Sent!</span>
                        {% else %}
                            <a href="/send_reply/{{ email.id }}" class="btn btn-send" onclick="return confirm('Send this reply?')">🚀 Send Now</a>
                        {% endif %}
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function scanEmails() {
            const btn = document.getElementById('scanBtn');
            const loadingDiv = document.getElementById('loadingDiv');
            
            btn.disabled = true;
            btn.textContent = '⏳ Scanning...';
            loadingDiv.style.display = 'block';
            
            window.location.href = '/scan';
        }
    </script>
</body>
</html>
"""

ANALYTICS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics - AI Inbox Zero</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700&display=swap" rel="stylesheet">
    <style>
        /* Reuse same styles from main template */
        :root {
            --bg-gradient: linear-gradient(135deg, #fdf2f2, #fff1f2, #ffffff);
            --accent-primary: #dc2626;
            --text-main: #1f2937;
            --text-muted: #6b7280;
        }
        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            padding: 40px 20px;
        }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { 
            font-size: 2.5rem;
            background: linear-gradient(to right, #dc2626, #b91c1c);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 30px;
        }
        .back-btn {
            display: inline-block;
            color: var(--accent-primary);
            text-decoration: none;
            margin-bottom: 20px;
            font-weight: 600;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border: 1px solid #fecaca;
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--accent-primary);
        }
        .stat-label {
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-top: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-btn">← Back to Inbox</a>
        <h1>📊 Analytics Dashboard</h1>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.total or 0 }}</div>
                <div class="stat-label">Total Emails</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.important or 0 }}</div>
                <div class="stat-label">Important</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.personal or 0 }}</div>
                <div class="stat-label">Personal</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.newsletter or 0 }}</div>
                <div class="stat-label">Newsletters</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.replies or 0 }}</div>
                <div class="stat-label">Replies Sent</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ analytics.summary.archived or 0 }}</div>
                <div class="stat-label">Archived</div>
            </div>
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def home():
    """Home page showing processed emails"""
    try:
        emails = db.get_recent_emails(limit=50, include_deleted=False)
        
        # Format emails for template
        formatted_emails = []
        for email in emails:
            formatted_emails.append({
                'id': email['email_id'],
                'sender': email['sender'],
                'subject': email['subject'],
                'category': email['category'],
                'priority': email.get('priority', 'Medium'),
                'reply': email['clean_reply'] or 'No reply needed',
                'needs_reply': bool(email['needs_reply']),
                'sent': bool(email['sent']),
                'from_cache': True,  # All from DB are cached
                'is_fallback': bool(email.get('is_fallback', False))
            })
        
        # Get quick stats
        analytics = db.get_analytics(days=30)
        stats = analytics['summary']
        
        return render_template_string(
            HTML_TEMPLATE,
            emails=formatted_emails,
            stats=stats,
            error=None
        )
    except Exception as e:
        logger.error(f"Error loading home page: {e}", exc_info=True)
        return render_template_string(
            HTML_TEMPLATE,
            emails=[],
            stats={},
            error=str(e)
        )


@app.route('/scan')
def scan():
    """Scan inbox for new emails - FAST VERSION"""
    try:
        logger.info("⚡ Starting FAST parallel scan...")
        
        # Use fast parallel scanner
        results = fast_scanner.scan_parallel(max_emails=20)
        
        logger.info(f"✅ Fast scan complete! Processed: {results['processed']}, Cached: {results['cached']}")
        return redirect(url_for('home'))
        
    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        return render_template_string(
            HTML_TEMPLATE,
            emails=[],
            stats={},
            error=f"Scan failed: {str(e)}"
        )


@app.route('/send_reply/<message_id>')
def send_reply_route(message_id):
    """Send reply to an email"""
    try:
        email_data = db.get_email_analysis(message_id)
        if not email_data:
            return redirect(url_for('home'))
        
        if email_data['clean_reply'] and not email_data['sent']:
            success = gmail_service.send_email_reply(
                email_data['sender'],
                email_data['subject'],
                email_data['clean_reply'],
                email_data.get('thread_id')
            )
            
            if success:
                db.mark_as_sent(message_id)
                logger.info(f"Reply sent for {message_id}")
        
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error sending reply: {e}")
        return redirect(url_for('home'))


@app.route('/archive/<message_id>')
def archive_route(message_id):
    """Archive an email"""
    try:
        success = gmail_service.archive_email(message_id)
        if success:
            db.mark_as_archived(message_id)
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error archiving: {e}")
        return redirect(url_for('home'))


@app.route('/delete/<message_id>')
def delete_route(message_id):
    """Delete an email"""
    try:
        success = gmail_service.delete_email(message_id)
        if success:
            db.mark_as_deleted(message_id)
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error deleting: {e}")
        return redirect(url_for('home'))


@app.route('/analytics')
def analytics():
    """Show analytics dashboard"""
    try:
        analytics_data = db.get_analytics(days=30)
        return render_template_string(
            ANALYTICS_TEMPLATE,
            analytics=analytics_data
        )
    except Exception as e:
        logger.error(f"Error loading analytics: {e}")
        return redirect(url_for('home'))


@app.route('/clear_cache')
def clear_cache():
    """Clear all data"""
    try:
        db.clear_all_data()
        logger.info("Cache cleared")
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return redirect(url_for('home'))


@app.route('/logout')
def logout():
    """Logout and remove credentials"""
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
        logger.info("User logged out")
        return redirect(url_for('home'))
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return redirect(url_for('home'))


if __name__ == '__main__':
    logger.info("Starting AI Inbox Zero application...")
    app.run(debug=True, port=5000)