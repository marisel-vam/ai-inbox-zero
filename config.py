"""
Configuration file for AI Inbox Zero
Loads settings from environment variables with sensible defaults
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # Flask Settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT = int(os.getenv('FLASK_PORT', '5000'))
    
    # API Keys
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'inbox_zero.db')
    
    # Gmail API
    GMAIL_CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
    GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
    
    # Email Processing
    MAX_EMAILS_PER_SCAN = int(os.getenv('MAX_EMAILS', '20'))
    USER_NAME = os.getenv('USER_NAME', 'Mariselvam M')
    USER_EMAIL = os.getenv('USER_EMAIL', '')
    
    # AI Settings
    AI_MODEL = os.getenv('AI_MODEL', 'llama-3.3-70b-versatile')
    AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.3'))
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '600'))
    
    # Rate Limiting
    RATE_LIMIT_CALLS = int(os.getenv('RATE_LIMIT_CALLS', '10'))
    RATE_LIMIT_PERIOD = int(os.getenv('RATE_LIMIT_PERIOD', '60'))
    
    # Processing Settings
    EMAIL_BODY_PREVIEW_LENGTH = int(os.getenv('EMAIL_BODY_PREVIEW_LENGTH', '1500'))
    PROCESSING_DELAY = float(os.getenv('PROCESSING_DELAY', '0.5'))  # seconds between emails
    
    # Feature Flags
    ENABLE_ANALYTICS = os.getenv('ENABLE_ANALYTICS', 'True').lower() == 'true'
    ENABLE_AUTO_ARCHIVE = os.getenv('ENABLE_AUTO_ARCHIVE', 'False').lower() == 'true'
    ENABLE_AUTO_DRAFT = os.getenv('ENABLE_AUTO_DRAFT', 'True').lower() == 'true'
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'ai_inbox.log')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        errors = []
        
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required. Set it in .env file.")
        
        if not os.path.exists(cls.GMAIL_CREDENTIALS_FILE):
            errors.append(f"{cls.GMAIL_CREDENTIALS_FILE} not found. Download from Google Cloud Console.")
        
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production' and not cls.DEBUG:
            errors.append("FLASK_SECRET_KEY should be changed for production.")
        
        if errors:
            error_msg = "\n❌ Configuration Errors:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
        
        return True
    
    @classmethod
    def display(cls):
        """Display current configuration (safe values only)"""
        print("\n" + "="*60)
        print("AI Inbox Zero - Configuration")
        print("="*60)
        print(f"Flask Debug Mode: {cls.DEBUG}")
        print(f"Host: {cls.HOST}")
        print(f"Port: {cls.PORT}")
        print(f"Database: {cls.DATABASE_PATH}")
        print(f"Max Emails: {cls.MAX_EMAILS_PER_SCAN}")
        print(f"AI Model: {cls.AI_MODEL}")
        print(f"User Name: {cls.USER_NAME}")
        print(f"Rate Limit: {cls.RATE_LIMIT_CALLS} calls per {cls.RATE_LIMIT_PERIOD}s")
        print(f"Analytics: {'Enabled' if cls.ENABLE_ANALYTICS else 'Disabled'}")
        print(f"Auto Draft: {'Enabled' if cls.ENABLE_AUTO_DRAFT else 'Disabled'}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print("="*60 + "\n")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Override defaults for production
    HOST = '0.0.0.0'
    
    @classmethod
    def validate(cls):
        """Additional validation for production"""
        super().validate()
        
        if cls.SECRET_KEY == 'dev-secret-key-change-in-production':
            raise ValueError("Must set FLASK_SECRET_KEY for production!")


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])


if __name__ == '__main__':
    # Test configuration
    try:
        Config.validate()
        Config.display()
        print("✅ Configuration is valid!")
    except ValueError as e:
        print(str(e))