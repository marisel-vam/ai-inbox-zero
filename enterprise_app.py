"""
AI INBOX ZERO - ENTERPRISE EDITION
Modern, production-grade email management with AI-powered automation
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from db_manager import DatabaseManager
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enterprise_inbox.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket connection manager for real-time updates"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("="*60)
    logger.info("AI INBOX ZERO - ENTERPRISE EDITION")
    logger.info("="*60)
    
    try:
        Config.validate()
        Config.display()
    except ValueError as e:
        logger.error(str(e))
        raise
    
    app.state.gmail = GmailService()
    app.state.analyzer = EmailAnalyzer()
    app.state.db = DatabaseManager(Config.DATABASE_PATH)
    app.state.manager = ConnectionManager()
    app.state.processing = False
    
    logger.info("✅ All services initialized successfully")
    logger.info(f"🌐 Starting server on {Config.HOST}:{Config.PORT}")
    
    yield
    
    logger.info("Shutting down services...")


app = FastAPI(title="AI Inbox Zero Enterprise", lifespan=lifespan)


class ScanRequest(BaseModel):
    max_emails: Optional[int] = 20
    auto_draft: Optional[bool] = True


class AutoPilotRequest(BaseModel):
    archive_newsletters: bool = True
    delete_spam: bool = True
    auto_reply: bool = False


class EmailActionRequest(BaseModel):
    email_ids: List[str]
    action: str


def process_single_email(email: Dict, analyzer: EmailAnalyzer, gmail: GmailService, 
                        db: DatabaseManager, auto_draft: bool = True) -> Optional[Dict]:
    """Process a single email with AI analysis"""
    email_id = email['id']
    
    try:
        existing = db.get_email_analysis(email_id)
        if existing:
            logger.info(f"Email {email_id} already processed, using cached result")
            return existing
        
        logger.info(f"Analyzing email: {email['subject'][:60]}")
        
        ai_result = analyzer.analyze_email(
            email['sender'],
            email['subject'],
            email.get('body', email.get('snippet', ''))[:Config.EMAIL_BODY_PREVIEW_LENGTH],
            user_name=Config.USER_NAME
        )
        
        db.save_email_analysis(email_id, email, ai_result)
        
        if auto_draft and ai_result.get('needs_reply') and ai_result.get('reply') != "No reply needed":
            try:
                success = gmail.create_draft_reply(
                    email['sender'],
                    email['subject'],
                    ai_result['reply'],
                    email.get('thread_id')
                )
                if success:
                    logger.info(f"✅ Draft created for {email_id}")
            except Exception as e:
                logger.warning(f"Failed to create draft: {e}")
        
        return {
            'email_id': email_id,
            'sender': email['sender'],
            'subject': email['subject'],
            'category': ai_result.get('category', 'Unknown'),
            'priority': ai_result.get('priority', 'Medium'),
            'reply': ai_result.get('reply', 'No reply needed'),
            'needs_reply': ai_result.get('needs_reply', False),
            'reasoning': ai_result.get('reasoning', ''),
            'processed_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing email {email_id}: {str(e)}", exc_info=True)
        return None


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main application UI"""
    with open("enterprise_ui.html", "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.get("/api/stats")
async def get_stats(request: Request):
    """Get dashboard statistics"""
    try:
        db: DatabaseManager = request.app.state.db
        
        recent_emails = db.get_recent_emails(limit=1000, include_deleted=False)
        all_emails = db.get_recent_emails(limit=10000, include_deleted=True)
        
        total = len(recent_emails)
        by_category = {'Important': 0, 'Personal': 0, 'Newsletter': 0, 'Spam': 0, 'Unknown': 0}
        by_priority = {'High': 0, 'Medium': 0, 'Low': 0}
        needs_reply_count = 0
        
        archived_count = 0
        deleted_count = 0
        sent_count = 0
        
        for email in recent_emails:
            cat = email.get('category', 'Unknown')
            if cat in by_category:
                by_category[cat] += 1
            
            pri = email.get('priority', 'Medium')
            if pri in by_priority:
                by_priority[pri] += 1
            
            if email.get('needs_reply'):
                needs_reply_count += 1
        
        for email in all_emails:
            if email.get('archived'):
                archived_count += 1
            if email.get('deleted'):
                deleted_count += 1
            if email.get('sent'):
                sent_count += 1
        
        time_saved = sent_count * 5 + archived_count * 2
        
        return {
            "total_emails": total,
            "categories": by_category,
            "priorities": by_priority,
            "needs_reply": needs_reply_count,
            "time_saved_minutes": time_saved,
            "replies_sent": sent_count,
            "archived": archived_count,
            "deleted": deleted_count,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        return {
            "total_emails": 0,
            "categories": {},
            "priorities": {},
            "needs_reply": 0,
            "time_saved_minutes": 0,
            "replies_sent": 0,
            "archived": 0,
            "deleted": 0,
            "error": str(e)
        }


@app.get("/api/emails")
async def get_emails(
    request: Request,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    needs_reply: Optional[bool] = None,
    limit: int = 50,
    search: Optional[str] = None
):
    """Get emails with filtering"""
    try:
        db: DatabaseManager = request.app.state.db
        emails = db.get_recent_emails(limit=limit, include_deleted=False)
        
        if category and category != "All":
            emails = [e for e in emails if e.get('category') == category]
        
        if priority and priority != "All":
            emails = [e for e in emails if e.get('priority') == priority]
        
        if needs_reply is not None:
            emails = [e for e in emails if e.get('needs_reply') == needs_reply]
        
        if search:
            search_lower = search.lower()
            emails = [
                e for e in emails 
                if search_lower in e.get('subject', '').lower() 
                or search_lower in e.get('sender', '').lower()
            ]
        
        for email in emails:
            try:
                if email.get('ai_response'):
                    parsed = json.loads(email['ai_response'])
                    email['reply'] = parsed.get('reply', '')
                    email['reasoning'] = parsed.get('reasoning', '')
            except:
                pass
        
        return {
            "emails": emails,
            "count": len(emails),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting emails: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scan")
async def scan_inbox(request: Request, scan_req: ScanRequest, background_tasks: BackgroundTasks):
    """Scan inbox and process emails"""
    if request.app.state.processing:
        return {
            "status": "already_processing",
            "message": "Email scan already in progress"
        }
    
    try:
        request.app.state.processing = True
        
        gmail: GmailService = request.app.state.gmail
        analyzer: EmailAnalyzer = request.app.state.analyzer
        db: DatabaseManager = request.app.state.db
        manager: ConnectionManager = request.app.state.manager
        
        await manager.broadcast({
            "type": "scan_started",
            "message": "Starting email scan..."
        })
        
        raw_emails = gmail.fetch_unread_emails(max_results=scan_req.max_emails)
        
        if not raw_emails:
            request.app.state.processing = False
            await manager.broadcast({
                "type": "scan_completed",
                "count": 0,
                "message": "No new emails found"
            })
            return {
                "status": "success",
                "emails_found": 0,
                "emails_processed": 0,
                "message": "No new emails to process"
            }
        
        logger.info(f"Found {len(raw_emails)} unread emails")
        
        await manager.broadcast({
            "type": "scan_progress",
            "total": len(raw_emails),
            "processed": 0
        })
        
        processed_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(
                    process_single_email,
                    email,
                    analyzer,
                    gmail,
                    db,
                    scan_req.auto_draft
                )
                for email in raw_emails
            ]
            
            for i, future in enumerate(futures, 1):
                result = future.result()
                if result:
                    processed_count += 1
                
                await manager.broadcast({
                    "type": "scan_progress",
                    "total": len(raw_emails),
                    "processed": i
                })
        
        request.app.state.processing = False
        
        await manager.broadcast({
            "type": "scan_completed",
            "count": processed_count,
            "message": f"Successfully processed {processed_count} emails"
        })
        
        return {
            "status": "success",
            "emails_found": len(raw_emails),
            "emails_processed": processed_count,
            "message": f"Successfully processed {processed_count} out of {len(raw_emails)} emails"
        }
        
    except Exception as e:
        request.app.state.processing = False
        logger.error(f"Error during scan: {e}", exc_info=True)
        
        await manager.broadcast({
            "type": "error",
            "message": f"Scan failed: {str(e)}"
        })
        
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auto-pilot")
async def auto_pilot(request: Request, pilot_req: AutoPilotRequest):
    """Execute auto-pilot actions"""
    try:
        db: DatabaseManager = request.app.state.db
        gmail: GmailService = request.app.state.gmail
        
        emails = db.get_recent_emails(limit=100, include_deleted=False)
        
        logger.info(f"Auto-pilot: Found {len(emails)} emails to process")
        
        archived_count = 0
        deleted_count = 0
        replied_count = 0
        
        newsletter_count = sum(1 for e in emails if e.get('category') == 'Newsletter')
        spam_count = sum(1 for e in emails if e.get('category') == 'Spam')
        logger.info(f"Auto-pilot: {newsletter_count} newsletters, {spam_count} spam emails found")
        
        for email in emails:
            email_id = email['email_id']
            category = email.get('category', '')
            subject = email.get('subject', 'No subject')
            
            if pilot_req.archive_newsletters and category == 'Newsletter':
                logger.info(f"Auto-pilot: Deleting newsletter '{subject}' (ID: {email_id})")
                if gmail.delete_email(email_id):
                    db.mark_as_deleted(email_id)
                    deleted_count += 1
                    logger.info(f"✅ Deleted newsletter: {email_id}")
                else:
                    logger.error(f"❌ Failed to delete newsletter: {email_id}")
            
            if pilot_req.delete_spam and category == 'Spam':
                logger.info(f"Auto-pilot: Deleting spam '{subject}' (ID: {email_id})")
                if gmail.delete_email(email_id):
                    db.mark_as_deleted(email_id)
                    deleted_count += 1
                    logger.info(f"✅ Deleted spam: {email_id}")
                else:
                    logger.error(f"❌ Failed to delete spam: {email_id}")
            
            if pilot_req.auto_reply and email.get('needs_reply') and not email.get('sent'):
                try:
                    reply = email.get('clean_reply', '')
                    if reply and reply != "No reply needed":
                        sender = email.get('sender', '')
                        subject = email.get('subject', '')
                        thread_id = email.get('thread_id', '')
                        
                        if gmail.send_email_reply(sender, subject, reply, thread_id):
                            db.mark_as_sent(email_id)
                            replied_count += 1
                except Exception as e:
                    logger.warning(f"Auto-reply failed for {email_id}: {e}")
        
        return {
            "status": "success",
            "archived": archived_count,
            "deleted": deleted_count,
            "replied": replied_count,
            "message": f"Auto-pilot completed: {deleted_count} deleted, {replied_count} replied"
        }
        
    except Exception as e:
        logger.error(f"Auto-pilot error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/{email_id}/send")
async def send_email(request: Request, email_id: str):
    """Send email reply"""
    try:
        db: DatabaseManager = request.app.state.db
        gmail: GmailService = request.app.state.gmail
        
        email = db.get_email_analysis(email_id)
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        reply = email.get('clean_reply', '')
        if not reply or reply == "No reply needed":
            raise HTTPException(status_code=400, detail="No reply available")
        
        success = gmail.send_email_reply(
            email['sender'],
            email['subject'],
            reply,
            email.get('thread_id')
        )
        
        if success:
            db.mark_as_sent(email_id)
            return {
                "status": "success",
                "message": "Reply sent successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send reply")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/{email_id}/archive")
async def archive_email(request: Request, email_id: str):
    """Archive an email"""
    try:
        db: DatabaseManager = request.app.state.db
        gmail: GmailService = request.app.state.gmail
        
        if gmail.archive_email(email_id):
            db.mark_as_archived(email_id)
            return {"status": "success", "message": "Email archived"}
        else:
            raise HTTPException(status_code=500, detail="Failed to archive email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/{email_id}/delete")
async def delete_email(request: Request, email_id: str):
    """Delete an email"""
    try:
        db: DatabaseManager = request.app.state.db
        gmail: GmailService = request.app.state.gmail
        
        if gmail.delete_email(email_id):
            db.mark_as_deleted(email_id)
            return {"status": "success", "message": "Email deleted"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete email")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/{email_id}/mark-read")
async def mark_read(request: Request, email_id: str):
    """Mark email as read"""
    try:
        gmail: GmailService = request.app.state.gmail
        
        if gmail.mark_as_read(email_id):
            return {"status": "success", "message": "Email marked as read"}
        else:
            raise HTTPException(status_code=500, detail="Failed to mark as read")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch")
async def batch_action(request: Request, action_req: EmailActionRequest):
    """Perform batch actions on multiple emails"""
    try:
        db: DatabaseManager = request.app.state.db
        gmail: GmailService = request.app.state.gmail
        
        success_count = 0
        failed_count = 0
        
        for email_id in action_req.email_ids:
            try:
                if action_req.action == "archive":
                    if gmail.archive_email(email_id):
                        db.mark_as_archived(email_id)
                        success_count += 1
                    else:
                        failed_count += 1
                        
                elif action_req.action == "delete":
                    if gmail.delete_email(email_id):
                        db.mark_as_deleted(email_id)
                        success_count += 1
                    else:
                        failed_count += 1
                        
                elif action_req.action == "mark_read":
                    if gmail.mark_as_read(email_id):
                        success_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.warning(f"Batch action failed for {email_id}: {e}")
                failed_count += 1
        
        return {
            "status": "success",
            "processed": success_count + failed_count,
            "success": success_count,
            "failed": failed_count,
            "message": f"Batch action completed: {success_count} succeeded, {failed_count} failed"
        }
        
    except Exception as e:
        logger.error(f"Batch action error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics")
async def get_analytics(request: Request, days: int = 30):
    """Get detailed analytics"""
    try:
        db: DatabaseManager = request.app.state.db
        analytics = db.get_analytics(days=days)
        
        return {
            "summary": analytics['summary'],
            "daily": analytics['daily'],
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    manager: ConnectionManager = websocket.app.state.manager
    await manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.post("/api/logout")
async def logout():
    """Logout and clear credentials"""
    try:
        if os.path.exists('token.json'):
            os.remove('token.json')
            logger.info("User logged out, token removed")
        return {"status": "success", "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/preferences")
async def get_preferences(request: Request):
    """Get user preferences"""
    try:
        db: DatabaseManager = request.app.state.db
        
        return {
            "auto_draft": db.get_preference("auto_draft", "true") == "true",
            "auto_archive_newsletters": db.get_preference("auto_archive_newsletters", "false") == "true",
            "auto_delete_spam": db.get_preference("auto_delete_spam", "false") == "true",
            "max_emails_per_scan": int(db.get_preference("max_emails_per_scan", "20")),
            "user_name": db.get_preference("user_name", Config.USER_NAME)
        }
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        return {}


@app.post("/api/preferences")
async def save_preferences(request: Request, preferences: Dict):
    """Save user preferences"""
    try:
        db: DatabaseManager = request.app.state.db
        
        for key, value in preferences.items():
            db.set_preference(key, str(value))
        
        return {"status": "success", "message": "Preferences saved"}
    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=Config.HOST,
        port=Config.PORT,
        log_level="info"
    )
