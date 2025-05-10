"""
Webhook event delivery system for LCleanerController integration with ShopTracker.

This module handles sending real-time event notifications to external systems
through webhook endpoints as described in MM_API_DOCUMENTATION.md.
"""
import json
import logging
import requests
import threading
from datetime import datetime
from flask import current_app
from config import get_rfid_config

logger = logging.getLogger(__name__)

class WebhookHandler:
    """Handler for delivering webhook events to external systems."""
    
    # Define available event types
    EVENT_TYPES = {
        "machine.login": "User logged in to the machine",
        "machine.logout": "User logged out of the machine",
        "machine.status_change": "Machine status changed",
        "alert.created": "New alert was created",
        "node.status_change": "Node status changed"
    }
    
    def __init__(self):
        """Initialize the webhook handler."""
        self.config = get_rfid_config()
        self.webhook_urls = []
        self.machine_id = self.config.get('machine_id', 'laser_room_1')
        self.api_key = self.config.get('api_key', '')
        
        # Queue for failed webhook events to retry
        self.retry_queue = []
        self.max_retries = 3
        
        # Load webhook configuration
        self._load_webhook_config()
    
    def _load_webhook_config(self):
        """Load webhook configuration from settings."""
        try:
            # Get webhook URLs from config or environment
            # For now, we'll just check if server_url is set and use that as our webhook target
            server_url = self.config.get('server_url', '')
            if server_url:
                webhook_url = f"{server_url.rstrip('/')}/webhooks"
                self.webhook_urls.append(webhook_url)
                logger.info(f"Webhook target configured: {webhook_url}")
        except Exception as e:
            logger.error(f"Error loading webhook configuration: {e}")
    
    def send_event(self, event_type, data, retries=0):
        """
        Send an event to all configured webhook endpoints.
        
        Args:
            event_type (str): Type of event (must be in EVENT_TYPES)
            data (dict): Event data payload
            retries (int): Current retry count for this event
        
        Returns:
            bool: True if sent successfully to at least one endpoint
        """
        if event_type not in self.EVENT_TYPES:
            logger.error(f"Invalid event type: {event_type}")
            return False
            
        if not self.webhook_urls:
            logger.warning("No webhook URLs configured. Event not sent.")
            return False
            
        # Create webhook payload
        payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Add machine identifier to all events
        if "machine_id" not in data:
            data["machine_id"] = self.machine_id
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        success = False
        
        # Send to all configured webhook endpoints
        for webhook_url in self.webhook_urls:
            try:
                # Use a background thread to avoid blocking the main thread
                thread = threading.Thread(
                    target=self._send_webhook_request,
                    args=(webhook_url, headers, payload, retries)
                )
                thread.daemon = True
                thread.start()
                success = True
            except Exception as e:
                logger.error(f"Error dispatching webhook event: {e}")
                
        return success
    
    def _send_webhook_request(self, url, headers, payload, retries):
        """Send the actual webhook request in a background thread."""
        try:
            logger.debug(f"Sending webhook to {url}: {payload['event']}")
            response = requests.post(
                url, 
                headers=headers,
                json=payload,
                timeout=5
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook delivered successfully: {payload['event']}")
                return True
            else:
                logger.warning(f"Webhook delivery failed with status {response.status_code}: {response.text}")
                
                # Add to retry queue if we haven't exceeded max retries
                if retries < self.max_retries:
                    self.retry_queue.append({
                        "url": url,
                        "headers": headers,
                        "payload": payload,
                        "retries": retries + 1
                    })
                return False
                
        except requests.RequestException as e:
            logger.error(f"Webhook request error: {e}")
            # Add to retry queue if we haven't exceeded max retries
            if retries < self.max_retries:
                self.retry_queue.append({
                    "url": url,
                    "headers": headers,
                    "payload": payload,
                    "retries": retries + 1
                })
            return False
    
    def retry_failed_webhooks(self):
        """Retry sending failed webhook events."""
        if not self.retry_queue:
            return
            
        logger.info(f"Retrying {len(self.retry_queue)} failed webhook events")
        
        # Make a copy of the retry queue and clear it
        retry_items = self.retry_queue.copy()
        self.retry_queue = []
        
        # Process each failed item
        for item in retry_items:
            self._send_webhook_request(
                item["url"],
                item["headers"],
                item["payload"],
                item["retries"]
            )
    
    # Event helper methods for common events
    
    def send_login_event(self, user, card_id=None):
        """Send machine.login event when a user logs in."""
        data = {
            "machine_id": self.machine_id,
            "machine_name": "Laser Cleaner",
            "user_id": user.id,
            "user_name": user.full_name or user.username,
        }
        
        if card_id:
            data["rfid_tag"] = card_id
            
        return self.send_event("machine.login", data)
    
    def send_logout_event(self, user, card_id=None):
        """Send machine.logout event when a user logs out."""
        data = {
            "machine_id": self.machine_id,
            "machine_name": "Laser Cleaner",
            "user_id": user.id,
            "user_name": user.full_name or user.username,
        }
        
        if card_id:
            data["rfid_tag"] = card_id
            
        return self.send_event("machine.logout", data)
    
    def send_status_change_event(self, status, details=None):
        """Send machine.status_change event when machine status changes."""
        data = {
            "machine_id": self.machine_id,
            "machine_name": "Laser Cleaner",
            "status": status,
            "previous_status": getattr(self, "last_status", "unknown"),
        }
        
        if details:
            data["details"] = details
            
        # Update last status
        self.last_status = status
            
        return self.send_event("machine.status_change", data)
    
    def send_alert_event(self, message, alert_type="info"):
        """Send alert.created event when a new alert is generated."""
        data = {
            "machine_id": self.machine_id,
            "machine_name": "Laser Cleaner",
            "message": message,
            "alert_type": alert_type,  # info, warning, error, maintenance
        }
            
        return self.send_event("alert.created", data)
    
    def send_node_status_event(self, status, details=None):
        """Send node.status_change event when node status changes."""
        data = {
            "machine_id": self.machine_id,
            "machine_name": "Laser Cleaner",
            "node_status": status,
            "previous_status": getattr(self, "last_node_status", "unknown"),
        }
        
        if details:
            data["details"] = details
            
        # Update last node status
        self.last_node_status = status
            
        return self.send_event("node.status_change", data)


# Create a singleton instance
webhook_handler = WebhookHandler()

def register_webhook_tasks(app):
    """Register webhook tasks with the scheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = BackgroundScheduler()
        
        # Add webhook retry job
        scheduler.add_job(
            func=webhook_handler.retry_failed_webhooks,
            trigger=IntervalTrigger(minutes=5),
            id='retry_webhooks',
            name='Retry failed webhook deliveries',
            replace_existing=True
        )
        
        # Start the scheduler if not already started
        if not scheduler.running:
            scheduler.start()
            
        logger.info("Webhook retry task registered with scheduler")
        return scheduler
    except ImportError:
        logger.warning("APScheduler not installed. Skipping webhook retry task registration.")
        return None
    except Exception as e:
        logger.error(f"Error registering webhook tasks: {e}")
        return None