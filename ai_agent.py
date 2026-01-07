import os
import json
import time
from functools import wraps
from groq import Groq
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_inbox.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Rate limiting decorator
def rate_limit(calls=10, period=60):
    """Limit API calls to prevent rate limit errors"""
    def decorator(func):
        calls_made = []
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            calls_made[:] = [c for c in calls_made if c > now - period]
            if len(calls_made) >= calls:
                sleep_time = period - (now - calls_made[0])
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
            calls_made.append(time.time())
            return func(*args, **kwargs)
        return wrapper
    return decorator


class EmailAnalyzer:
    """Enhanced email analyzer with better error handling and structured output"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or GROQ_API_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"
    
    def _is_no_reply_sender(self, sender):
        """Check if sender is a no-reply address"""
        no_reply_patterns = [
            'no-reply', 'noreply', 'donotreply', 'do-not-reply',
            'notifications', 'automated', 'mailer-daemon'
        ]
        sender_lower = sender.lower()
        return any(pattern in sender_lower for pattern in no_reply_patterns)
    
    @rate_limit(calls=30, period=60)  # Increased to 30 calls per minute
    def analyze_email(self, sender, subject, body, user_name="Mariselvam M"):
        """
        Analyze email using AI and return structured response
        
        Args:
            sender: Email sender address
            subject: Email subject line
            body: Email body content
            user_name: Name for email signature
            
        Returns:
            dict: Structured analysis with category, priority, reply, etc.
        """
        try:
            # Quick check for no-reply senders
            if self._is_no_reply_sender(sender):
                logger.info(f"No-reply sender detected: {sender}")
                return {
                    "category": "Newsletter",
                    "priority": "Low",
                    "reply": "No reply needed",
                    "reasoning": "Automated no-reply sender",
                    "needs_reply": False
                }
            
            # Construct the prompt
            prompt = self._build_prompt(sender, subject, body, user_name)
            
            # Call Groq API
            logger.info(f"Analyzing email from {sender}: {subject[:50]}...")
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=600,
                top_p=1,
                stream=False,
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Parse the response
            return self._parse_response(response_text, sender, subject)
            
        except Exception as e:
            logger.error(f"Error analyzing email: {str(e)}", exc_info=True)
            return self._generate_fallback_response(sender, subject, body)
    
    def _build_prompt(self, sender, subject, body, user_name):
        """Build the AI prompt for email analysis - ENHANCED VERSION"""
        return f"""You are an expert executive assistant AI for {user_name}, known for professional, warm, and intelligent communication.

📧 EMAIL TO ANALYZE:
From: {sender}
Subject: {subject}
Preview: {body[:1500]}

🎯 YOUR TASK:
Analyze this email and provide:

1. **Category Classification:**
   - **Important**: Work matters, urgent requests, meetings, deadlines, business opportunities
   - **Personal**: Friends, family, personal contacts, social invitations
   - **Newsletter**: Marketing, updates, subscriptions, promotional content
   - **Spam**: Unsolicited, irrelevant, suspicious, or low-quality content

2. **Priority Level:**
   - **High**: Requires immediate attention, time-sensitive, from important contacts
   - **Medium**: Should respond within 24-48 hours, moderate importance
   - **Low**: Can wait, informational only, or no response needed

3. **Intelligent Reply Draft:**
   
   **CRITICAL RULES FOR REPLIES:**
   
   ✅ **Always draft replies for Important & Personal emails**
   - Be warm, professional, and helpful
   - Address specific points mentioned in the email
   - Show genuine interest and engagement
   - Use natural, conversational language
   - Add relevant questions or next steps when appropriate
   
   ❌ **Never reply to Newsletters or Spam**
   - Simply output: "No reply needed"
   
   **REPLY STYLE GUIDE:**
   - **Tone**: Professional yet friendly, confident but humble
   - **Structure**: 
     * Warm greeting using their name if available
     * Acknowledge their email/request specifically
     * Provide helpful, substantive response
     * Include actionable next steps or questions
     * Professional sign-off
   - **Length**: 3-5 sentences (substantial but concise)
   - **Intelligence**: Show you understood the context, reference specific details
   - **Engagement**: Ask relevant questions, show interest, build relationships
   
   **EXAMPLES OF GREAT REPLIES:**
   
   For meeting request:
   "Hi Sarah! Thanks for reaching out about collaborating on the Q2 campaign. I'm definitely interested in exploring this further. Would Tuesday at 2 PM or Thursday at 10 AM work for a quick call to discuss the scope and timeline? Looking forward to working together on this!"
   
   For project update:
   "Hey Michael, appreciate the detailed update on the website redesign. The mockups look fantastic! I have a few thoughts on the navigation structure - would you be open to a brief review session this week? Also, curious about your timeline for the mobile version. Great work so far!"
   
   For personal invitation:
   "Hi Emma! How wonderful to hear from you! I'd absolutely love to catch up over coffee. It's been way too long! I'm free next week - does Wednesday or Friday afternoon work for you? There's a great new café downtown I've been wanting to try. Can't wait to hear about your new venture!"

