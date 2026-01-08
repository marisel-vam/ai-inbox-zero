"""
ULTIMATE AI INBOX ZERO - V2.2 (Production Ready)
Features: Manual Delete Button Added, Bug Fixes, Persistent Storage
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, redirect, url_for, session, jsonify
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'ultimate-dev-key-secure')

# --- CONFIGURATION & STORAGE ---
CACHE_FILE = 'email_cache.json'
ANALYTICS_FILE = 'analytics.json'
SNOOZED_FILE = 'snoozed.json'
SETTINGS_FILE = 'settings.json'

EMAIL_CACHE = {}
SNOOZED_EMAILS = {} 

# Enhanced Analytics
ANALYTICS_DATA = {
    'total_processed': 0,
    'time_saved_minutes': 0,
    'inbox_zero_streak': 0,
    'last_check': None,
    'sender_frequency': defaultdict(int),
    'category_breakdown': defaultdict(int)
}

# Granular Auto-Pilot Settings
AUTO_PILOT_SETTINGS = {
    'enabled': False,
    'rules': {
        'archive_newsletters': True,
        'delete_spam': True,
        'archive_low_priority': False
    }
}

gmail_service = GmailService()
email_analyzer = EmailAnalyzer()

# --- PERSISTENCE LAYER ---
def load_data():
    global EMAIL_CACHE, ANALYTICS_DATA, SNOOZED_EMAILS, AUTO_PILOT_SETTINGS
    
    # Load Cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                EMAIL_CACHE = json.load(f)
        except: EMAIL_CACHE = {}

    # Load Analytics
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                ANALYTICS_DATA.update(loaded)
                ANALYTICS_DATA['sender_frequency'] = defaultdict(int, loaded.get('sender_frequency', {}))
                ANALYTICS_DATA['category_breakdown'] = defaultdict(int, loaded.get('category_breakdown', {}))
        except: pass

    # Load Snoozed
    if os.path.exists(SNOOZED_FILE):
        try:
            with open(SNOOZED_FILE, 'r', encoding='utf-8') as f:
                SNOOZED_EMAILS = json.load(f)
        except: SNOOZED_EMAILS = {}

    # Load Settings
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
                if 'enabled' in loaded_settings:
                    AUTO_PILOT_SETTINGS['enabled'] = loaded_settings['enabled']
                if 'rules' in loaded_settings:
                    AUTO_PILOT_SETTINGS['rules'].update(loaded_settings['rules'])
        except: pass

def save_data():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMAIL_CACHE, f, ensure_ascii=False, indent=2)
        
        analytics_safe = dict(ANALYTICS_DATA)
        analytics_safe['sender_frequency'] = dict(ANALYTICS_DATA['sender_frequency'])
        analytics_safe['category_breakdown'] = dict(ANALYTICS_DATA['category_breakdown'])
        
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics_safe, f, indent=2)
            
        with open(SNOOZED_FILE, 'w', encoding='utf-8') as f:
            json.dump(SNOOZED_EMAILS, f, indent=2)
            
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(AUTO_PILOT_SETTINGS, f, indent=2)
    except Exception as e:
        logger.error(f"Save error: {e}")

load_data()

# --- LOGIC HELPERS ---
def check_snoozed_emails():
    """Wakes up emails whose snooze time has passed."""
    now = datetime.now()
    woken_count = 0
    for email_id, wake_time_str in list(SNOOZED_EMAILS.items()):
        wake_time = datetime.fromisoformat(wake_time_str)
        if now >= wake_time:
            del SNOOZED_EMAILS[email_id]
            woken_count += 1
    if woken_count > 0:
        save_data()
    return woken_count

def calculate_priority(email_data, ai_result):
    """Scoring system to determine High/Medium/Low priority."""
    score = 0
    subject_lower = email_data['subject'].lower()
    
    # 1. Keyword urgency (Added security/alert keywords)
    urgent_keywords = [
        'urgent', 'asap', 'immediate', 'deadline', 'critical', 'overdue',
        'security', 'alert', 'verify', 'password', 'login'
    ]
    if any(k in subject_lower for k in urgent_keywords): score += 30
    
    # 2. AI Categorization
    cat = ai_result.get('category', '')
    if cat == 'Important': score += 40
    elif cat == 'Personal': score += 20
    elif cat == 'Spam': score -= 50
    
    # 3. AI Direct Priority
    ai_prio = ai_result.get('priority', 'Low')
    if ai_prio == 'High': score += 30
    elif ai_prio == 'Medium': score += 15
    
    if score >= 50: return 'HIGH'
    elif score >= 25: return 'MEDIUM'
    return 'LOW'

def apply_autopilot_rules(email_id, category, priority):
    """Applies granular auto-pilot actions."""
    if not AUTO_PILOT_SETTINGS['enabled']: return None
    
    rules = AUTO_PILOT_SETTINGS['rules']
    action_taken = None

    try:
        if rules.get('archive_newsletters') and category == 'Newsletter':
            gmail_service.archive_email(email_id)
            action_taken = 'Archived (Newsletter)'
            
        elif rules.get('delete_spam') and category == 'Spam':
            gmail_service.delete_email(email_id)
            action_taken = 'Deleted (Spam)'
            
        elif rules.get('archive_low_priority') and priority == 'LOW' and category not in ['Important', 'Personal']:
            gmail_service.archive_email(email_id)
            action_taken = 'Archived (Low Prio)'
            
    except Exception as e:
        logger.error(f"Autopilot failed for {email_id}: {e}")
        
    return action_taken

def process_email(email):
    """Main processing pipeline for a single email."""
    email_id = email['id']
    
    if email_id in SNOOZED_EMAILS: return None

    if email_id in EMAIL_CACHE:
        return {**EMAIL_CACHE[email_id], 'id': email_id, 'cached': True}

    try:
        ai_res = email_analyzer.analyze_email(email['sender'], email['subject'], email.get('snippet', ''))
        priority = calculate_priority(email, ai_res)
        auto_action = apply_autopilot_rules(email_id, ai_res.get('category'), priority)
        
        ANALYTICS_DATA['total_processed'] += 1
        ANALYTICS_DATA['time_saved_minutes'] += 2.5
        ANALYTICS_DATA['sender_frequency'][email['sender']] += 1
        ANALYTICS_DATA['category_breakdown'][ai_res.get('category', 'Unknown')] += 1
        
        if ai_res.get('needs_reply') and not auto_action:
            try:
                gmail_service.create_draft_reply(email['sender'], email['subject'], ai_res['reply'])
            except: pass

        data = {
            'sender': email['sender'],
            'subject': email['subject'],
            'category': ai_res.get('category', 'Unknown'),
            'reply': ai_res.get('reply', 'No reply needed'),
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'autopilot_action': auto_action
        }
        
        EMAIL_CACHE[email_id] = data
        return {**data, 'id': email_id, 'cached': False}

    except Exception as e:
        logger.error(f"Processing error: {e}")
        return None

# --- HTML TEMPLATE ---
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Inbox Zero - Ultimate</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #dc2626; --primary-dark: #991b1b; --primary-light: #fef2f2;
            --secondary: #0ea5e9; --success: #10b981; --warning: #f59e0b; --danger: #ef4444;
            --bg: #fafafa; --card: #ffffff; --text: #1f2937; --text-light: #6b7280;
            --border: #e5e7eb; --shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--primary-light) 0%, #fff 50%, #dbeafe 100%);
            color: var(--text); line-height: 1.6; min-height: 100vh;
        }
        .container { max-width: 1600px; margin: 0 auto; padding: 2rem; }
        
        /* Navbar */
        .navbar {
            background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--border); padding: 1rem 0;
            position: sticky; top: 0; z-index: 100;
        }
        .navbar-content {
            max-width: 1600px; margin: 0 auto; padding: 0 2rem;
            display: flex; justify-content: space-between; align-items: center;
        }
        .logo {
            font-size: 1.75rem; font-weight: 800;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .nav-actions { display: flex; gap: 0.75rem; align-items: center; }
        
        /* Buttons */
        .btn {
            padding: 0.75rem 1.5rem; border-radius: 0.75rem; text-decoration: none;
            font-weight: 600; font-size: 0.875rem; transition: all 0.2s;
            cursor: pointer; border: none; display: inline-flex; align-items: center; gap: 0.5rem;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white; box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.3);
        }
        .btn-primary:hover { transform: translateY(-2px); }
        .btn-secondary { background: white; color: var(--text); border: 1px solid var(--border); }
        .btn-secondary:hover { background: var(--bg); border-color: var(--primary); }
        .btn-success { background: var(--success); color: white; }
        
        .btn-danger { background: white; color: var(--danger); border: 1px solid var(--danger); }
        .btn-danger:hover { background: var(--danger); color: white; }
        
        /* Auto-Pilot & Settings */
        .autopilot-banner {
            background: linear-gradient(135deg, var(--success), #059669);
            color: white; padding: 1.5rem 2rem; border-radius: 1rem 1rem 0 0;
            display: flex; justify-content: space-between; align-items: center;
            box-shadow: var(--shadow);
        }
        .autopilot-banner.inactive {
            background: linear-gradient(135deg, var(--text-light), #4b5563);
            border-radius: 1rem;
        }
        .settings-panel {
            background: white; border: 1px solid var(--border); border-top: none;
            border-radius: 0 0 1rem 1rem; padding: 1.5rem; margin-bottom: 2rem;
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;
            box-shadow: var(--shadow);
        }
        .setting-toggle {
            display: flex; align-items: center; justify-content: space-between;
            padding: 1rem; background: var(--bg); border-radius: 0.75rem;
        }
        .toggle-switch {
            width: 44px; height: 24px; background: #cbd5e1; border-radius: 12px;
            position: relative; transition: 0.3s; cursor: pointer;
        }
        .toggle-switch.active { background: var(--success); }
        .toggle-switch::after {
            content: ''; position: absolute; top: 2px; left: 2px;
            width: 20px; height: 20px; background: white; border-radius: 50%;
            transition: 0.3s;
        }
        .toggle-switch.active::after { left: 22px; }

        /* Metrics */
        .analytics-grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem; margin-bottom: 3rem; margin-top: 2rem;
        }
        .metric-card {
            background: var(--card); padding: 2rem; border-radius: 1.25rem;
            border: 1px solid var(--border); transition: all 0.3s;
            position: relative; overflow: hidden;
        }
        .metric-card:hover { transform: translateY(-5px); box-shadow: var(--shadow); }
        .metric-value {
            font-size: 2.5rem; font-weight: 800; margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        
        /* Email Cards */
        .email-grid { display: grid; gap: 1.5rem; }
        .email-card {
            background: var(--card); border-radius: 1.25rem; padding: 2rem;
            border: 1px solid var(--border); transition: all 0.3s; position: relative;
        }
        .email-card:hover { transform: translateX(5px); box-shadow: var(--shadow); }
        .priority-tag {
            font-weight: 800; font-size: 0.8rem; letter-spacing: 0.05em; text-transform: uppercase;
        }
        .priority-HIGH { color: #dc2626; }
        .priority-MEDIUM { color: #f59e0b; }
        .priority-LOW { color: #6b7280; }
        
        .ai-response {
            background: linear-gradient(135deg, #fafafa, #f3f4f6);
            border-radius: 1rem; padding: 1.5rem; margin: 1.5rem 0;
            border-left: 4px solid var(--primary);
        }
        .badge {
            padding: 0.375rem 0.875rem; border-radius: 0.75rem;
            font-size: 0.75rem; font-weight: 700; text-transform: uppercase;
        }
        .badge-Important { background: #fee2e2; color: #991b1b; }
        .badge-Newsletter { background: #d1fae5; color: #065f46; }
        .badge-Spam { background: #f3f4f6; color: #4b5563; }
        
        .alert-success {
            background: #d1fae5; color: #065f46; padding: 1rem;
            border-radius: 0.75rem; margin-bottom: 1.5rem; font-weight: 600;
            text-align: center;
        }
        .autopilot-action {
            position: absolute; top: 1rem; right: 1rem;
            background: var(--success); color: white; padding: 0.25rem 0.75rem;
            border-radius: 1rem; font-size: 0.7rem; font-weight: 700;
        }
    </style>
</head>
<body>
    <nav class="navbar">
        <div class="navbar-content">
            <div class="logo">⚡ AI INBOX ZERO</div>
            <div class="nav-actions">
                <a href="/scan" class="btn btn-primary">🔄 Scan Inbox</a>
                <a href="/clear" class="btn btn-secondary">🗑️ Reset</a>
                <a href="/logout" class="btn btn-secondary">👋 Logout</a>
            </div>
        </div>
    </nav>

    <div class="container">
        {% if msg %}
        <div class="alert-success">✨ {{ msg }}</div>
        {% endif %}

        <div class="autopilot-banner {% if not autopilot.enabled %}inactive{% endif %}">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="font-size: 2.5rem;">🤖</div>
                <div>
                    <h3 style="margin: 0; font-size: 1.5rem;">{% if autopilot.enabled %}AUTO-PILOT ACTIVE{% else %}AUTO-PILOT OFF{% endif %}</h3>
                    <p style="margin: 0; opacity: 0.9;">AI is analyzing and organizing your inbox</p>
                </div>
            </div>
            <a href="/toggle_autopilot" class="btn {% if autopilot.enabled %}btn-secondary{% else %}btn-success{% endif %}">
                {% if autopilot.enabled %}Disable{% else %}Enable Now{% endif %}
            </a>
        </div>
        
        {% if autopilot.enabled %}
        <div class="settings-panel">
            <div class="setting-toggle">
                <span>📦 Archive Newsletters</span>
                <a href="/toggle_rule/archive_newsletters" class="toggle-switch {% if autopilot.rules.archive_newsletters %}active{% endif %}"></a>
            </div>
            <div class="setting-toggle">
                <span>🗑️ Delete Spam</span>
                <a href="/toggle_rule/delete_spam" class="toggle-switch {% if autopilot.rules.delete_spam %}active{% endif %}"></a>
            </div>
            <div class="setting-toggle">
                <span>📉 Archive Low Priority</span>
                <a href="/toggle_rule/archive_low_priority" class="toggle-switch {% if autopilot.rules.archive_low_priority %}active{% endif %}"></a>
            </div>
        </div>
        {% else %}
        <div style="margin-bottom: 2rem;"></div>
        {% endif %}

        <div class="analytics-grid">
            <div class="metric-card">
                <span style="font-size: 2rem;">⏱️</span>
                <div class="metric-value">{{ analytics.time_saved_minutes | int }}min</div>
                <div style="color: var(--text-light); font-weight: 600;">Time Saved</div>
            </div>
            <div class="metric-card">
                <span style="font-size: 2rem;">🔥</span>
                <div class="metric-value">{{ analytics.inbox_zero_streak }}</div>
                <div style="color: var(--text-light); font-weight: 600;">Inbox Zero Streak</div>
            </div>
            <div class="metric-card">
                <span style="font-size: 2rem;">📧</span>
                <div class="metric-value">{{ total_emails }}</div>
                <div style="color: var(--text-light); font-weight: 600;">Active Emails</div>
            </div>
            <div class="metric-card">
                <span style="font-size: 2rem;">⚡</span>
                <div class="metric-value">{{ analytics.total_processed }}</div>
                <div style="color: var(--text-light); font-weight: 600;">Total Processed</div>
            </div>
        </div>

        {% if not emails %}
        <div style="text-align: center; padding: 4rem;">
            <div style="font-size: 5rem; margin-bottom: 1rem; opacity: 0.5;">✨</div>
            <h2 style="font-size: 2rem; font-weight: 700;">You've reached Inbox Zero!</h2>
            <p>All caught up. Enjoy your day.</p>
        </div>
        {% else %}
        <div class="email-grid">
            {% for email in emails %}
            <div class="email-card">
                {% if email.autopilot_action %}
                <div class="autopilot-action">⚡ {{ email.autopilot_action }}</div>
                {% endif %}
                
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                    <div>
                        <div style="color: var(--primary); font-weight: 600;">{{ email.sender }}</div>
                        <h3 style="font-size: 1.25rem; font-weight: 700; margin: 0.25rem 0;">{{ email.subject }}</h3>
                        <span class="priority-tag priority-{{ email.priority }}">{{ email.priority }} PRIORITY</span>
                    </div>
                    <span class="badge badge-{{ email.category }}">{{ email.category }}</span>
                </div>

                {% if email.reply and email.reply != "No reply needed" %}
                <div class="ai-response">
                    <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-light); margin-bottom: 0.5rem;">ROBOT GENERATED REPLY</div>
                    <div style="white-space: pre-wrap;">{{ email.reply }}</div>
                </div>
                {% endif %}

                <div style="display: flex; gap: 0.5rem; border-top: 1px solid var(--border); padding-top: 1rem;">
                    {% if email.reply and email.reply != "No reply needed" %}
                    <a href="/send/{{ email.id }}" class="btn btn-primary">🚀 Send Reply</a>
                    {% endif %}
                    <a href="/quick_action/{{ email.id }}/archive" class="btn btn-secondary">📦 Archive</a>
                    <a href="/quick_action/{{ email.id }}/delete" class="btn btn-danger">🗑️ Delete</a>
                    <a href="/quick_action/{{ email.id }}/snooze" class="btn btn-secondary">⏰ Snooze 24h</a>
                    <a href="/quick_action/{{ email.id }}/archive_similar" class="btn btn-secondary">🧹 Archive Similar</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def home():
    check_snoozed_emails()
    
    display_emails = []
    for eid, data in EMAIL_CACHE.items():
        if eid not in SNOOZED_EMAILS:
            display_emails.append({**data, 'id': eid})
            
    priority_map = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    display_emails.sort(key=lambda x: priority_map.get(x['priority'], 3))
    
    msg = session.pop('msg', None)
    
    return render_template_string(
        HTML,
        emails=display_emails,
        analytics=ANALYTICS_DATA,
        autopilot=AUTO_PILOT_SETTINGS,
        total_emails=len(display_emails),
        msg=msg
    )

@app.route('/scan')
def scan():
    raw = gmail_service.fetch_unread_emails(max_results=15)
    
    if raw:
        processed_count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(process_email, email) for email in raw]
            for f in as_completed(futures):
                if f.result(): processed_count += 1
        
        session['msg'] = f"Scanned and processed {processed_count} emails."
        if AUTO_PILOT_SETTINGS['enabled']:
            session['msg'] += " Auto-pilot actions applied."
    else:
        ANALYTICS_DATA['inbox_zero_streak'] += 1
        session['msg'] = "No new emails found. Inbox Zero maintained! 🎉"
        
    save_data()
    return redirect(url_for('home'))

@app.route('/toggle_autopilot')
def toggle_autopilot():
    AUTO_PILOT_SETTINGS['enabled'] = not AUTO_PILOT_SETTINGS['enabled']
    save_data()
    session['msg'] = f"Auto-Pilot {'Enabled' if AUTO_PILOT_SETTINGS['enabled'] else 'Disabled'}"
    return redirect(url_for('home'))

@app.route('/toggle_rule/<rule_name>')
def toggle_rule(rule_name):
    if rule_name in AUTO_PILOT_SETTINGS['rules']:
        AUTO_PILOT_SETTINGS['rules'][rule_name] = not AUTO_PILOT_SETTINGS['rules'][rule_name]
        save_data()
    return redirect(url_for('home'))

@app.route('/quick_action/<email_id>/<action>')
def quick_action(email_id, action):
    if email_id not in EMAIL_CACHE:
        return redirect(url_for('home'))
        
    try:
        if action == 'archive':
            gmail_service.archive_email(email_id)
            del EMAIL_CACHE[email_id]
            session['msg'] = "Email archived."

        elif action == 'delete':
            gmail_service.delete_email(email_id)
            del EMAIL_CACHE[email_id]
            session['msg'] = "Email moved to trash."
            
        elif action == 'snooze':
            wake_time = (datetime.now() + timedelta(days=1)).isoformat()
            SNOOZED_EMAILS[email_id] = wake_time
            session['msg'] = "Email snoozed for 24 hours. It will reappear tomorrow."
            
        elif action == 'archive_similar':
            sender = EMAIL_CACHE[email_id]['sender']
            count = 0
            to_remove = []
            for eid, data in EMAIL_CACHE.items():
                if data['sender'] == sender:
                    gmail_service.archive_email(eid)
                    to_remove.append(eid)
                    count += 1
            
            for eid in to_remove:
                del EMAIL_CACHE[eid]
            session['msg'] = f"Archived {count} emails from {sender}."
            
        save_data()
    except Exception as e:
        logger.error(f"Action error: {e}")
        session['msg'] = "Error performing action."
        
    return redirect(url_for('home'))

@app.route('/send/<email_id>')
def send_reply(email_id):
    if email_id in EMAIL_CACHE:
        data = EMAIL_CACHE[email_id]
        try:
            gmail_service.send_email_reply(data['sender'], data['subject'], data['reply'])
            session['msg'] = "Reply sent successfully!"
        except Exception as e:
            session['msg'] = f"Error sending reply: {e}"
    return redirect(url_for('home'))

@app.route('/clear')
def clear():
    global EMAIL_CACHE
    EMAIL_CACHE = {}
    save_data()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    if os.path.exists('token.json'):
        os.remove('token.json')
    return redirect(url_for('home'))

if __name__ == '__main__':
    print("🚀 STARTING ULTIMATE AI INBOX V2.2")
    app.run(debug=True, port=5000)