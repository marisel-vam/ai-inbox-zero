
import os.path
import base64
import logging
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class GmailService:
    """Enhanced Gmail service with better error handling and features"""
    
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self._service = None
    
    @property
    def service(self):
        """Lazy load Gmail service"""
        if self._service is None:
            self._service = self._get_service()
        return self._service
    
    def _get_service(self):
        """Authenticate and return Gmail service"""
        creds = None
        
        # Load existing credentials
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.info("Loaded credentials from token file")
            except Exception as e:
                logger.error(f"Error loading credentials: {e}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new credentials")
            
            # Save credentials
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        return build('gmail', 'v1', credentials=creds)
    
    def fetch_unread_emails(self, max_results=20, label_ids=None) -> List[Dict]:
        """
        Fetch unread emails from inbox
        
        Args:
            max_results: Maximum number of emails to fetch
            label_ids: List of label IDs to filter (default: ['INBOX', 'UNREAD'])
            
        Returns:
            List of email dictionaries
        """
        if label_ids is None:
            label_ids = ['INBOX', 'UNREAD']
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=label_ids,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} unread emails")
            
            email_data = []
            for msg in messages:
                try:
                    email = self._get_email_details(msg['id'])
                    if email:
                        email_data.append(email)
                except Exception as e:
                    logger.error(f"Error fetching email {msg['id']}: {e}")
                    continue
            
            return email_data
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information about an email"""
        try:
            msg_details = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = msg_details['payload']['headers']
            
            # Extract headers
            subject = self._get_header_value(headers, 'Subject') or 'No Subject'
            sender = self._get_header_value(headers, 'From') or 'Unknown'
            to = self._get_header_value(headers, 'To') or ''
            date = self._get_header_value(headers, 'Date') or ''
            
            # Get email body
            body = self._get_email_body(msg_details['payload'])
            snippet = msg_details.get('snippet', '')
            
            # Get labels
            labels = msg_details.get('labelIds', [])
            
            return {
                'id': message_id,
                'sender': sender,
                'to': to,
                'subject': subject,
                'snippet': snippet,
                'body': body,
                'date': date,
                'labels': labels,
                'thread_id': msg_details.get('threadId', '')
            }
            
        except HttpError as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None
    
    def _get_header_value(self, headers: List[Dict], name: str) -> Optional[str]:
        """Extract header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None
    
    def _get_email_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return body
    
    def create_draft_reply(self, to: str, subject: str, reply_text: str, 
                          thread_id: Optional[str] = None) -> bool:
        """
        Create a draft reply
        
        Args:
            to: Recipient email address
            subject: Email subject
            reply_text: Reply message body
            thread_id: Thread ID for threading replies
            
        Returns:
            bool: True if successful
        """
        try:
            message = MIMEText(reply_text)
            message['to'] = to
            message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft_body = {'message': {'raw': raw_message}}
            if thread_id:
                draft_body['message']['threadId'] = thread_id
            
            self.service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            
            logger.info(f"Draft created for {to}")
            return True
            
        except HttpError as e:
            logger.error(f"Error creating draft: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating draft: {e}")
            return False
    
    def send_email_reply(self, to: str, subject: str, reply_text: str,
                        thread_id: Optional[str] = None) -> bool:
        """
        Send an email reply
        
        Args:
            to: Recipient email address
            subject: Email subject
            reply_text: Reply message body
            thread_id: Thread ID for threading replies
            
        Returns:
            bool: True if successful
        """
        try:
            message = MIMEText(reply_text)
            message['to'] = to
            message['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            send_body = {'raw': raw_message}
            if thread_id:
                send_body['threadId'] = thread_id
            
            self.service.users().messages().send(
                userId='me',
                body=send_body
            ).execute()
            
            logger.info(f"Email sent to {to}")
            return True
            
        except HttpError as e:
            logger.error(f"Error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            return False
    
    def archive_email(self, message_id: str) -> bool:
        """Archive email by removing INBOX label"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            logger.info(f"Archived message {message_id}")
            return True
        except HttpError as e:
            logger.error(f"Error archiving email: {e}")
            return False
    
    def delete_email(self, message_id: str) -> bool:
        """Move email to trash"""
        try:
            result = self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            logger.info(f"✅ Trashed message {message_id} - API response: {result.get('id')}")
            return True
        except HttpError as e:
            logger.error(f"❌ Error deleting email {message_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error deleting email {message_id}: {e}")
            return False
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked message {message_id} as read")
            return True
        except HttpError as e:
            logger.error(f"Error marking as read: {e}")
            return False
    
    def add_label(self, message_id: str, label_id: str) -> bool:
        """Add a label to an email"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            logger.info(f"Added label {label_id} to message {message_id}")
            return True
        except HttpError as e:
            logger.error(f"Error adding label: {e}")
            return False


# Legacy functions for backward compatibility
_service_instance = None

def get_gmail_service():
    """Get Gmail service instance"""
    global _service_instance
    if _service_instance is None:
        _service_instance = GmailService()
    return _service_instance.service

def fetch_unread_emails(max_results=20):
    """Legacy function"""
    service = GmailService()
    return service.fetch_unread_emails(max_results)

def create_draft_reply(sender, subject, reply_text):
    """Legacy function"""
    service = GmailService()
    return service.create_draft_reply(sender, subject, reply_text)

def send_email_reply(sender, subject, reply_text):
    """Legacy function"""
    service = GmailService()
    return service.send_email_reply(sender, subject, reply_text)

def archive_email_api(message_id):
    """Legacy function"""
    service = GmailService()
    return service.archive_email(message_id)

def delete_email_api(message_id):
    """Legacy function"""
    service = GmailService()
    return service.delete_email(message_id)
# In gmail_service.py, add retry logic:
def create_draft_reply(self, to, subject, reply_text, thread_id=None, retries=3):
    for attempt in range(retries):
        try:
            # existing code...
            return True
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
                continue
            logger.error(f"Draft creation failed: {e}")
            return False