📋 OUTPUT FORMAT (strict JSON):
{{
  "category": "Important|Personal|Newsletter|Spam",
  "priority": "High|Medium|Low",
  "reply": "Your drafted reply OR 'No reply needed'",
  "reasoning": "Brief explanation of why you classified it this way",
  "needs_reply": true|false
}}

⚡ REMEMBER: 
- Be intelligent and engaging, not robotic
- Show you actually read and understood the email
- Make replies feel personal and thoughtful
- Sign all replies with: "Best regards,\\n{user_name}" """

    def _parse_response(self, response_text, sender, subject):
        """Parse AI response into structured format"""
        try:
            # Try to extract JSON from response
            if '{' in response_text and '}' in response_text:
                start = response_text.index('{')
                end = response_text.rindex('}') + 1
                json_str = response_text[start:end]
                data = json.loads(json_str)
                
                # Validate required fields
                if 'category' in data and 'reply' in data:
                    # Ensure needs_reply is set correctly
                    if 'needs_reply' not in data:
                        data['needs_reply'] = "No reply needed" not in data['reply']
                    
                    logger.info(f"Successfully parsed response: {data['category']}, Priority: {data.get('priority', 'N/A')}")
                    return data
            
            # Fallback: parse text format
            return self._parse_text_response(response_text)
            
        except Exception as e:
            logger.warning(f"JSON parse failed, using text parser: {str(e)}")
            return self._parse_text_response(response_text)
    
    def _parse_text_response(self, response_text):
        """Parse non-JSON text response"""
        lines = response_text.split('\n')
        category = "Personal"
        priority = "Medium"
        reply = response_text
        reasoning = "Parsed from text format"
        
        for line in lines:
            if line.startswith('Category:'):
                category = line.split(':', 1)[1].strip()
            elif line.startswith('Priority:'):
                priority = line.split(':', 1)[1].strip()
            elif line.startswith('Reply:'):
                reply = line.split(':', 1)[1].strip()
        
        needs_reply = "No reply needed" not in reply
        
        return {
            "category": category,
            "priority": priority,
            "reply": reply,
            "reasoning": reasoning,
            "needs_reply": needs_reply
        }
    
    def _generate_fallback_response(self, sender, subject, body):
        """Generate fallback response when API fails"""
        logger.warning("Using fallback response due to API error")
        
        # Simple heuristic classification
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        
        if any(word in subject_lower for word in ['newsletter', 'unsubscribe', 'promotion']):
            category = "Newsletter"
            reply = "No reply needed"
            needs_reply = False
        else:
            category = "Personal"
            sender_name = sender.split('<')[0].strip() or sender
            reply = f"""Dear {sender_name},

Thank you for your email regarding "{subject}". I have received your message and will review it shortly.

(Note: This is an automated acknowledgment. A detailed response will follow.)

Best regards,
Mariselvam M"""
            needs_reply = True
        
        return {
            "category": category,
            "priority": "Medium",
            "reply": reply,
            "reasoning": "Fallback due to API unavailability",
            "needs_reply": needs_reply,
            "is_fallback": True
        }


# Backward compatibility function
def analyze_email(sender, subject, body):
    """Legacy function for backward compatibility"""
    analyzer = EmailAnalyzer()
    result = analyzer.analyze_email(sender, subject, body)
    
    # Convert to old format for compatibility
    response = f"Category: {result['category']}\n"
    if 'priority' in result:
        response += f"Priority: {result['priority']}\n"
    response += f"Reply: {result['reply']}"
    
    return response


if __name__ == "__main__":
    # Test the analyzer
    analyzer = EmailAnalyzer()
    
    test_cases = [
        ("no-reply@company.com", "Weekly Newsletter", "Check out our updates"),
        ("john.doe@company.com", "Project Deadline Tomorrow", "We need to finalize the report"),
        ("friend@gmail.com", "Coffee next week?", "Hey! Want to catch up?"),
    ]
    
    for sender, subject, body in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {subject}")
        result = analyzer.analyze_email(sender, subject, body)
        print(json.dumps(result, indent=2))