"""
Fast parallel email scanner - processes multiple emails simultaneously
"""
import concurrent.futures
import logging
from typing import List, Dict
from gmail_service import GmailService
from ai_agent import EmailAnalyzer
from db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class FastEmailScanner:
    """Parallel email scanner for faster processing"""
    
    def __init__(self, max_workers=5):
        self.gmail_service = GmailService()
        self.email_analyzer = EmailAnalyzer()
        self.db = DatabaseManager()
        self.max_workers = max_workers
    
    def process_single_email(self, email: Dict) -> Dict:
        """Process a single email"""
        email_id = email['id']
        
        try:
            # Check if already processed
            existing = self.db.get_email_analysis(email_id)
            if existing:
                logger.info(f"✓ Cached: {email['subject'][:40]}")
                return {'status': 'cached', 'email_id': email_id}
            
            # Analyze with AI
            logger.info(f"⚡ Analyzing: {email['subject'][:40]}...")
            ai_result = self.email_analyzer.analyze_email(
                email['sender'],
                email['subject'],
                email.get('body', email.get('snippet', ''))
            )
            
            # Save to database
            self.db.save_email_analysis(email_id, email, ai_result)
            
            # Create draft if needed
            if ai_result.get('needs_reply') and ai_result.get('reply'):
                self.gmail_service.create_draft_reply(
                    email['sender'],
                    email['subject'],
                    ai_result['reply'],
                    email.get('thread_id')
                )
            
            logger.info(f"✓ Done: {email['subject'][:40]}")
            return {'status': 'processed', 'email_id': email_id, 'category': ai_result.get('category')}
            
        except Exception as e:
            logger.error(f"✗ Error processing {email_id}: {e}")
            return {'status': 'error', 'email_id': email_id, 'error': str(e)}
    
    def scan_parallel(self, max_emails=20) -> Dict:
        """Scan and process emails in parallel"""
        logger.info("🚀 Starting FAST parallel scan...")
        
        # Fetch emails
        emails = self.gmail_service.fetch_unread_emails(max_results=max_emails)
        total = len(emails)
        
        if total == 0:
            logger.info("✅ No unread emails")
            return {'total': 0, 'processed': 0, 'cached': 0, 'errors': 0}
        
        logger.info(f"📧 Found {total} emails - processing in parallel...")
        
        # Process in parallel
        results = {'processed': 0, 'cached': 0, 'errors': 0, 'total': total}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_email = {
                executor.submit(self.process_single_email, email): email 
                for email in emails
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_email):
                result = future.result()
                if result['status'] == 'processed':
                    results['processed'] += 1
                elif result['status'] == 'cached':
                    results['cached'] += 1
                elif result['status'] == 'error':
                    results['errors'] += 1
        
        logger.info(f"✅ Scan complete! Processed: {results['processed']}, Cached: {results['cached']}, Errors: {results['errors']}")
        return results


def quick_scan(max_emails=20):
    """Quick function to scan emails"""
    scanner = FastEmailScanner(max_workers=5)
    return scanner.scan_parallel(max_emails)


if __name__ == '__main__':
    # Test the fast scanner
    import time
    start = time.time()
    results = quick_scan(max_emails=20)
    duration = time.time() - start
    print(f"\n⚡ Completed in {duration:.1f} seconds")
    print(f"📊 Results: {results}")