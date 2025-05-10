# ShopTracker Integration API Documentation

This document provides comprehensive documentation for integrating the RFID Machine Monitor system with ShopTracker or other external systems.

## Overview

The RFID Machine Monitor system provides a RESTful API for bidirectional data exchange with ShopTracker, enabling:

1. User data synchronization
2. Machine access verification
3. Status reporting
4. Alert management
5. Machine usage analytics

## Authentication

All API requests require authentication using an API key. The API key should be included in the request header:

```
Authorization: Bearer YOUR_API_KEY_HERE
```

API keys can be generated and managed in the Integration Configuration section of the RFID Machine Monitor admin panel.

## Base URL

The base URL for all API endpoints is:

```
https://your-server-address/integration/api/
```

## API Endpoints

### Authentication & Access Control

#### Verify Machine Access

```
POST /auth
```

Verifies if a user has permission to access a specific machine.

**Request Body:**
```json
{
  "card_id": "0123456789",
  "machine_id": "W1"
}
```

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "0123456789",
    "fullName": "John Doe",
    "role": "operator"
  },
  "access_level": "operator",
  "machine_id": "W1",
  "timestamp": "2025-04-18T12:30:45Z"
}
```

### Status Reporting

#### Get Node Status

```
GET /node_status
```

Returns the status of all nodes and their connected machines.

**Response:**
```json
{
  "timestamp": "2025-04-18T12:30:45Z",
  "nodes": [
    {
      "id": 1,
      "node_id": "esp32_001",
      "name": "Shop Floor Node 1",
      "ip_address": "192.168.1.100",
      "node_type": "machine_monitor",
      "status": "online",
      "last_seen": "2025-04-18T12:25:45Z",
      "machines": [
        {
          "id": 1,
          "machine_id": "W1",
          "name": "Welding Machine 1",
          "status": "active",
          "zone": "Shop Floor",
          "current_user": {
            "id": 1,
            "name": "John Doe",
            "rfid_tag": "0123456789"
          },
          "today_access_count": 5,
          "activity_count": 42,
          "last_activity": "2025-04-18T12:30:45Z"
        }
      ]
    }
  ]
}
```

### Alert Management

#### Send Alert

```
POST /alerts
```

Sends an alert from ShopTracker to the RFID Machine Monitor system.

**Request Body:**
```json
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
```

**Response:**
```json
{
  "success": true,
  "message": "Alert received and stored",
  "local_alert_id": 1,
  "external_alert_id": 1,
  "timestamp": "2025-04-18T12:31:45Z",
  "machine_name": "Welding Machine 1"
}
```

#### Acknowledge Alert

```
POST /alerts/:id/acknowledge
```

Acknowledges an alert in the RFID Machine Monitor system.

**Response:**
```json
{
  "success": true,
  "message": "Alert 1 acknowledged",
  "alert": {
    "id": 1,
    "external_id": 1,
    "machine_id": "W1",
    "machine_name": "Welding Machine 1",
    "message": "Machine requires maintenance",
    "alert_type": "warning",
    "status": "acknowledged",
    "origin": "shop_tracker",
    "created_at": "2025-04-18T12:30:45Z",
    "acknowledged_at": "2025-04-18T12:45:22Z",
    "resolved_at": null
  },
  "timestamp": "2025-04-18T12:45:22Z"
}
```

#### Resolve Alert

```
POST /alerts/:id/resolve
```

Resolves an alert in the RFID Machine Monitor system.

**Response:**
```json
{
  "success": true,
  "message": "Alert 1 resolved",
  "alert": {
    "id": 1,
    "external_id": 1,
    "machine_id": "W1",
    "machine_name": "Welding Machine 1",
    "message": "Machine requires maintenance",
    "alert_type": "warning",
    "status": "resolved",
    "origin": "shop_tracker",
    "created_at": "2025-04-18T12:30:45Z",
    "acknowledged_at": "2025-04-18T12:45:22Z",
    "resolved_at": "2025-04-18T13:15:07Z"
  },
  "timestamp": "2025-04-18T13:15:07Z"
}
```

### User Management

#### Get Available Users

```
GET /users/available
```

Returns a list of users available in ShopTracker that can be imported.

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "username": "jdoe",
      "email": "john.doe@example.com",
      "card_id": "0123456789",
      "access_level": "operator",
      "status": "active"
    }
  ]
}
```

#### Sync User

```
POST /users/sync
```

Synchronizes a user between systems.

