#!/usr/bin/env python
"""
Migration script to convert history.json to SQLite database
Run this once when upgrading from the old JSON-based version
"""

import json
import os
import logging
from db_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_json_to_sqlite():
    """Migrate history.json to SQLite database"""
    
    json_file = 'history.json'
    
    # Check if history.json exists
    if not os.path.exists(json_file):
        logger.warning(f"{json_file} not found. Nothing to migrate.")
        return
    
    # Initialize database
    db = DatabaseManager()
    
    try:
        # Load JSON data
        with open(json_file, 'r') as f:
            history = json.load(f)
        
        logger.info(f"Found {len(history)} emails in {json_file}")
        
        migrated = 0
        skipped = 0
        
        # Migrate each email
        for email_id, email_data in history.items():
            try:
                # Parse the old format
                ai_response = email_data.get('ai_response', '')
                clean_reply = email_data.get('clean_reply', '')
                
                # Extract category from response
                category = 'Unknown'
                if 'Category:' in ai_response:
                    for line in ai_response.split('\n'):
                        if line.startswith('Category:'):
                            category = line.split(':', 1)[1].strip()
                            break
                
                # Determine if reply is needed
                needs_reply = clean_reply and 'No reply needed' not in clean_reply
                
                # Create structured AI result
                ai_result = {
                    'category': category,
                    'priority': 'Medium',  # Default for migrated data
                    'reply': clean_reply or 'No reply needed',
                    'reasoning': 'Migrated from history.json',
                    'needs_reply': needs_reply
                }
                
                # Create email data structure
                email_info = {
                    'sender': 'unknown@example.com',  # Not stored in old format
                    'subject': 'Migrated Email',
                    'snippet': '',
                    'thread_id': ''
                }
                
                # Save to database
                success = db.save_email_analysis(
                    email_id,
                    email_info,
                    ai_result
                )
                
                if success:
                    migrated += 1
                else:
                    skipped += 1
                    logger.warning(f"Failed to migrate {email_id}")
                
            except Exception as e:
                logger.error(f"Error migrating email {email_id}: {e}")
                skipped += 1
        
        logger.info(f"Migration complete! Migrated: {migrated}, Skipped: {skipped}")
        
        # Ask user if they want to backup and remove the old file
        response = input(f"\nMigration successful. Backup and remove {json_file}? (y/n): ")
        if response.lower() == 'y':
            backup_file = f"{json_file}.backup"
            os.rename(json_file, backup_file)
            logger.info(f"Backed up to {backup_file}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing {json_file}: {e}")
    except Exception as e:
        logger.error(f"Migration failed: {e}")


def verify_migration():
    """Verify the migration was successful"""
    db = DatabaseManager()
    
    try:
        emails = db.get_recent_emails(limit=1000)
        logger.info(f"Database contains {len(emails)} emails")
        
        # Show category breakdown
        categories = {}
        for email in emails:
            cat = email.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        logger.info("Category breakdown:")
        for category, count in categories.items():
            logger.info(f"  {category}: {count}")
        
        return True
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("AI Inbox Zero - History Migration Tool")
    print("=" * 60)
    print("\nThis will migrate your history.json to SQLite database.")
    print("Your existing data will be preserved.\n")
    
    response = input("Continue? (y/n): ")
    if response.lower() == 'y':
        migrate_json_to_sqlite()
        print("\nVerifying migration...")
        if verify_migration():
            print("\n✅ Migration completed successfully!")
        else:
            print("\n⚠️  Please verify the database manually.")
    else:
        print("Migration cancelled.")