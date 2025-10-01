# WebEngage API Documentation for Google Apps Script Automation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [User Management](#user-management)
5. [Event Tracking](#event-tracking)
6. [Bulk Operations](#bulk-operations)
7. [Google Apps Script Integration](#google-apps-script-integration)
8. [Error Handling](#error-handling)
9. [Rate Limits](#rate-limits)
10. [Best Practices](#best-practices)

## Overview

WebEngage is a full-stack marketing automation suite that enables businesses to engage users across multiple channels including Push, In-app, SMS, On-site Notifications, Web Push, Email, Facebook-Instagram, and WhatsApp.

This documentation focuses on the REST API integration for Google Apps Script automation, covering user creation, event tracking, and bulk operations.

### Key Capabilities
- **User Tracking**: Create and update user profiles with attributes
- **Event Tracking**: Log user actions and behaviors
- **Bulk Operations**: Process large datasets efficiently
- **Real-time Integration**: Immediate data synchronization

## Authentication

### Bearer Token Authentication
WebEngage uses Bearer Authentication Scheme for API access.

```javascript
// Google Apps Script Example
const headers = {
  'Authorization': 'Bearer YOUR_API_KEY',
  'Content-Type': 'application/json'
};
```

### Getting Your Credentials
1. Navigate to **Data Platform > Integrations > REST API** in your WebEngage dashboard
2. Copy your **REST API Key** and **WebEngage Account License Code**
3. Store these securely in your Google Apps Script project

### Important Notes
- Only Account Admins with **Account Management** and **Update Data** permissions can access the API
- API keys are valid for the entire lifetime of an Account Admin
- If compromised, contact support@webengage.com for a new key

## API Endpoints

### Base URLs by Data Center
- **Global Data Center**: `https://api.webengage.com/`
- **India Data Center**: `https://api.in.webengage.com/`
- **Saudi Arabia Data Center**: `https://api.ksa.webengage.com/`

### Endpoint Structure
```
<HOST>/v1/accounts/<YOUR_WEBENGAGE_LICENSE_CODE>/<RESOURCE>
```

## User Management

### Creating/Updating Users
**Endpoint**: `POST /users`

```javascript
// Google Apps Script Example
function createUser(userData) {
  const url = `${HOST}/v1/accounts/${LICENSE_CODE}/users`;
  const payload = {
    userId: userData.userId,
    firstName: userData.firstName,
    lastName: userData.lastName,
    email: userData.email,
    phone: userData.phone,
    attributes: {
      "Customer Type": userData.customerType,
      "Total Spent": userData.totalSpent,
      "Last Purchase Date": userData.lastPurchaseDate
    }
  };
  
  const options = {
    method: 'POST',
    headers: headers,
    payload: JSON.stringify(payload)
  };
  
  return UrlFetchApp.fetch(url, options);
}
```

### User Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | String | Yes* | Unique user identifier (max 100 chars) |
| `anonymousId` | String | Yes* | Anonymous user identifier |
| `firstName` | String | No | User's first name |
| `lastName` | String | No | User's last name |
| `email` | String | No | User's email address |
| `phone` | String | No | Phone number (E.164 format) |
| `birthDate` | String | No | ISO format: yyyy-MM-ddTHH:mm:ss±hhmm |
| `gender` | String | No | male, female, or other |
| `company` | String | No | Company name |
| `attributes` | Object | No | Custom user attributes |

*Either `userId` or `anonymousId` is required

### User Identification Guidelines
- User IDs can be maximum 100 characters
- Once assigned, user ID cannot be changed
- Use system-generated IDs instead of changeable information like email addresses
- Anonymous users become known users when assigned a `userId`

## Event Tracking

### Logging Events
**Endpoint**: `POST /events`

```javascript
// Google Apps Script Example
function trackEvent(userId, eventName, eventData) {
  const url = `${HOST}/v1/accounts/${LICENSE_CODE}/events`;
  const payload = {
    userId: userId,
    eventName: eventName,
    eventTime: new Date().toISOString(),
    eventData: eventData
  };
  
  const options = {
    method: 'POST',
    headers: headers,
    payload: JSON.stringify(payload)
  };
  
  return UrlFetchApp.fetch(url, options);
}

// Example Usage
trackEvent("user123", "Purchase Completed", {
  "Product ID": 1337,
  "Price": 39.80,
  "Quantity": 1,
  "Product": "Givenchy Pour Homme Cologne",
  "Category": "Fragrance",
  "Currency": "USD"
});
```

### Event Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userId` | String | Yes* | User identifier |
| `anonymousId` | String | Yes* | Anonymous user identifier |
| `eventName` | String | Yes | Event name (max 50 chars) |
| `eventTime` | String | No | ISO format timestamp |
| `eventData` | Object | No | Event attributes |

*Either `userId` or `anonymousId` is required

### Event Guidelines
- Event names must be less than 50 characters
- Event attribute names are case-sensitive and must be less than 50 characters
- String attribute values must be less than 1000 characters
- Maximum 25 event attributes per event
- Avoid names starting with `we_` (reserved for internal use)

## Bulk Operations

### Bulk User Creation
**Endpoint**: `POST /bulk-users`

```javascript
// Google Apps Script Example
function bulkCreateUsers(usersArray) {
  const url = `${HOST}/v1/accounts/${LICENSE_CODE}/bulk-users`;
  const payload = {
    users: usersArray
  };
  
  const options = {
    method: 'POST',
    headers: headers,
    payload: JSON.stringify(payload)
  };
  
  return UrlFetchApp.fetch(url, options);
}

// Example Usage
const users = [
  {
    userId: "user1",
    firstName: "John",
    lastName: "Doe",
    email: "john@example.com",
    attributes: {
      "Customer Type": "Premium",
      "Total Spent": 500.00
    }
  },
  {
    userId: "user2",
    firstName: "Jane",
    lastName: "Smith",
    email: "jane@example.com",
    attributes: {
      "Customer Type": "Standard",
      "Total Spent": 250.00
    }
  }
];

bulkCreateUsers(users);
```

### Bulk Event Creation
**Endpoint**: `POST /bulk-events`

```javascript
// Google Apps Script Example
function bulkTrackEvents(eventsArray) {
  const url = `${HOST}/v1/accounts/${LICENSE_CODE}/bulk-events`;
  const payload = {
    events: eventsArray
  };
  
  const options = {
    method: 'POST',
    headers: headers,
    payload: JSON.stringify(payload)
  };
  
  return UrlFetchApp.fetch(url, options);
}
```

### Bulk Operation Limits
- **Users/Events per call**: 25
- **Rate limit**: 500 requests per minute
- **Individual API rate limit**: 5,000 per minute

## Google Apps Script Integration

### Complete Integration Example

```javascript
// WebEngage API Configuration
const WEBENGAGE_CONFIG = {
  HOST: 'https://api.webengage.com', // or appropriate data center
  LICENSE_CODE: 'YOUR_LICENSE_CODE',
  API_KEY: 'YOUR_API_KEY'
};

// Headers for all requests
const getHeaders = () => {
  return {
    'Authorization': `Bearer ${WEBENGAGE_CONFIG.API_KEY}`,
    'Content-Type': 'application/json'
  };
};

// Create or update user
function createOrUpdateUser(userData) {
  try {
    const url = `${WEBENGAGE_CONFIG.HOST}/v1/accounts/${WEBENGAGE_CONFIG.LICENSE_CODE}/users`;
    const payload = {
      userId: userData.userId,
      firstName: userData.firstName,
      lastName: userData.lastName,
      email: userData.email,
      phone: userData.phone,
      attributes: userData.attributes || {}
    };
    
    const options = {
      method: 'POST',
      headers: getHeaders(),
      payload: JSON.stringify(payload)
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());
    
    if (result.response.status === 'queued') {
      console.log(`User ${userData.userId} created/updated successfully`);
      return true;
    } else {
      console.error(`Error creating user: ${result.response.message}`);
      return false;
    }
  } catch (error) {
    console.error(`Exception creating user: ${error.toString()}`);
    return false;
  }
}

// Track event for user
function trackUserEvent(userId, eventName, eventData) {
  try {
    const url = `${WEBENGAGE_CONFIG.HOST}/v1/accounts/${WEBENGAGE_CONFIG.LICENSE_CODE}/events`;
    const payload = {
      userId: userId,
      eventName: eventName,
      eventTime: new Date().toISOString(),
      eventData: eventData || {}
    };
    
    const options = {
      method: 'POST',
      headers: getHeaders(),
      payload: JSON.stringify(payload)
    };
    
    const response = UrlFetchApp.fetch(url, options);
    const result = JSON.parse(response.getContentText());
    
    if (result.response.status === 'queued') {
      console.log(`Event ${eventName} tracked successfully for user ${userId}`);
      return true;
    } else {
      console.error(`Error tracking event: ${result.response.message}`);
      return false;
    }
  } catch (error) {
    console.error(`Exception tracking event: ${error.toString()}`);
    return false;
  }
}

// Bulk user creation from Google Sheets
function bulkCreateUsersFromSheet() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  const headers = data[0];
  const users = [];
  
  // Skip header row
  for (let i = 1; i < data.length; i++) {
    const row = data[i];
    const user = {
      userId: row[headers.indexOf('userId')],
      firstName: row[headers.indexOf('firstName')],
      lastName: row[headers.indexOf('lastName')],
      email: row[headers.indexOf('email')],
      phone: row[headers.indexOf('phone')],
      attributes: {
        "Customer Type": row[headers.indexOf('customerType')],
        "Total Spent": parseFloat(row[headers.indexOf('totalSpent')]) || 0
      }
    };
    users.push(user);
  }
  
  // Process in batches of 25
  for (let i = 0; i < users.length; i += 25) {
    const batch = users.slice(i, i + 25);
    bulkCreateUsers(batch);
    Utilities.sleep(1000); // Rate limiting
  }
}
```

## Error Handling

### Common Error Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| 400 | Invalid resource/parameters | Check license code and endpoint URL |
| 401 | Invalid authentication | Verify API key and permissions |
| 404 | Invalid URL | Check host URL for your data center |
| 429 | Rate limit exceeded | Implement exponential backoff |

### Error Handling Example

```javascript
function handleApiResponse(response) {
  const statusCode = response.getResponseCode();
  const content = JSON.parse(response.getContentText());
  
  switch (statusCode) {
    case 200:
      return { success: true, data: content };
    case 400:
      console.error('Bad Request:', content.response.message);
      return { success: false, error: 'Invalid parameters' };
    case 401:
      console.error('Unauthorized:', content.response.message);
      return { success: false, error: 'Authentication failed' };
    case 429:
      console.error('Rate Limited:', content.response.message);
      return { success: false, error: 'Rate limit exceeded' };
    default:
      console.error('Unknown Error:', statusCode, content);
      return { success: false, error: 'Unknown error' };
  }
}
```

## Rate Limits

### Default Rate Limits
- **User Data Update**: 5,000 per minute
- **Event Data Update**: 5,000 per minute
- **Bulk Operations**: 500 requests per minute (25 items per request)

### Rate Limiting Headers
- `X-RateLimit-Limit`: Per minute limit for endpoint
- `X-RateLimit-Remaining`: Remaining requests in current minute

### Rate Limiting Implementation

```javascript
function rateLimitedRequest(url, options) {
  const maxRetries = 3;
  let retryCount = 0;
  
  while (retryCount < maxRetries) {
    try {
      const response = UrlFetchApp.fetch(url, options);
      
      if (response.getResponseCode() === 429) {
        retryCount++;
        const waitTime = Math.pow(2, retryCount) * 1000; // Exponential backoff
        Utilities.sleep(waitTime);
        continue;
      }
      
      return response;
    } catch (error) {
      retryCount++;
      if (retryCount >= maxRetries) {
        throw error;
      }
      Utilities.sleep(1000);
    }
  }
}
```

## Best Practices

### 1. Data Consistency
- Use consistent data types for attributes
- First data point defines the attribute type
- Avoid changing data types after initial setup

### 2. User Identification
- Use stable, unique identifiers
- Avoid using email addresses as user IDs
- Implement proper user merging logic

### 3. Event Tracking
- Use descriptive event names
- Include relevant context in event data
- Avoid tracking sensitive information

### 4. Error Handling
- Implement comprehensive error handling
- Log all API interactions
- Use exponential backoff for retries

### 5. Performance
- Use bulk operations for large datasets
- Implement proper rate limiting
- Cache frequently used data

### 6. Security
- Store API keys securely
- Use environment variables
- Regularly rotate API keys

## Support and Resources

- **Email Support**: support@webengage.com
- **Documentation**: https://docs.webengage.com/docs/
- **Knowledge Base**: https://knowledgebase.webengage.com/docs/

---

*This documentation is based on WebEngage's official API documentation and is specifically tailored for Google Apps Script automation needs.* 