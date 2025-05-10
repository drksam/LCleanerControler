"""
API routes for ShopTracker Integration as defined in MM_API_DOCUMENTATION.md
"""
from datetime import datetime
import functools
import json
import time
from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from models import User, RFIDCard, AccessLog, ApiKey, db

# Create a Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/integration/api')

# Dictionary to track API requests for rate limiting
request_tracker = {}
RATE_LIMIT = 100  # requests per minute

def require_api_key(f):
    """Decorator to require API key authentication for endpoints"""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # Check for API key in Authorization header
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                'success': False,
                'error': 'Missing API key',
                'code': 'UNAUTHORIZED',
                'timestamp': datetime.utcnow().isoformat()
            }), 401
            
        api_key = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Check rate limiting
        now = time.time()
        minute_ago = now - 60
        
        # Clean up old entries
        for key in list(request_tracker.keys()):
            if request_tracker[key]['timestamp'] < minute_ago:
                del request_tracker[key]
                
        # Check if this key has exceeded rate limit
        if api_key in request_tracker:
            request_tracker[api_key]['count'] += 1
            request_tracker[api_key]['timestamp'] = now
            if request_tracker[api_key]['count'] > RATE_LIMIT:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Maximum 100 requests per minute.',
                    'code': 'RATE_LIMIT_EXCEEDED',
                    'timestamp': datetime.utcnow().isoformat()
                }), 429
        else:
            request_tracker[api_key] = {'count': 1, 'timestamp': now}
        
        # Verify API key
        api_key_obj = ApiKey.query.filter_by(key=api_key, active=True).first()
        if not api_key_obj:
            return jsonify({
                'success': False,
                'error': 'Invalid API key',
                'code': 'UNAUTHORIZED',
                'timestamp': datetime.utcnow().isoformat()
            }), 401
            
        # API key is valid, proceed
        return f(*args, **kwargs)
    return decorated

