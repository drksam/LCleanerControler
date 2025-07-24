"""
Synchronization handler for LCleanerController integration with Shop Suite.

This module handles synchronization of data between LCleanerController and 
the shared Shop Suite database infrastructure.
"""
import logging
import json
from datetime import datetime
from flask import current_app
from sqlalchemy import text
from main import db, app
from models import SyncEvent, SuiteUser, User, RFIDCard

logger = logging.getLogger(__name__)

class SyncHandler:
    """Handles synchronization between LCleanerController and Shop Suite database."""
    
    @staticmethod
    def initialize_sync():
        """Initialize the synchronization system."""
        logger.info("Initializing Shop Suite synchronization")
        try:
            # Check if PostgreSQL is being used and if schema bindings are available
            if 'postgresql' in current_app.config["SQLALCHEMY_DATABASE_URI"]:
                # Create schemas if they don't exist
                db.session.execute(text("CREATE SCHEMA IF NOT EXISTS cleaner_controller"))
                db.session.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
                db.session.commit()
                logger.info("Database schemas created/verified")
            
            return True
        except Exception as e:
            logger.error(f"Error initializing sync: {e}")
            return False
    
    @staticmethod
    def sync_users():
        """Synchronize users between local database and suite database."""
        logger.info("Synchronizing users with Shop Suite")
        try:
            # Check if we're in PostgreSQL mode with schema bindings
            if 'core' in current_app.config.get("SQLALCHEMY_BINDS", {}):
                # Get all suite users
                suite_users = SuiteUser.query.all()
                
                for suite_user in suite_users:
                    # Create or update local user
                    User.sync_from_suite_user(suite_user)
                
                # Create SyncEvent for any unsynced local users
                local_users = User.query.filter_by(sync_status="pending").all()
                for local_user in local_users:
                    # Create a SuiteUser if one doesn't exist
                    if not local_user.suite_user_id:
                        suite_user = SuiteUser(
                            username=local_user.username,
                            display_name=local_user.full_name,
                            email=local_user.email,
                            active=local_user.active,
                            is_admin=local_user.access_level == 'admin',
                            created_by_app="cleaner_controller",
                            managed_by_app="cleaner_controller"
                        )
                        
                        # If the local user has a password hash, copy it
                        if local_user.password_hash:
                            suite_user.password_hash = local_user.password_hash
                            
                        db.session.add(suite_user)
                        db.session.flush()  # Get the ID without committing
                        
                        # Associate the local user with the suite user
                        local_user.suite_user_id = suite_user.id
                        
                    # Create a sync event
                    sync_event = local_user.to_sync_event("user.updated")
                    db.session.add(sync_event)
                    
                    # Mark as synced
                    local_user.mark_synced()
                
                db.session.commit()
                logger.info("User synchronization completed")
                return True
            else:
                logger.warning("Not in PostgreSQL mode, skipping user synchronization")
                return False
                
        except Exception as e:
            logger.error(f"Error synchronizing users: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def process_pending_sync_events():
        """Process pending synchronization events."""
        logger.info("Processing pending sync events")
        try:
            # Get pending events where this app is the target
            pending_events = SyncEvent.query.filter_by(
                target_app="cleaner_controller",
                status="pending"
            ).order_by(SyncEvent.created_at.asc()).limit(100).all()
            
            for event in pending_events:
                logger.debug(f"Processing sync event: {event.event_type} for {event.resource_type}")
                
                # Process based on event type
                if event.event_type == "user.created" or event.event_type == "user.updated":
                    # A user was created or updated in another app
                    payload = json.loads(event.payload)
                    suite_user_id = payload.get("user_id") or event.resource_id
                    
                    suite_user = SuiteUser.query.get(suite_user_id)
                    if suite_user:
                        User.sync_from_suite_user(suite_user)
                        
                # Mark event as processed
                event.status = "processed"
                event.processed_at = datetime.utcnow()
                
            db.session.commit()
            logger.info(f"Processed {len(pending_events)} sync events")
            return True
        except Exception as e:
            logger.error(f"Error processing sync events: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def sync_access_logs():
        """Send access logs to the suite database for analytics."""
        # This would be implemented based on suite analytics requirements
        pass
    
    @staticmethod
    def report_machine_status():
        """Report this machine's status to the suite database."""
        # This would send the current machine status to the suite for dashboard display
        pass

# Function to register scheduled sync tasks
def register_sync_tasks(app):
    """Register synchronization tasks with the scheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = BackgroundScheduler()
        
        # Add sync jobs with app context wrappers
        def process_sync_with_context():
            with app.app_context():
                SyncHandler.process_pending_sync_events()
        
        def sync_users_with_context():
            with app.app_context():
                SyncHandler.sync_users()
        
        scheduler.add_job(
            func=process_sync_with_context,
            trigger=IntervalTrigger(minutes=5),
            id='process_sync_events',
            name='Process pending sync events',
            replace_existing=True
        )
        
        scheduler.add_job(
            func=sync_users_with_context,
            trigger=IntervalTrigger(minutes=15),
            id='sync_users',
            name='Synchronize users with suite database',
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Sync tasks registered with scheduler")
        return scheduler
    except ImportError:
        logger.warning("APScheduler not installed. Skipping sync task registration.")
        return None
    except Exception as e:
        logger.error(f"Error registering sync tasks: {e}")
        return None