"""
SIMPLIFIED FAST VERSION - No database locks, instant results
Uses in-memory cache instead of complex database operations
"""
import os
import json
import logging
from flask import Flask, render_template_string, redirect, url_for
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key')

# In-memory storage (fast, no locks!)
EMAIL_CACHE = {}
CACHE_FILE = 'email_cache.json'

# Services
gmail_service = GmailService()
email_analyzer = EmailAnalyzer()

# Load cache on startup
def load_cache():
    global EMAIL_CACHE
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                EMAIL_CACHE = json.load(f)
            logger.info(f"Loaded {len(EMAIL_CACHE)} emails from cache")
        except:
            EMAIL_CACHE = {}

def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMAIL_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Cache save error: {e}")

load_cache()

# Simple HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Inbox Zero - Fast</title>
    <meta http-equiv="refresh" content="5;url={{ url_for('home') }}" />
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', system-ui, sans-serif; 
            background: linear-gradient(135deg, #fef2f2, #fff); 
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #dc2626; margin-bottom: 30px; text-align: center; font-size: 2.5rem; }
        .nav { display: flex; gap: 10px; justify-content: center; margin-bottom: 30px; }
        .btn { 
            padding: 12px 30px; background: #dc2626; color: white; 
            text-decoration: none; border-radius: 25px; font-weight: 600;
            display: inline-block; transition: 0.2s;
        }
        .btn:hover { background: #991b1b; transform: translateY(-2px); }
        .btn-secondary { background: white; color: #dc2626; border: 2px solid #dc2626; }
        .stats { display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; justify-content: center; }
        .stat { 
            background: white; padding: 20px 30px; border-radius: 15px; 
            border: 1px solid #fecaca; min-width: 150px; text-align: center;
        }
        .stat-num { font-size: 2rem; font-weight: 700; color: #dc2626; }
        .stat-label { color: #6b7280; margin-top: 5px; }
        .email-grid { display: grid; gap: 20px; }
        .email-card { 
            background: white; padding: 25px; border-radius: 15px; 
            border: 1px solid #fecaca; transition: 0.2s;
        }
        .email-card:hover { transform: translateY(-3px); box-shadow: 0 10px 20px rgba(0,0,0,0.1); }
        .email-header { display: flex; justify-content: space-between; margin-bottom: 15px; }
        .sender { color: #991b1b; font-weight: 700; font-size: 0.9rem; }
        .subject { font-size: 1.3rem; font-weight: 600; margin: 8px 0; color: #111; }
        .badge { 
            padding: 5px 12px; border-radius: 10px; font-size: 0.75rem; 
            font-weight: 700; text-transform: uppercase;
        }
        .badge-Important { background: #fee2e2; color: #991b1b; }
        .badge-Newsletter { background: #d1fae5; color: #065f46; }
        .badge-Personal { background: #dbeafe; color: #1e40af; }
        .badge-Spam { background: #f3f4f6; color: #4b5563; }
        .reply-box { 
            background: #f9fafb; padding: 15px; border-radius: 10px; 
            margin: 15px 0; border-left: 4px solid #dc2626;
            white-space: pre-wrap; font-family: monospace; font-size: 0.9rem;
        }
        .actions { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        .action-btn { 
            padding: 8px 20px; border-radius: 10px; text-decoration: none; 
            font-weight: 600; font-size: 0.9rem; transition: 0.2s;
        }
        .btn-send { background: #dc2626; color: white; }
        .btn-send:hover { background: #991b1b; }
        .btn-archive { background: white; color: #4b5563; border: 1px solid #d1d5db; }
        .btn-archive:hover { background: #f3f4f6; }
        .empty { text-align: center; padding: 60px; color: #6b7280; font-size: 1.2rem; }
        .loading { text-align: center; padding: 40px; }
        .spinner { 
            border: 3px solid #f3f4f6; border-top-color: #dc2626; 
            border-radius: 50%; width: 40px; height: 40px; 
            animation: spin 1s linear infinite; margin: 0 auto 20px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .auto-refresh { text-align: center; color: #6b7280; font-size: 0.85rem; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ AI Inbox Zero</h1>
        
        <div class="nav">
            <a href="/scan" class="btn">🔄 Scan Inbox</a>
            <a href="/clear" class="btn btn-secondary">🗑️ Clear Cache</a>
        </div>

        {% if scanning %}
        <div class="loading">
            <div class="spinner"></div>
            <p>⚡ Scanning emails in parallel...</p>
        </div>
        {% endif %}

        <div class="stats">
            <div class="stat">
                <div class="stat-num">{{ stats.total }}</div>
                <div class="stat-label">Total</div>
            </div>
            <div class="stat">
                <div class="stat-num">{{ stats.important }}</div>
                <div class="stat-label">Important</div>
            </div>
            <div class="stat">
                <div class="stat-num">{{ stats.personal }}</div>
                <div class="stat-label">Personal</div>
            </div>
            <div class="stat">
                <div class="stat-num">{{ stats.newsletter }}</div>
                <div class="stat-label">Newsletters</div>
            </div>
            <div class="stat">
                <div class="stat-num">{{ stats.spam }}</div>
                <div class="stat-label">Spam</div>
            </div>
        </div>

        <div class="auto-refresh">🔄 Auto-refreshing every 5 seconds...</div>

        {% if not emails %}
        <div class="empty">✅ Inbox Zero! No emails to process.</div>
        {% else %}
        <div class="email-grid">
            {% for email in emails %}
            <div class="email-card">
                <div class="email-header">
                    <div>
                        <div class="sender">{{ email.sender[:60] }}</div>
                        <div class="subject">{{ email.subject }}</div>
                    </div>
                    <span class="badge badge-{{ email.category }}">{{ email.category }}</span>
                </div>
                
                {% if email.reply != "No reply needed" %}
                <div class="reply-box">{{ email.reply[:300] }}...</div>
                {% endif %}

                <div class="actions">
                    {% if email.reply != "No reply needed" %}
                    <a href="/send/{{ email.id }}" class="action-btn btn-send">🚀 Send</a>
                    {% endif %}
                    <a href="/archive/{{ email.id }}" class="action-btn btn-archive">📦 Archive</a>
                    <a href="/delete/{{ email.id }}" class="action-btn btn-archive">🗑️ Delete</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

def process_email(email):
    """Process a single email"""
    email_id = email['id']
    
    # Check cache
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
    
    # Analyze with AI
    try:
        logger.info(f"⚡ {email['subject'][:40]}")
        ai_result = email_analyzer.analyze_email(
            email['sender'],
            email['subject'],
            email.get('snippet', '')
        )
        
        # Store in cache
        EMAIL_CACHE[email_id] = {
            'category': ai_result.get('category', 'Unknown'),
            'reply': ai_result.get('reply', 'No reply needed'),
            'sender': email['sender'],
            'subject': email['subject']
        }
        
        # Create draft if needed
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
        logger.error(f"Error: {e}")
        return None

@app.route('/')
def home():
    """Show processed emails"""
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
    
    return render_template_string(HTML, emails=emails, stats=stats, scanning=False)

@app.route('/scan')
def scan():
    """Fast parallel scan"""
    logger.info("🚀 Starting fast scan...")
    
    # Fetch emails
    raw_emails = gmail_service.fetch_unread_emails(max_results=20)
    
    if not raw_emails:
        return redirect(url_for('home'))
    
    # Process in parallel
    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(process_email, email) for email in raw_emails]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)
    
    # Save cache
    save_cache()
    
    logger.info(f"✅ Processed {len(results)} emails")
    return redirect(url_for('home'))

@app.route('/send/<email_id>')
def send_reply(email_id):
    """Send reply"""
    if email_id in EMAIL_CACHE:
        data = EMAIL_CACHE[email_id]
        try:
            gmail_service.send_email_reply(
                data['sender'],
                data['subject'],
                data['reply']
            )
            logger.info(f"✉️ Sent reply to {data['sender']}")
        except Exception as e:
            logger.error(f"Send error: {e}")
    return redirect(url_for('home'))

@app.route('/archive/<email_id>')
def archive(email_id):
    """Archive email"""
    try:
        gmail_service.archive_email(email_id)
        if email_id in EMAIL_CACHE:
            del EMAIL_CACHE[email_id]
        save_cache()
    except Exception as e:
        logger.error(f"Archive error: {e}")
    return redirect(url_for('home'))

@app.route('/delete/<email_id>')
def delete(email_id):
    """Delete email"""
    try:
        gmail_service.delete_email(email_id)
        if email_id in EMAIL_CACHE:
            del EMAIL_CACHE[email_id]
        save_cache()
    except Exception as e:
        logger.error(f"Delete error: {e}")
    return redirect(url_for('home'))

@app.route('/clear')
def clear():
    """Clear cache"""
    global EMAIL_CACHE
    EMAIL_CACHE = {}
    save_cache()
    return redirect(url_for('home'))

if __name__ == '__main__':
    logger.info("⚡ Starting FAST AI Inbox Zero...")
    app.run(debug=True, port=5000)