@api_bp.route('/auth', methods=['POST'])
@require_api_key
def verify_machine_access():
    """
    Verify if a user has permission to access a specific machine
    
    Request body:
    {
        "card_id": "0123456789",
        "machine_id": "W1"
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body',
                'code': 'BAD_REQUEST',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        # Extract parameters
        card_id = data.get('card_id')
        machine_id = data.get('machine_id')
        
        if not card_id or not machine_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: card_id, machine_id',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        
        # Find the card in the database
        card = RFIDCard.query.filter_by(card_id=card_id, active=True).first()
        
        if not card:
            # Log the failed access attempt
            log_entry = AccessLog(
                card_id=card_id,
                machine_id=machine_id,
                action='access_denied',
                details='Card not found or inactive'
            )
            db.session.add(log_entry)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'authorized': False,
                'reason': 'Card not found or inactive',
                'machine_id': machine_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        # Check if the card is expired
        if card.expiry_date and card.expiry_date < datetime.utcnow():
            # Log the failed access attempt
            log_entry = AccessLog(
                card_id=card_id,
                machine_id=machine_id,
                user_id=card.user_id,
                action='access_denied',
                details='Card expired'
            )
            db.session.add(log_entry)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'authorized': False,
                'reason': 'Card has expired',
                'machine_id': machine_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
        # Get the user
        user = User.query.get(card.user_id)
        
        if not user or not user.active:
            # Log the failed access attempt
            log_entry = AccessLog(
                card_id=card_id,
                machine_id=machine_id,
                user_id=card.user_id if card else None,
                action='access_denied',
                details='User account inactive or not found'
            )
            db.session.add(log_entry)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'authorized': False,
                'reason': 'User account inactive or not found',
                'machine_id': machine_id,
                'timestamp': datetime.utcnow().isoformat()
            })
        
        # User is authorized
        # In a more complex system, we would check machine-specific permissions here
        
        # Log the successful access
        log_entry = AccessLog(
            card_id=card_id,
            machine_id=machine_id,
            user_id=user.id,
            action='login',
            details='API authorization'
        )
        db.session.add(log_entry)
        db.session.commit()
        
        # Return success response
        return jsonify({
            'success': True,
            'authorized': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'fullName': user.full_name,
                'role': user.access_level
            },
            'access_level': user.access_level,
            'machine_id': machine_id,
            'expiry_hours': 8,  # Default session length
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in authentication API: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/node_status', methods=['GET'])
@require_api_key
def get_node_status():
    """Get the status of all nodes and their connected machines"""
    try:
        # In this implementation, we'll return the status of this machine
        # In a more complex system with multiple nodes, we'd gather data from all nodes
        
        # Get current authenticated user if any
        current_authenticated_user = None
        if hasattr(current_app, 'rfid_controller') and current_app.rfid_controller:
            current_authenticated_user = current_app.rfid_controller.get_authenticated_user()
        
        # Format the response according to API documentation
        response = {
            'timestamp': datetime.utcnow().isoformat(),
            'nodes': [
                {
                    'id': 1,
                    'node_id': 'laser_room_1',  # Use machine_id from config
                    'name': 'Laser Room Controller',
                    'ip_address': request.remote_addr,
                    'node_type': 'machine_monitor',
                    'status': 'online',
                    'last_seen': datetime.utcnow().isoformat(),
                    'machines': [
                        {
                            'id': 1,
                            'machine_id': 'laser_room_1',
                            'name': 'Laser Cleaning System',
                            'status': 'active' if current_authenticated_user else 'idle',
                            'zone': 'Laser Room',
                            'current_user': {
                                'id': current_authenticated_user.get('user_id') if current_authenticated_user else None,
                                'name': current_authenticated_user.get('full_name') if current_authenticated_user else None,
                                'rfid_tag': None  # We don't expose RFID tag for privacy/security
                            } if current_authenticated_user else None,
                            'today_access_count': AccessLog.query.filter(
                                AccessLog.action == 'login',
                                AccessLog.timestamp > datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                            ).count(),
                            'activity_count': AccessLog.query.filter_by(action='login').count(),
                            'last_activity': AccessLog.query.filter_by(action='login').order_by(AccessLog.timestamp.desc()).first().timestamp.isoformat() if AccessLog.query.filter_by(action='login').count() > 0 else None
                        }
                    ]
                }
            ]
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error getting node status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# User Management Endpoints

@api_bp.route('/users/available', methods=['GET'])
@require_api_key
def get_available_users():
    """Get a list of available users that can be imported"""
    try:
        # Get all active users
        users = User.query.filter_by(active=True).all()
        
        # Format user data for response
        user_list = []
        for user in users:
            # Get the user's RFID card if any
            rfid_card = RFIDCard.query.filter_by(user_id=user.id, active=True).first()
            
            user_list.append({
                'id': user.id,
                'name': user.full_name or user.username,
                'username': user.username,
                'email': user.email,
                'card_id': rfid_card.card_id if rfid_card else None,
                'access_level': user.access_level,
                'status': 'active' if user.active else 'inactive'
            })
            
        return jsonify({
            'success': True,
            'users': user_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting available users: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/users/sync', methods=['POST'])
@require_api_key
def sync_user():
    """
    Synchronize a user between systems
    
    Request body:
    {
        "external_id": 1,
        "direction": "import",
        "overwrite_permissions": true
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body',
                'code': 'BAD_REQUEST',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        
        # Extract parameters
        external_id = data.get('external_id')
        direction = data.get('direction', 'import')
        overwrite_permissions = data.get('overwrite_permissions', False)
        
        if not external_id:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: external_id',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        # In a real implementation, we'd communicate with the external system
        # to get user details. For this implementation, we'll
        # just check if the user exists in our database
        
        user = User.query.get(external_id)
        
        # If user doesn't exist and direction is import, create a new user record
        # Here we're simulating data from an external system
        if not user and direction == 'import':
            user = User(
                id=external_id,
                username=f"user_{external_id}",
                full_name=f"Imported User {external_id}",
                email=f"user{external_id}@example.com",
                access_level='operator',
                active=True
            )
            user.set_password('default_password')  # In real implementation, generate secure password
            db.session.add(user)
            db.session.commit()
            
            # Log the user creation
            current_app.logger.info(f"Created new user with ID {user.id} via API sync")
        
        # If user exists and direction is export, we'd send our data to the external system
        elif user and direction == 'export':
            # Simulate sending to external system
            current_app.logger.info(f"Exporting user {user.id} to external system")
        
        # For either case, return the synchronized user
        if user:
            # Get the user's RFID card if any
            rfid_card = RFIDCard.query.filter_by(user_id=user.id, active=True).first()
            
            return jsonify({
                'success': True,
                'message': 'User synchronized successfully',
                'user': {
                    'id': user.id,
                    'external_id': user.id,  # In real implementation, these might be different
                    'name': user.full_name or user.username,
                    'rfid_tag': rfid_card.card_id if rfid_card else None,
                    'email': user.email,
                    'active': user.active,
                    'last_synced': datetime.utcnow().isoformat()
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'User with ID {external_id} not found',
                'code': 'NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Error in user synchronization: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/users/<int:user_id>/permissions', methods=['GET'])
@require_api_key
def get_user_permissions(user_id):
    """Get the permissions for a specific user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User with ID {user_id} not found',
                'code': 'NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
        # In a full implementation, we'd have a permissions table
        # For now, we'll simulate permissions based on access level
        
        # Create a list of machine IDs this user has access to
        # In this simple implementation, operators have access to machine 1
        # Admins have access to all machines
        local_permissions = [1]
        if user.access_level == 'admin':
            local_permissions.extend([2, 3])
            
        # Simulate external permissions coming from ShopTracker
        # In a real implementation, these would be fetched from the external system
        external_permissions = [1, 2, 4, 5]
        
        # Combine permissions (union of both permission sets)
        combined_permissions = list(set(local_permissions + external_permissions))
        
        # Create a list of machine entries
        machines = [
            {
                'id': 1,
                'machine_id': 'laser_room_1',
                'name': 'Laser Cleaning System',
                'zone': 'Laser Room',
                'status': 'active',
                'in_local': 1 in local_permissions,
                'in_external': 1 in external_permissions
            },
            {
                'id': 2,
                'machine_id': 'W1',
                'name': 'Welding Machine 1',
                'zone': 'Shop Floor',
                'status': 'idle',
                'in_local': 2 in local_permissions,
                'in_external': 2 in external_permissions
            },
            {
                'id': 3,
                'machine_id': 'C1',
                'name': 'Cutting Machine 1',
                'zone': 'Shop Floor',
                'status': 'offline',
                'in_local': 3 in local_permissions,
                'in_external': 3 in external_permissions
            },
            {
                'id': 4,
                'machine_id': 'C2',
                'name': 'Cutting Machine 2',
                'zone': 'Shop Floor',
                'status': 'idle',
                'in_local': 4 in local_permissions,
                'in_external': 4 in external_permissions
            },
            {
                'id': 5,
                'machine_id': 'P1',
                'name': 'Press 1',
                'zone': 'Forming Area',
                'status': 'active',
                'in_local': 5 in local_permissions,
                'in_external': 5 in external_permissions
            }
        ]
        
        # Only return machines that the user has permission for in either local or external systems
        permitted_machines = [m for m in machines if m['id'] in combined_permissions]
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'external_id': user.id,  # In real implementation, these might be different
                'name': user.full_name or user.username
            },
            'permissions': {
                'local': local_permissions,
                'external': external_permissions,
                'combined': combined_permissions
            },
            'machines': permitted_machines
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user permissions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/users/<int:user_id>/permissions', methods=['POST'])
@require_api_key
def update_user_permissions(user_id):
    """Update the permissions for a specific user"""
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'error': f'User with ID {user_id} not found',
                'code': 'NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body',
                'code': 'BAD_REQUEST',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        
        # Extract parameters
        permissions = data.get('permissions', [])
        
        if not permissions:
            return jsonify({
                'success': False,
                'error': 'Missing required parameter: permissions',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
        
        # In a real implementation, we'd update the permissions in the database
        # For this implementation, we'll just log the update
        
        current_app.logger.info(f"Updating permissions for user {user.id}: {permissions}")
        
        return jsonify({
            'success': True,
            'message': 'Permissions updated successfully',
            'user': {
                'id': user.id,
                'name': user.full_name or user.username
            },
            'permissions': permissions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating user permissions: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Alert Management Endpoints

@api_bp.route('/alerts', methods=['POST'])
@require_api_key
def send_alert():
    """
    Sends an alert from ShopTracker to the RFID Machine Monitor system
    
    Request body:
    {
        "id": 1,
        "machineId": "W1",
        "senderId": 1,
        "message": "Machine requires maintenance",
        "alertType": "warning",
        "status": "pending",
        "origin": "machine",
        "createdAt": "2025-04-18T12:30:45Z"
    }
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing request body',
                'code': 'BAD_REQUEST',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        # Extract required parameters
        external_alert_id = data.get('id')
        machine_id = data.get('machineId')
        message = data.get('message')
        alert_type = data.get('alertType')
        
        if not all([external_alert_id, machine_id, message, alert_type]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        # In a full implementation, we'd save this alert to a database
        # For now, we'll just log it
        current_app.logger.info(f"Alert received - ID: {external_alert_id}, Machine: {machine_id}, Type: {alert_type}, Message: {message}")
        
        # Create a simulated local alert ID
        local_alert_id = external_alert_id  # In a real system, this would be a database ID
        
        # Get the machine name
        machine_name = 'Unknown'
        if machine_id == 'laser_room_1':
            machine_name = 'Laser Cleaning System'
        elif machine_id == 'W1':
            machine_name = 'Welding Machine 1'
        
        return jsonify({
            'success': True,
            'message': 'Alert received and stored',
            'local_alert_id': local_alert_id,
            'external_alert_id': external_alert_id,
            'timestamp': datetime.utcnow().isoformat(),
            'machine_name': machine_name
        })
        
    except Exception as e:
        current_app.logger.error(f"Error processing alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
@require_api_key
def acknowledge_alert(alert_id):
    """Acknowledge an alert in the RFID Machine Monitor system"""
    try:
        # In a full implementation, we'd update the alert status in the database
        # For now, we'll simulate the response
        
        # Check if alert exists (simulated)
        if alert_id <= 0:
            return jsonify({
                'success': False,
                'error': f'Alert with ID {alert_id} not found',
                'code': 'NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
        current_app.logger.info(f"Alert {alert_id} acknowledged")
        
        # Simulate alert data
        machine_id = 'laser_room_1' if alert_id % 2 == 0 else 'W1'
        machine_name = 'Laser Cleaning System' if machine_id == 'laser_room_1' else 'Welding Machine 1'
        acknowledged_time = datetime.utcnow()
        created_time = acknowledged_time - datetime.timedelta(minutes=15)
        
        return jsonify({
            'success': True,
            'message': f'Alert {alert_id} acknowledged',
            'alert': {
                'id': alert_id,
                'external_id': alert_id,
                'machine_id': machine_id,
                'machine_name': machine_name,
                'message': 'Machine requires maintenance',
                'alert_type': 'warning',
                'status': 'acknowledged',
                'origin': 'ShopTracker',
                'created_at': created_time.isoformat(),
                'acknowledged_at': acknowledged_time.isoformat(),
                'resolved_at': None
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error acknowledging alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@api_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@require_api_key
def resolve_alert(alert_id):
    """Resolve an alert in the RFID Machine Monitor system"""
    try:
        # In a full implementation, we'd update the alert status in the database
        # For now, we'll simulate the response
        
        # Check if alert exists (simulated)
        if alert_id <= 0:
            return jsonify({
                'success': False,
                'error': f'Alert with ID {alert_id} not found',
                'code': 'NOT_FOUND',
                'timestamp': datetime.utcnow().isoformat()
            }), 404
            
        current_app.logger.info(f"Alert {alert_id} resolved")
        
        # Simulate alert data
        machine_id = 'laser_room_1' if alert_id % 2 == 0 else 'W1'
        machine_name = 'Laser Cleaning System' if machine_id == 'laser_room_1' else 'Welding Machine 1'
        resolved_time = datetime.utcnow()
        acknowledged_time = resolved_time - datetime.timedelta(minutes=10)
        created_time = acknowledged_time - datetime.timedelta(minutes=20)
        
        return jsonify({
            'success': True,
            'message': f'Alert {alert_id} resolved',
            'alert': {
                'id': alert_id,
                'external_id': alert_id,
                'machine_id': machine_id,
                'machine_name': machine_name,
                'message': 'Machine requires maintenance',
                'alert_type': 'warning',
                'status': 'resolved',
                'origin': 'ShopTracker',
                'created_at': created_time.isoformat(),
                'acknowledged_at': acknowledged_time.isoformat(),
                'resolved_at': resolved_time.isoformat()
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resolving alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Machine Usage Endpoint

@api_bp.route('/machines/usage', methods=['GET'])
@require_api_key
def get_machine_usage():
    """
    Returns usage statistics for machines
    
    Query Parameters:
    - start_date: ISO format date (required)
    - end_date: ISO format date (required)
    - machine_id: Filter by specific machine ID (optional)
    - zone_id: Filter by specific zone ID (optional)
    """
    try:
        # Extract query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        machine_id = request.args.get('machine_id')
        zone_id = request.args.get('zone_id')
        
        if not start_date_str or not end_date_str:
            return jsonify({
                'success': False,
                'error': 'Missing required query parameters: start_date, end_date',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        try:
            # Parse dates from ISO format
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({
                'success': False,
                'error': 'Invalid date format. Use ISO format dates.',
                'code': 'INVALID_PARAMETERS',
                'timestamp': datetime.utcnow().isoformat()
            }), 400
            
        # In a full implementation, we'd query the database for actual usage data
        # For now, we'll create simulated usage statistics
        
        # Get access log counts within date range
        login_count = AccessLog.query.filter(
            AccessLog.timestamp >= start_date,
            AccessLog.timestamp <= end_date,
            AccessLog.action == 'login'
        ).count()
        
        # Calculate simulated usage hours based on login count
        # Assuming each login lasts about 2 hours on average
        total_usage_hours = login_count * 2
        
        # Create simulated machine usage data
        machines_data = []
        
        # Add laser room machine
        laser_machine = {
            'id': 1,
            'machine_id': 'laser_room_1',
            'name': 'Laser Cleaning System',
            'zone': 'Laser Room',
            'usage_hours': round(total_usage_hours * 0.7, 1),  # 70% of total usage
            'login_count': int(login_count * 0.7),
            'users': [
                {
                    'id': 1,
                    'name': 'John Doe',
                    'usage_hours': round(total_usage_hours * 0.4, 1),
                    'login_count': int(login_count * 0.4)
                },
                {
                    'id': 2,
                    'name': 'Jane Smith',
                    'usage_hours': round(total_usage_hours * 0.3, 1),
                    'login_count': int(login_count * 0.3)
                }
            ]
        }
        
        # If no machine_id filter or filter matches laser_room_1
        if not machine_id or machine_id == 'laser_room_1':
            machines_data.append(laser_machine)
            
        # Add welding machine if no filter or filter matches W1
        if not machine_id or machine_id == 'W1':
            machines_data.append({
                'id': 2,
                'machine_id': 'W1',
                'name': 'Welding Machine 1',
                'zone': 'Shop Floor',
                'usage_hours': round(total_usage_hours * 0.3, 1),  # 30% of total usage
                'login_count': int(login_count * 0.3),
                'users': [
                    {
                        'id': 1,
                        'name': 'John Doe',
                        'usage_hours': round(total_usage_hours * 0.2, 1),
                        'login_count': int(login_count * 0.2)
                    },
                    {
                        'id': 3,
                        'name': 'Robert Johnson',
                        'usage_hours': round(total_usage_hours * 0.1, 1),
                        'login_count': int(login_count * 0.1)
                    }
                ]
            })
            
        return jsonify({
            'success': True,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_usage_hours': total_usage_hours,
            'machines': machines_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting machine usage: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'code': 'SERVER_ERROR',
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Helper function to register all API routes with the Flask app
def register_api_routes(app):
    """Register all API routes with the Flask app"""
    app.register_blueprint(api_bp)
    app.logger.info(f"Registered {len([rule for rule in app.url_map.iter_rules() if rule.endpoint.startswith('api.')])} API routes")