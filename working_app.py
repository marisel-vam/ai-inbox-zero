"""
FULLY WORKING AI INBOX ZERO
All features actually implemented and working!
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, redirect, url_for, session
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-this')

# Storage
EMAIL_CACHE = {}
ANALYTICS_DATA = {
    'total_processed': 0,
    'time_saved_minutes': 0,
    'inbox_zero_streak': 0,
    'last_check': None,
    'response_times': [],
    'sender_frequency': defaultdict(int),
    'category_breakdown': defaultdict(int)
}
AUTO_PILOT_SETTINGS = {
    'enabled': False,
    'auto_archive_newsletters': True,
    'auto_delete_spam': True,
    'auto_archive_low_priority': False
}
SNOOZED_EMAILS = {}

CACHE_FILE = 'email_cache.json'
ANALYTICS_FILE = 'analytics.json'
AUTOPILOT_FILE = 'autopilot.json'
SNOOZED_FILE = 'snoozed.json'

gmail_service = GmailService()
email_analyzer = EmailAnalyzer()

def load_data():
    global EMAIL_CACHE, ANALYTICS_DATA, AUTO_PILOT_SETTINGS, SNOOZED_EMAILS
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                EMAIL_CACHE = json.load(f)
        except:
            EMAIL_CACHE = {}
    
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                ANALYTICS_DATA.update(loaded)
                if 'sender_frequency' in loaded:
                    ANALYTICS_DATA['sender_frequency'] = defaultdict(int, loaded['sender_frequency'])
                if 'category_breakdown' in loaded:
                    ANALYTICS_DATA['category_breakdown'] = defaultdict(int, loaded['category_breakdown'])
        except:
            pass
    
    if os.path.exists(AUTOPILOT_FILE):
        try:
            with open(AUTOPILOT_FILE, 'r', encoding='utf-8') as f:
                AUTO_PILOT_SETTINGS.update(json.load(f))
        except:
            pass
    
    if os.path.exists(SNOOZED_FILE):
        try:
            with open(SNOOZED_FILE, 'r', encoding='utf-8') as f:
                SNOOZED_EMAILS = json.load(f)
        except:
            SNOOZED_EMAILS = {}

def save_data():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMAIL_CACHE, f, ensure_ascii=False, indent=2)
        
        analytics_to_save = dict(ANALYTICS_DATA)
        analytics_to_save['sender_frequency'] = dict(ANALYTICS_DATA['sender_frequency'])
        analytics_to_save['category_breakdown'] = dict(ANALYTICS_DATA['category_breakdown'])
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics_to_save, f, indent=2)
        
        with open(AUTOPILOT_FILE, 'w', encoding='utf-8') as f:
            json.dump(AUTO_PILOT_SETTINGS, f, indent=2)
        
        with open(SNOOZED_FILE, 'w', encoding='utf-8') as f:
            json.dump(SNOOZED_EMAILS, f, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

load_data()

def check_snoozed_emails():
    now = datetime.now()
    woken = []
    for email_id, wake_time_str in list(SNOOZED_EMAILS.items()):
        wake_time = datetime.fromisoformat(wake_time_str)
        if now >= wake_time:
            woken.append(email_id)
            del SNOOZED_EMAILS[email_id]
    if woken:
        save_data()
    return woken

def calculate_priority(email_data, ai_result):
    priority_score = 0
    urgent_keywords = ['urgent', 'asap', 'immediate', 'deadline', 'important', 'critical']
    subject_lower = email_data['subject'].lower()
    
    for word in urgent_keywords:
        if word in subject_lower:
            priority_score += 15
    
    category = ai_result.get('category', '')
    if category == 'Important':
        priority_score += 40
    elif category == 'Personal':
        priority_score += 20
    
    if ai_result.get('priority') == 'High':
        priority_score += 30
    elif ai_result.get('priority') == 'Medium':
        priority_score += 15
    
    if priority_score >= 50:
        return 'HIGH'
    elif priority_score >= 20:
        return 'MEDIUM'
    else:
        return 'LOW'

def apply_autopilot(email_id, category, priority):
    if not AUTO_PILOT_SETTINGS['enabled']:
        return None
    
    action_taken = None
    try:
        if AUTO_PILOT_SETTINGS.get('auto_archive_newsletters', True):
            if category == 'Newsletter':
                gmail_service.archive_email(email_id)
                action_taken = '📦 Auto-archived (Newsletter)'
                logger.info(f"✈️ Auto-Pilot: Archived newsletter")
        
        if AUTO_PILOT_SETTINGS.get('auto_delete_spam', True):
            if category == 'Spam':
                gmail_service.delete_email(email_id)
                action_taken = '🗑️ Auto-deleted (Spam)'
                logger.info(f"✈️ Auto-Pilot: Deleted spam")
        
        if AUTO_PILOT_SETTINGS.get('auto_archive_low_priority', False):
            if priority == 'LOW' and category not in ['Important', 'Personal']:
                gmail_service.archive_email(email_id)
                action_taken = '📦 Auto-archived (Low Priority)'
                logger.info(f"✈️ Auto-Pilot: Archived low priority")
    except Exception as e:
        logger.error(f"Auto-pilot error: {e}")
    
    return action_taken

def process_email_with_analytics(email):
    email_id = email['id']
    
    if email_id in SNOOZED_EMAILS:
        return None
    
    if email_id in EMAIL_CACHE:
        cached = EMAIL_CACHE[email_id]
        return {
            'id': email_id,
            'sender': email['sender'],
            'subject': email['subject'],
            'category': cached.get('category', 'Unknown'),
            'reply': cached.get('reply', 'No reply needed'),
            'priority': cached.get('priority', 'MEDIUM'),
            'autopilot_action': cached.get('autopilot_action'),
            'cached': True
        }
    
    try:
        logger.info(f"⚡ Analyzing: {email['subject'][:50]}")
        ai_result = email_analyzer.analyze_email(
            email['sender'],
            email['subject'],
            email.get('snippet', '')
        )
        
        priority = calculate_priority(email, ai_result)
        autopilot_action = apply_autopilot(email_id, ai_result.get('category'), priority)
        
        ANALYTICS_DATA['total_processed'] += 1
        ANALYTICS_DATA['time_saved_minutes'] += 3
        ANALYTICS_DATA['sender_frequency'][email['sender']] += 1
        ANALYTICS_DATA['category_breakdown'][ai_result.get('category', 'Unknown')] += 1
        
        EMAIL_CACHE[email_id] = {
            'category': ai_result.get('category', 'Unknown'),
            'reply': ai_result.get('reply', 'No reply needed'),
            'sender': email['sender'],
            'subject': email['subject'],
            'priority': priority,
            'autopilot_action': autopilot_action,
            'timestamp': datetime.now().isoformat()
        }
        
        if ai_result.get('needs_reply') and not autopilot_action:
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
            'priority': priority,
            'autopilot_action': autopilot_action,
            'cached': False
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Inbox Zero</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #dc2626; --success: #10b981; --bg: #fafafa;
            --card: #ffffff; --text: #1f2937; --border: #e5e7eb;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #fef2f2 0%, #fff 50%, #dbeafe 100%);
            color: var(--text); min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 2rem; }
        .navbar {
            background: rgba(255, 255, 255, 0.95); padding: 1rem 0;
            position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border);
        }
        .navbar-content {
            max-width: 1600px; margin: 0 auto; padding: 0 2rem;
            display: flex; justify-content: space-between; align-items: center;
        }
        .logo {
            font-size: 1.75rem; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), #0ea5e9);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .nav-actions { display: flex; gap: 0.75rem; }
        .btn {
            padding: 0.75rem 1.5rem; border-radius: 0.75rem; text-decoration: none;
            font-weight: 600; font-size: 0.875rem; transition: 0.2s;
            cursor: pointer; border: none; display: inline-flex;
            align-items: center; gap: 0.5rem; text-transform: uppercase;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), #991b1b);
            color: white; box-shadow: 0 4px 6px rgba(220, 38, 38, 0.3);
        }
        .btn-secondary { background: white; color: var(--text); border: 1px solid var(--border); }
        .btn-success { background: var(--success); color: white; }
        .autopilot-banner {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white; padding: 1.5rem 2rem; border-radius: 1rem;
            margin-bottom: 2rem; display: flex; justify-content: space-between;
            align-items: center; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);
        }
        .autopilot-banner.inactive { background: linear-gradient(135deg, #6b7280, #4b5563); }
        .autopilot-info { display: flex; align-items: center; gap: 1rem; }
        .autopilot-icon {
            width: 60px; height: 60px; background: rgba(255,255,255,0.2);
            border-radius: 50%; display: flex; align-items: center;
            justify-content: center; font-size: 2rem;
        }
        .settings-panel {
            background: white; padding: 1.5rem; border-radius: 1rem;
            border: 1px solid var(--border); margin-bottom: 2rem;
        }
        .setting-item {
            display: flex; justify-content: space-between; align-items: center;
            padding: 1rem; border-bottom: 1px solid var(--border);
        }
        .setting-item:last-child { border-bottom: none; }
        .toggle {
            width: 50px; height: 26px; background: #6b7280;
            border-radius: 13px; position: relative; cursor: pointer; transition: 0.3s;
        }
        .toggle.active { background: var(--success); }
        .toggle-slider {
            width: 22px; height: 22px; background: white;
            border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: 0.3s;
        }
        .toggle.active .toggle-slider { left: 26px; }
        .analytics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem; margin-bottom: 3rem;
        }
        .metric-card {
            background: white; padding: 2rem; border-radius: 1.25rem; border: 1px solid var(--border);
        }
        .metric-value {
            font-size: 2.5rem; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), #0ea5e9);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .metric-label { color: #6b7280; font-size: 0.875rem; text-transform: uppercase; margin-top: 0.5rem; }
        .email-grid { display: grid; gap: 1.5rem; }
        .email-card {
            background: white; border-radius: 1.25rem; padding: 2rem;
            border: 1px solid var(--border); position: relative;
        }
        .autopilot-badge {
            position: absolute; top: 1rem; right: 1rem;
            background: var(--success); color: white;
            padding: 0.5rem 1rem; border-radius: 0.5rem;
            font-size: 0.75rem; font-weight: 700;
        }
        .sender { color: var(--primary); font-weight: 600; font-size: 0.875rem; }
        .subject { font-size: 1.25rem; font-weight: 700; margin: 0.5rem 0; }
        .priority-HIGH { color: #dc2626; }
        .priority-MEDIUM { color: #f59e0b; }
        .priority-LOW { color: #6b7280; }
        .badge {
            padding: 0.375rem 0.875rem; border-radius: 0.75rem;
            font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
        }
        .badge-Important { background: #fee2e2; color: #991b1b; }
        .badge-Newsletter { background: #d1fae5; color: #065f46; }
        .badge-Personal { background: #dbeafe; color: #1e40af; }
        .badge-Spam { background: #f3f4f6; color: #4b5563; }
        .ai-response {
            background: #f9fafb; border-radius: 1rem; padding: 1.5rem;
            margin: 1rem 0; border-left: 4px solid var(--primary);
        }
        .email-actions {
            display: flex; gap: 0.75rem; margin-top: 1rem;
            padding-top: 1rem; border-top: 1px solid var(--border);
        }
        .success-message {
            background: var(--success); color: white;
            padding: 1rem 2rem; border-radius: 0.75rem;
            margin-bottom: 1rem; font-weight: 600;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-content">
            <div class="logo">⚡ AI INBOX ZERO</div>
            <div class="nav-actions">
                <a href="/scan" class="btn btn-primary">🔄 Scan</a>
                <a href="/clear" class="btn btn-secondary">🗑️ Clear</a>
                <a href="/logout" class="btn btn-secondary">👋 Logout</a>
            </div>
        </div>
    </nav>

    <div class="container">
        {% if success %}
        <div class="success-message">✅ {{ success }}</div>
        {% endif %}

        <div class="autopilot-banner {% if not autopilot.enabled %}inactive{% endif %}">
            <div class="autopilot-info">
                <div class="autopilot-icon">🤖</div>
                <div>
                    <h3>{% if autopilot.enabled %}AUTO-PILOT ACTIVE{% else %}AUTO-PILOT OFF{% endif %}</h3>
                    <p>{% if autopilot.enabled %}AI managing inbox automatically{% else %}Enable for hands-free management{% endif %}</p>
                </div>
            </div>
            <a href="/toggle_autopilot" class="btn {% if autopilot.enabled %}btn-secondary{% else %}btn-success{% endif %}">
                {% if autopilot.enabled %}Disable{% else %}Enable Now{% endif %}
            </a>
        </div>

        {% if autopilot.enabled %}
        <div class="settings-panel">
            <div style="font-size: 1.25rem; font-weight: 700; margin-bottom: 1rem;">⚙️ Auto-Pilot Settings</div>
            <div class="setting-item">
                <span>📦 Auto-archive Newsletters</span>
                <a href="/toggle_setting/auto_archive_newsletters">
                    <div class="toggle {% if autopilot.auto_archive_newsletters %}active{% endif %}">
                        <div class="toggle-slider"></div>
                    </div>
                </a>
            </div>
            <div class="setting-item">
                <span>🗑️ Auto-delete Spam</span>
                <a href="/toggle_setting/auto_delete_spam">
                    <div class="toggle {% if autopilot.auto_delete_spam %}active{% endif %}">
                        <div class="toggle-slider"></div>
                    </div>
                </a>
            </div>
            <div class="setting-item">
                <span>📦 Auto-archive Low Priority</span>
                <a href="/toggle_setting/auto_archive_low_priority">
                    <div class="toggle {% if autopilot.auto_archive_low_priority %}active{% endif %}">
                        <div class="toggle-slider"></div>
                    </div>
                </a>
            </div>
        </div>
        {% endif %}

        <div class="analytics-grid">
            <div class="metric-card">
                <div class="metric-value">{{ analytics.time_saved }}min</div>
                <div class="metric-label">Time Saved</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ analytics.inbox_zero_streak }}</div>
                <div class="metric-label">Inbox Zero Streak</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ stats.total }}</div>
                <div class="metric-label">Total Emails</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ analytics.total_processed }}</div>
                <div class="metric-label">All-Time Processed</div>
            </div>
        </div>

        <h2 style="margin-bottom: 1.5rem; font-size: 1.75rem;">📬 Emails by Priority</h2>
        <div class="email-grid">
            {% for email in emails %}
            <div class="email-card">
                {% if email.autopilot_action %}
                <div class="autopilot-badge">{{ email.autopilot_action }}</div>
                {% endif %}
                
                <div>
                    <div class="sender">{{ email.sender[:50] }}</div>
                    <h3 class="subject">{{ email.subject }}</h3>
                    <span class="priority-{{ email.priority }}">
                        {% if email.priority == 'HIGH' %}🔴{% elif email.priority == 'MEDIUM' %}🟡{% else %}⚪{% endif %}
                        {{ email.priority }}
                    </span>
                    <span class="badge badge-{{ email.category }}" style="margin-left: 1rem;">{{ email.category }}</span>
                </div>

                {% if email.reply and email.reply != "No reply needed" %}
                <div class="ai-response">
                    <div style="font-size: 0.75rem; font-weight: 700; margin-bottom: 0.75rem;">🤖 AI REPLY</div>
                    <div>{{ email.reply[:300] }}</div>
                </div>
                {% endif %}

                <div class="email-actions">
                    {% if email.reply and email.reply != "No reply needed" %}
                    <a href="/send/{{ email.id }}" class="btn btn-primary">🚀 Send</a>
                    {% endif %}
                    <a href="/archive/{{ email.id }}" class="btn btn-secondary">📦 Archive</a>
                    <a href="/snooze/{{ email.id }}" class="btn btn-secondary">⏰ Snooze</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    check_snoozed_emails()
    emails = []
    stats = {'total': 0, 'important': 0, 'personal': 0, 'newsletter': 0, 'spam': 0}
    
    email_list = []
    for email_id, data in EMAIL_CACHE.items():
        if email_id not in SNOOZED_EMAILS:
            email_list.append({
                'id': email_id,
                'sender': data['sender'],
                'subject': data['subject'],
                'category': data['category'],
                'reply': data['reply'],
                'priority': data.get('priority', 'MEDIUM'),
                'autopilot_action': data.get('autopilot_action')
            })
            stats['total'] += 1
            cat = data['category'].lower()
            if cat in stats:
                stats[cat] += 1
    
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    emails = sorted(email_list, key=lambda x: priority_order.get(x['priority'], 3))[:50]
    
    analytics = {
        'time_saved': ANALYTICS_DATA['time_saved_minutes'],
        'inbox_zero_streak': ANALYTICS_DATA['inbox_zero_streak'],
        'total_processed': ANALYTICS_DATA['total_processed']
    }
    
    success = session.pop('success', None)
    return render_template_string(HTML, emails=emails, stats=stats, analytics=analytics, autopilot=AUTO_PILOT_SETTINGS, success=success)

@app.route('/scan')
def scan():
    raw_emails = gmail_service.fetch_unread_emails(max_results=20)
    if raw_emails:
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_email_with_analytics, email) for email in raw_emails]
            count = 0
            for future in as_completed(futures):
                if future.result():
                    count += 1
        session['success'] = f"Processed {count} emails!"
        if AUTO_PILOT_SETTINGS['enabled']:
            session['success'] += " Auto-Pilot active!"
    else:
        ANALYTICS_DATA['inbox_zero_streak'] += 1
        session['success'] = "Inbox Zero! 🎉"
    save_data()
    return redirect(url_for('home'))

@app.route('/toggle_autopilot')
def toggle_autopilot():
    AUTO_PILOT_SETTINGS['enabled'] = not AUTO_PILOT_SETTINGS['enabled']
    save_data()
    status = "enabled ✈️" if AUTO_PILOT_SETTINGS['enabled'] else "disabled"
    session['success'] = f"Auto-Pilot {status}!"
    return redirect(url_for('home'))

@app.route('/toggle_setting/<setting_name>')
def toggle_setting(setting_name):
    if setting_name in AUTO_PILOT_SETTINGS:
        AUTO_PILOT_SETTINGS[setting_name] = not AUTO_PILOT_SETTINGS[setting_name]
        save_data()
        session['success'] = "Setting updated!"
    return redirect(url_for('home'))

@app.route('/snooze/<email_id>')
def snooze(email_id):
    wake_time = datetime.now() + timedelta(hours=24)
    SNOOZED_EMAILS[email_id] = wake_time.isoformat()
    save_data()
    session['success'] = "Email snoozed for 24 hours! ⏰"
    return redirect(url_for('home'))

@app.route('/send/<email_id>')
def send_reply(email_id):
    if email_id in EMAIL_CACHE:
        data = EMAIL_CACHE[email_id]
        try:
            gmail_service.send_email_reply(data['sender'], data['subject'], data['reply'])
            session['success'] = "Reply sent! 🚀"
        except Exception as e:
            logger.error(f"Send error: {e}")
    return redirect(url_for('home'))

@app.route('/archive/<email_id>')
def archive(email_id):
    try:
        gmail_service.archive_email(email_id)
        if email_id in EMAIL_CACHE:
            del EMAIL_CACHE[email_id]
        save_data()
        session['success'] = "Email archived! 📦"
    except Exception as e:
        logger.error(f"Archive error: {e}")
    return redirect(url_for('home'))

@app.route('/clear')
def clear():
    global EMAIL_CACHE
    EMAIL_CACHE = {}
    save_data()
    session['success'] = "Cache cleared!"
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
        session['success'] = "Logged out!"
    except Exception as e:
        logger.error(f"Logout error: {e}")
    return redirect(url_for('home'))

if __name__ == '__main__':
    logger.info("🚀 Starting Fully Working AI Inbox Zero...")
    app.run(debug=True, port=5000)