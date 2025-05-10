"""
Webhook integration module for LCleanerController.

This module integrates the webhook handler with various parts of the application.
It's designed to be imported by other modules that need to send webhook events.
"""
import logging
from webhook_handler import webhook_handler
from models import User

logger = logging.getLogger(__name__)

def handle_login_event(user_id, card_id=None):
    """
    Send a machine.login webhook event when a user logs in.
    
    Args:
        user_id (int): The ID of the user who logged in
        card_id (str, optional): The RFID card ID used for login, if applicable
    """
    try:
        # Get user from database
        user = User.query.get(user_id)
        
        if user:
            # Send login webhook
            webhook_handler.send_login_event(user, card_id)
            
            # Log successful webhook send
            logger.info(f"Login webhook sent for user {user.username}")
        else:
            logger.warning(f"Could not send login webhook - user ID {user_id} not found")
    
    except Exception as e:
        logger.error(f"Error sending login webhook: {e}")

def handle_logout_event(user_id, reason="Manual logout", card_id=None):
    """
    Send a machine.logout webhook event when a user logs out.
    
    Args:
        user_id (int): The ID of the user who logged out
        reason (str): The reason for logout
        card_id (str, optional): The RFID card ID used, if applicable
    """
    try:
        # Get user from database
        user = User.query.get(user_id)
        
        if user:
            # Send logout webhook
            webhook_handler.send_logout_event(user, card_id)
            
            # Log successful webhook send
            logger.info(f"Logout webhook sent for user {user.username}")
        else:
            logger.warning(f"Could not send logout webhook - user ID {user_id} not found")
    
    except Exception as e:
        logger.error(f"Error sending logout webhook: {e}")

def handle_session_expired_event(user_id):
    """
    Send webhooks when a user session expires.
    
    Args:
        user_id (int): The ID of the user whose session expired
    """
    try:
        # Get user from database
        user = User.query.get(user_id)
        
        if user:
            # Send logout webhook
            webhook_handler.send_logout_event(user)
            
            # Log successful webhook send
            logger.info(f"Session expired webhook sent for user {user.username}")
        else:
            logger.warning(f"Could not send session expired webhook - user ID {user_id} not found")
    
    except Exception as e:
        logger.error(f"Error sending session expired webhook: {e}")

def handle_temperature_warning_event(temperature, sensor_name):
    """
    Send an alert webhook when temperature exceeds threshold.
    
    Args:
        temperature (float): The current temperature
        sensor_name (str): The name of the sensor reporting high temperature
    """
    try:
        message = f"High temperature warning: {temperature}°C detected on {sensor_name}"
        webhook_handler.send_alert_event(message, alert_type="warning")
        logger.info(f"Temperature warning webhook sent: {temperature}°C on {sensor_name}")
    
    except Exception as e:
        logger.error(f"Error sending temperature warning webhook: {e}")

def handle_status_change_event(status, details=None):
    """
    Send a status change webhook event.
    
    Args:
        status (str): The new machine status
        details (dict, optional): Additional details about the status change
    """
    try:
        webhook_handler.send_status_change_event(status, details)
        logger.info(f"Status change webhook sent: {status}")
    
    except Exception as e:
        logger.error(f"Error sending status change webhook: {e}")

def handle_node_status_event(status, details=None):
    """
    Send a node status change webhook event.
    
    Args:
        status (str): The new node status
        details (dict, optional): Additional details about the status change
    """
    try:
        webhook_handler.send_node_status_event(status, details)
        logger.info(f"Node status webhook sent: {status}")
    
    except Exception as e:
        logger.error(f"Error sending node status webhook: {e}")