**Request Body:**
```json
{
  "external_id": 1,
  "direction": "import",
  "overwrite_permissions": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "User synchronized successfully",
  "user": {
    "id": 5,
    "external_id": 1,
    "name": "John Doe",
    "rfid_tag": "0123456789",
    "email": "john.doe@example.com",
    "active": true,
    "last_synced": "2025-04-18T14:22:15Z"
  }
}
```

#### Get User Permissions

```
GET /users/:id/permissions
```

Returns the permissions for a specific user.

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 5,
    "external_id": 1,
    "name": "John Doe"
  },
  "permissions": {
    "local": [1, 2, 3],
    "external": [1, 2, 4, 5],
    "combined": [1, 2, 3, 4, 5]
  },
  "machines": [
    {
      "id": 1,
      "machine_id": "W1",
      "name": "Welding Machine 1",
      "zone": "Shop Floor",
      "status": "active",
      "in_local": true,
      "in_external": true
    },
    {
      "id": 4,
      "machine_id": "C2",
      "name": "Cutting Machine 2",
      "zone": "Shop Floor",
      "status": "idle",
      "in_local": false,
      "in_external": true
    }
  ]
}
```

#### Update User Permissions

```
POST /users/:id/permissions
```

Updates the permissions for a specific user.

**Request Body:**
```json
{
  "machine_ids": [1, 2, 3, 4],
  "sync_to_external": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Permissions updated successfully",
  "user": {
    "id": 5,
    "name": "John Doe"
  },
  "updated_machines": 4,
  "synced_to_external": true
}
```

### Machine Usage

#### Get Machine Usage

```
GET /machines/usage
```

Returns usage statistics for machines.

**Query Parameters:**
- `start_date`: ISO format date (required)
- `end_date`: ISO format date (required)
- `machine_id`: Filter by specific machine ID (optional)
- `zone_id`: Filter by specific zone ID (optional)

**Response:**
```json
{
  "success": true,
  "start_date": "2025-04-01T00:00:00Z",
  "end_date": "2025-04-18T23:59:59Z",
  "total_usage_hours": 245.5,
  "machines": [
    {
      "id": 1,
      "machine_id": "W1",
      "name": "Welding Machine 1",
      "zone": "Shop Floor",
      "usage_hours": 78.2,
      "login_count": 42,
      "users": [
        {
          "id": 5,
          "name": "John Doe",
          "usage_hours": 45.5,
          "login_count": 25
        }
      ]
    }
  ]
}
```

## Webhooks

The RFID Machine Monitor can send webhook notifications to ShopTracker for real-time events.

### Webhook Events

- `machine.login`: User logged in to a machine
- `machine.logout`: User logged out of a machine
- `machine.status_change`: Machine status changed
- `alert.created`: New alert created
- `node.status_change`: Node status changed

### Webhook Format

```json
{
  "event": "machine.login",
  "timestamp": "2025-04-18T12:30:45Z",
  "data": {
    "machine_id": 1,
    "machine_code": "W1",
    "machine_name": "Welding Machine 1",
    "user_id": 5,
    "user_name": "John Doe",
    "rfid_tag": "0123456789"
  }
}
```

## Error Handling

All API endpoints return standard HTTP status codes:

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Missing or invalid API key
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with details:

```json
{
  "success": false,
  "error": "Invalid machine ID",
  "code": "INVALID_PARAMETER",
  "timestamp": "2025-04-18T12:30:45Z"
}
```

## Rate Limiting

API requests are limited to 100 requests per minute per API key. If exceeded, a `429 Too Many Requests` response will be returned.

## Data Synchronization Best Practices

1. **Scheduled Sync**: Run a full sync at regular intervals (e.g., daily)
2. **Event-Driven Updates**: Use webhooks for real-time updates
3. **Conflict Resolution**: External system (ShopTracker) is considered the source of truth for user data
4. **Permission Merging**: Local permissions take precedence over external ones when conflicts occur

## Appendix

### Alert Types

- `info`: Informational message
- `warning`: Warning that needs attention
- `error`: Error that requires action
- `maintenance`: Scheduled maintenance notification

### Machine Statuses

- `idle`: Machine is available but not in use
- `active`: Machine is in use
- `warning`: Machine has triggered a warning condition
- `offline`: Machine is not connected or powered off

### Node Types

- `machine_monitor`: Controls and monitors machines
- `office_reader`: RFID reader for card registration
- `accessory_io`: Controls external accessories

For further assistance, please contact the development team.