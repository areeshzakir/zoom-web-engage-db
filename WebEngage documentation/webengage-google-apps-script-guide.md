# WebEngage Google Apps Script Integration Guide

## Table of Contents
1. [Overview](#overview)
2. [Setup and Configuration](#setup-and-configuration)
3. [Core Functions](#core-functions)
4. [User Management](#user-management)
5. [Event Tracking](#event-tracking)
6. [Bulk Operations](#bulk-operations)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)
9. [Code Examples](#code-examples)
10. [Troubleshooting](#troubleshooting)

## Overview

This guide provides comprehensive Google Apps Script integration patterns for WebEngage automation, focusing on user management and event tracking for enterprise implementations.

### Key Integration Points
- **User Creation and Updates**: Bulk user management via REST API
- **Event Logging**: Real-time event tracking for user actions
- **Data Synchronization**: Sync data between Google Sheets and WebEngage
- **Automated Workflows**: Trigger-based automation for marketing campaigns

## Setup and Configuration

### Prerequisites
1. **WebEngage Account**: Active enterprise account with API access
2. **License Code**: Your WebEngage license code
3. **API Key**: Generated from WebEngage dashboard
4. **Data Center**: Your WebEngage data center (e.g., `us`, `eu`, `in`)

### Configuration Object
```javascript
const WEBENGAGE_CONFIG = {
  licenseCode: 'YOUR_LICENSE_CODE',
  apiKey: 'YOUR_API_KEY',
  dataCenter: 'us', // or 'eu', 'in'
  baseUrl: 'https://api.webengage.com',
  timeout: 30000, // 30 seconds
  retryAttempts: 3
};
```

### Environment Setup
```javascript
// Store configuration in Script Properties
function setupWebEngageConfig() {
  const config = {
    licenseCode: 'YOUR_LICENSE_CODE',
    apiKey: 'YOUR_API_KEY',
    dataCenter: 'us'
  };
  
  PropertiesService.getScriptProperties().setProperties(config);
}

// Retrieve configuration
function getWebEngageConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    licenseCode: props.getProperty('licenseCode'),
    apiKey: props.getProperty('apiKey'),
    dataCenter: props.getProperty('dataCenter'),
    baseUrl: 'https://api.webengage.com',
    timeout: 30000,
    retryAttempts: 3
  };
}
```

## Core Functions

### HTTP Request Utility
```javascript
function makeWebEngageRequest(endpoint, method, data, retryCount = 0) {
  const config = getWebEngageConfig();
  const url = `${config.baseUrl}/v1/${config.licenseCode}/${endpoint}`;
  
  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${config.apiKey}`,
      'User-Agent': 'GoogleAppsScript/WebEngage'
    },
    muteHttpExceptions: true,
    timeout: config.timeout
  };
  
  if (data && (method === 'POST' || method === 'PUT')) {
    options.payload = JSON.stringify(data);
  }
  
  try {
    const response = UrlFetchApp.fetch(url, options);
    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();
    
    if (responseCode >= 200 && responseCode < 300) {
      return {
        success: true,
        data: JSON.parse(responseText),
        statusCode: responseCode
      };
    } else {
      console.error(`WebEngage API Error: ${responseCode} - ${responseText}`);
      return {
        success: false,
        error: responseText,
        statusCode: responseCode
      };
    }
  } catch (error) {
    console.error(`Request failed: ${error.toString()}`);
    
    if (retryCount < config.retryAttempts) {
      Utilities.sleep(1000 * (retryCount + 1)); // Exponential backoff
      return makeWebEngageRequest(endpoint, method, data, retryCount + 1);
    }
    
    return {
      success: false,
      error: error.toString(),
      statusCode: 0
    };
  }
}
```

### Rate Limiting Utility
```javascript
class RateLimiter {
  constructor(maxRequests = 100, timeWindow = 60000) {
    this.maxRequests = maxRequests;
    this.timeWindow = timeWindow;
    this.requests = [];
  }
  
  async executeRequest(requestFunction) {
    this.cleanup();
    
    if (this.requests.length >= this.maxRequests) {
      const oldestRequest = this.requests[0];
      const waitTime = this.timeWindow - (Date.now() - oldestRequest);
      if (waitTime > 0) {
        Utilities.sleep(waitTime);
      }
    }
    
    this.requests.push(Date.now());
    return requestFunction();
  }
  
  cleanup() {
    const cutoff = Date.now() - this.timeWindow;
    this.requests = this.requests.filter(time => time > cutoff);
  }
}

// Global rate limiter instance
const rateLimiter = new RateLimiter(100, 60000); // 100 requests per minute
```

## User Management

### Create Single User
```javascript
function createUser(userData) {
  const endpoint = 'users';
  const payload = {
    userId: userData.userId,
    firstName: userData.firstName,
    lastName: userData.lastName,
    email: userData.email,
    phone: userData.phone,
    attributes: userData.attributes || {}
  };
  
  return rateLimiter.executeRequest(() => 
    makeWebEngageRequest(endpoint, 'POST', payload)
  );
}

// Example usage
function createUserExample() {
  const userData = {
    userId: 'customer_12345',
    firstName: 'John',
    lastName: 'Doe',
    email: 'john.doe@example.com',
    phone: '+1234567890',
    attributes: {
      customerType: 'premium',
      signupDate: '2024-01-15',
      totalSpent: 1500.00
    }
  };
  
  const result = createUser(userData);
  if (result.success) {
    console.log('User created successfully:', result.data);
  } else {
    console.error('Failed to create user:', result.error);
  }
}
```

### Update User
```javascript
function updateUser(userId, userData) {
  const endpoint = `users/${userId}`;
  const payload = {
    firstName: userData.firstName,
    lastName: userData.lastName,
    email: userData.email,
    phone: userData.phone,
    attributes: userData.attributes || {}
  };
  
  return rateLimiter.executeRequest(() => 
    makeWebEngageRequest(endpoint, 'PUT', payload)
  );
}

// Example usage
function updateUserExample() {
  const userData = {
    firstName: 'John',
    lastName: 'Smith',
    email: 'john.smith@example.com',
    attributes: {
      customerType: 'vip',
      lastPurchaseDate: '2024-01-20',
      totalSpent: 2500.00
    }
  };
  
  const result = updateUser('customer_12345', userData);
  if (result.success) {
    console.log('User updated successfully:', result.data);
  } else {
    console.error('Failed to update user:', result.error);
  }
}
```

### Bulk User Operations
```javascript
function bulkCreateUsers(usersArray, batchSize = 100) {
  const results = [];
  const batches = [];
  
  // Split into batches
  for (let i = 0; i < usersArray.length; i += batchSize) {
    batches.push(usersArray.slice(i, i + batchSize));
  }
  
  // Process each batch
  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const batchResults = [];
    
    for (const userData of batch) {
      const result = createUser(userData);
      batchResults.push({
        userId: userData.userId,
        success: result.success,
        data: result.data,
        error: result.error
      });
    }
    
    results.push(...batchResults);
    
    // Add delay between batches to respect rate limits
    if (i < batches.length - 1) {
      Utilities.sleep(1000);
    }
  }
  
  return results;
}

// Example usage
function bulkCreateUsersExample() {
  const users = [
    {
      userId: 'customer_001',
      firstName: 'Alice',
      lastName: 'Johnson',
      email: 'alice@example.com',
      attributes: { customerType: 'new' }
    },
    {
      userId: 'customer_002',
      firstName: 'Bob',
      lastName: 'Wilson',
      email: 'bob@example.com',
      attributes: { customerType: 'returning' }
    }
    // ... more users
  ];
  
  const results = bulkCreateUsers(users);
  
  // Process results
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`Successfully created ${successful.length} users`);
  console.log(`Failed to create ${failed.length} users`);
  
  if (failed.length > 0) {
    console.error('Failed users:', failed);
  }
}
```

## Event Tracking

### Track Single Event
```javascript
function trackEvent(userId, eventName, eventData, eventTime = null) {
  const endpoint = 'events';
  const payload = {
    userId: userId,
    eventName: eventName,
    eventTime: eventTime || new Date().toISOString(),
    eventData: eventData || {}
  };
  
  return rateLimiter.executeRequest(() => 
    makeWebEngageRequest(endpoint, 'POST', payload)
  );
}

// Example usage
function trackPurchaseEvent() {
  const eventData = {
    orderId: 'ORD-2024-001',
    totalAmount: 299.99,
    currency: 'USD',
    paymentMethod: 'credit_card',
    items: [
      {
        productId: 'PROD-123',
        productName: 'Wireless Headphones',
        quantity: 1,
        price: 199.99
      },
      {
        productId: 'PROD-456',
        productName: 'Phone Case',
        quantity: 2,
        price: 50.00
      }
    ]
  };
  
  const result = trackEvent('customer_12345', 'purchase_completed', eventData);
  if (result.success) {
    console.log('Event tracked successfully:', result.data);
  } else {
    console.error('Failed to track event:', result.error);
  }
}
```

### Track Multiple Events
```javascript
function trackMultipleEvents(eventsArray, batchSize = 50) {
  const results = [];
  const batches = [];
  
  // Split into batches
  for (let i = 0; i < eventsArray.length; i += batchSize) {
    batches.push(eventsArray.slice(i, i + batchSize));
  }
  
  // Process each batch
  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const batchResults = [];
    
    for (const event of batch) {
      const result = trackEvent(
        event.userId,
        event.eventName,
        event.eventData,
        event.eventTime
      );
      batchResults.push({
        userId: event.userId,
        eventName: event.eventName,
        success: result.success,
        data: result.data,
        error: result.error
      });
    }
    
    results.push(...batchResults);
    
    // Add delay between batches
    if (i < batches.length - 1) {
      Utilities.sleep(500);
    }
  }
  
  return results;
}

// Example usage
function trackMultipleEventsExample() {
  const events = [
    {
      userId: 'customer_001',
      eventName: 'product_viewed',
      eventData: {
        productId: 'PROD-123',
        productName: 'Wireless Headphones',
        category: 'Electronics'
      }
    },
    {
      userId: 'customer_002',
      eventName: 'cart_item_added',
      eventData: {
        productId: 'PROD-456',
        productName: 'Phone Case',
        quantity: 1
      }
    }
    // ... more events
  ];
  
  const results = trackMultipleEvents(events);
  
  // Process results
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`Successfully tracked ${successful.length} events`);
  console.log(`Failed to track ${failed.length} events`);
}
```

### Common Event Patterns
```javascript
// E-commerce Events
function trackEcommerceEvents() {
  // Product Viewed
  trackEvent('customer_123', 'product_viewed', {
    productId: 'PROD-123',
    productName: 'Wireless Headphones',
    category: 'Electronics',
    price: 199.99,
    currency: 'USD'
  });
  
  // Cart Item Added
  trackEvent('customer_123', 'cart_item_added', {
    productId: 'PROD-123',
    productName: 'Wireless Headphones',
    quantity: 1,
    price: 199.99
  });
  
  // Purchase Completed
  trackEvent('customer_123', 'purchase_completed', {
    orderId: 'ORD-2024-001',
    totalAmount: 199.99,
    currency: 'USD',
    paymentMethod: 'credit_card'
  });
}

// SaaS Events
function trackSaaSEvents() {
  // User Signed Up
  trackEvent('user_456', 'user_signed_up', {
    planType: 'premium',
    signupSource: 'website',
    referralCode: 'FRIEND10'
  });
  
  // Feature Used
  trackEvent('user_456', 'feature_used', {
    featureName: 'analytics_dashboard',
    usageDuration: 300,
    sessionId: 'sess_12345'
  });
  
  // Subscription Renewed
  trackEvent('user_456', 'subscription_renewed', {
    planType: 'premium',
    renewalAmount: 99.99,
    currency: 'USD'
  });
}
```

## Bulk Operations

### Bulk User Import from Google Sheets
```javascript
function importUsersFromSheet(sheetName, startRow = 2) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  const data = sheet.getDataRange().getValues();
  
  const users = [];
  
  for (let i = startRow - 1; i < data.length; i++) {
    const row = data[i];
    
    // Assuming columns: A=userId, B=firstName, C=lastName, D=email, E=phone, F=attributes
    const user = {
      userId: row[0],
      firstName: row[1],
      lastName: row[2],
      email: row[3],
      phone: row[4],
      attributes: {}
    };
    
    // Parse attributes from column F (JSON string)
    if (row[5]) {
      try {
        user.attributes = JSON.parse(row[5]);
      } catch (e) {
        console.error(`Invalid JSON in row ${i + 1}: ${row[5]}`);
      }
    }
    
    users.push(user);
  }
  
  return bulkCreateUsers(users);
}

// Example usage
function importUsersExample() {
  const results = importUsersFromSheet('Users');
  
  // Log results to a new sheet
  const resultSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Import Results') || 
                     SpreadsheetApp.getActiveSpreadsheet().insertSheet('Import Results');
  
  resultSheet.clear();
  resultSheet.getRange(1, 1, 1, 4).setValues([['User ID', 'Success', 'Data', 'Error']]);
  
  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    resultSheet.getRange(i + 2, 1, 1, 4).setValues([
      [result.userId, result.success, JSON.stringify(result.data), result.error || '']
    ]);
  }
}
```

### Bulk Event Import from Google Sheets
```javascript
function importEventsFromSheet(sheetName, startRow = 2) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  const data = sheet.getDataRange().getValues();
  
  const events = [];
  
  for (let i = startRow - 1; i < data.length; i++) {
    const row = data[i];
    
    // Assuming columns: A=userId, B=eventName, C=eventData, D=eventTime
    const event = {
      userId: row[0],
      eventName: row[1],
      eventData: {},
      eventTime: row[3] || new Date().toISOString()
    };
    
    // Parse event data from column C (JSON string)
    if (row[2]) {
      try {
        event.eventData = JSON.parse(row[2]);
      } catch (e) {
        console.error(`Invalid JSON in row ${i + 1}: ${row[2]}`);
      }
    }
    
    events.push(event);
  }
  
  return trackMultipleEvents(events);
}

// Example usage
function importEventsExample() {
  const results = importEventsFromSheet('Events');
  
  // Log results to a new sheet
  const resultSheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Event Import Results') || 
                     SpreadsheetApp.getActiveSpreadsheet().insertSheet('Event Import Results');
  
  resultSheet.clear();
  resultSheet.getRange(1, 1, 1, 5).setValues([['User ID', 'Event Name', 'Success', 'Data', 'Error']]);
  
  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    resultSheet.getRange(i + 2, 1, 1, 5).setValues([
      [result.userId, result.eventName, result.success, JSON.stringify(result.data), result.error || '']
    ]);
  }
}
```

## Error Handling

### Comprehensive Error Handler
```javascript
function handleWebEngageError(error, context) {
  const errorLog = {
    timestamp: new Date().toISOString(),
    context: context,
    error: error.toString(),
    stack: error.stack
  };
  
  // Log to console
  console.error('WebEngage Error:', errorLog);
  
  // Log to Google Sheets for monitoring
  logErrorToSheet(errorLog);
  
  // Send notification if critical
  if (isCriticalError(error)) {
    sendErrorNotification(errorLog);
  }
  
  return errorLog;
}

function logErrorToSheet(errorLog) {
  try {
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Error Log') || 
                 SpreadsheetApp.getActiveSpreadsheet().insertSheet('Error Log');
    
    sheet.appendRow([
      errorLog.timestamp,
      errorLog.context,
      errorLog.error,
      errorLog.stack
    ]);
  } catch (e) {
    console.error('Failed to log error to sheet:', e);
  }
}

function isCriticalError(error) {
  const criticalPatterns = [
    'authentication',
    'rate limit exceeded',
    'invalid license',
    'server error'
  ];
  
  const errorString = error.toString().toLowerCase();
  return criticalPatterns.some(pattern => errorString.includes(pattern));
}

function sendErrorNotification(errorLog) {
  // Implement your notification logic here
  // Could be email, Slack, etc.
  console.log('Critical error notification sent:', errorLog);
}
```

### Retry Logic with Exponential Backoff
```javascript
function executeWithRetry(operation, maxRetries = 3, baseDelay = 1000) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return operation();
    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }
      
      const delay = baseDelay * Math.pow(2, attempt - 1);
      console.log(`Attempt ${attempt} failed, retrying in ${delay}ms...`);
      Utilities.sleep(delay);
    }
  }
}

// Example usage
function createUserWithRetry(userData) {
  return executeWithRetry(() => createUser(userData));
}
```

## Best Practices

### Configuration Management
```javascript
// Store sensitive data in Script Properties
function setupSecureConfig() {
  const config = {
    licenseCode: 'YOUR_LICENSE_CODE',
    apiKey: 'YOUR_API_KEY',
    dataCenter: 'us'
  };
  
  PropertiesService.getScriptProperties().setProperties(config);
}

// Validate configuration
function validateConfig() {
  const config = getWebEngageConfig();
  const required = ['licenseCode', 'apiKey', 'dataCenter'];
  
  for (const field of required) {
    if (!config[field]) {
      throw new Error(`Missing required configuration: ${field}`);
    }
  }
  
  return true;
}
```

### Data Validation
```javascript
function validateUserData(userData) {
  const errors = [];
  
  if (!userData.userId) {
    errors.push('userId is required');
  }
  
  if (userData.email && !isValidEmail(userData.email)) {
    errors.push('Invalid email format');
  }
  
  if (userData.phone && !isValidPhone(userData.phone)) {
    errors.push('Invalid phone format');
  }
  
  if (errors.length > 0) {
    throw new Error(`Validation errors: ${errors.join(', ')}`);
  }
  
  return true;
}

function validateEventData(eventData) {
  const errors = [];
  
  if (!eventData.eventName) {
    errors.push('eventName is required');
  }
  
  if (eventData.eventName && eventData.eventName.length > 50) {
    errors.push('eventName must be 50 characters or less');
  }
  
  if (errors.length > 0) {
    throw new Error(`Validation errors: ${errors.join(', ')}`);
  }
  
  return true;
}

function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

function isValidPhone(phone) {
  const phoneRegex = /^\+?[\d\s\-\(\)]+$/;
  return phoneRegex.test(phone);
}
```

### Performance Optimization
```javascript
// Batch processing for large datasets
function processLargeDataset(data, batchSize = 100, delayBetweenBatches = 1000) {
  const results = [];
  const batches = [];
  
  // Split into batches
  for (let i = 0; i < data.length; i += batchSize) {
    batches.push(data.slice(i, i + batchSize));
  }
  
  // Process batches with delays
  for (let i = 0; i < batches.length; i++) {
    const batch = batches[i];
    const batchResults = processBatch(batch);
    results.push(...batchResults);
    
    // Add delay between batches
    if (i < batches.length - 1) {
      Utilities.sleep(delayBetweenBatches);
    }
  }
  
  return results;
}

// Cache frequently used data
const cache = new Map();

function getCachedData(key, fetchFunction, ttl = 300000) { // 5 minutes TTL
  const cached = cache.get(key);
  
  if (cached && (Date.now() - cached.timestamp) < ttl) {
    return cached.data;
  }
  
  const data = fetchFunction();
  cache.set(key, {
    data: data,
    timestamp: Date.now()
  });
  
  return data;
}
```

## Code Examples

### Complete User Management System
```javascript
class WebEngageUserManager {
  constructor() {
    this.config = getWebEngageConfig();
    this.rateLimiter = new RateLimiter(100, 60000);
  }
  
  createUser(userData) {
    validateUserData(userData);
    return this.rateLimiter.executeRequest(() => 
      makeWebEngageRequest('users', 'POST', userData)
    );
  }
  
  updateUser(userId, userData) {
    validateUserData({...userData, userId});
    return this.rateLimiter.executeRequest(() => 
      makeWebEngageRequest(`users/${userId}`, 'PUT', userData)
    );
  }
  
  bulkCreateUsers(usersArray) {
    return bulkCreateUsers(usersArray);
  }
  
  getUser(userId) {
    return this.rateLimiter.executeRequest(() => 
      makeWebEngageRequest(`users/${userId}`, 'GET')
    );
  }
}

// Usage
function userManagementExample() {
  const userManager = new WebEngageUserManager();
  
  // Create a user
  const userData = {
    userId: 'customer_12345',
    firstName: 'John',
    lastName: 'Doe',
    email: 'john.doe@example.com',
    attributes: {
      customerType: 'premium',
      signupDate: '2024-01-15'
    }
  };
  
  const result = userManager.createUser(userData);
  console.log('User creation result:', result);
}
```

### Complete Event Tracking System
```javascript
class WebEngageEventTracker {
  constructor() {
    this.config = getWebEngageConfig();
    this.rateLimiter = new RateLimiter(100, 60000);
  }
  
  trackEvent(userId, eventName, eventData, eventTime = null) {
    validateEventData({eventName});
    
    const payload = {
      userId: userId,
      eventName: eventName,
      eventTime: eventTime || new Date().toISOString(),
      eventData: eventData || {}
    };
    
    return this.rateLimiter.executeRequest(() => 
      makeWebEngageRequest('events', 'POST', payload)
    );
  }
  
  trackMultipleEvents(eventsArray) {
    return trackMultipleEvents(eventsArray);
  }
  
  // Predefined event methods
  trackPurchase(userId, orderData) {
    return this.trackEvent(userId, 'purchase_completed', orderData);
  }
  
  trackProductView(userId, productData) {
    return this.trackEvent(userId, 'product_viewed', productData);
  }
  
  trackCartAdd(userId, cartData) {
    return this.trackEvent(userId, 'cart_item_added', cartData);
  }
  
  trackSignup(userId, signupData) {
    return this.trackEvent(userId, 'user_signed_up', signupData);
  }
}

// Usage
function eventTrackingExample() {
  const eventTracker = new WebEngageEventTracker();
  
  // Track a purchase
  const purchaseData = {
    orderId: 'ORD-2024-001',
    totalAmount: 299.99,
    currency: 'USD',
    items: [
      {productId: 'PROD-123', quantity: 1, price: 199.99},
      {productId: 'PROD-456', quantity: 2, price: 50.00}
    ]
  };
  
  const result = eventTracker.trackPurchase('customer_12345', purchaseData);
  console.log('Purchase tracking result:', result);
}
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Authentication Errors
```javascript
function diagnoseAuthIssues() {
  const config = getWebEngageConfig();
  
  console.log('Checking configuration...');
  console.log('License Code:', config.licenseCode ? 'Set' : 'Missing');
  console.log('API Key:', config.apiKey ? 'Set' : 'Missing');
  console.log('Data Center:', config.dataCenter);
  
  // Test API connection
  const testResult = makeWebEngageRequest('users', 'GET');
  console.log('API Test Result:', testResult);
}
```

#### 2. Rate Limiting Issues
```javascript
function checkRateLimits() {
  const config = getWebEngageConfig();
  console.log('Current rate limit settings:');
  console.log('- Max requests per minute:', config.maxRequests || 100);
  console.log('- Time window (ms):', config.timeWindow || 60000);
}
```

#### 3. Data Validation Issues
```javascript
function validateDataFormat(data, type) {
  const errors = [];
  
  if (type === 'user') {
    if (!data.userId) errors.push('Missing userId');
    if (data.email && !isValidEmail(data.email)) errors.push('Invalid email');
  } else if (type === 'event') {
    if (!data.eventName) errors.push('Missing eventName');
    if (data.eventName && data.eventName.length > 50) errors.push('Event name too long');
  }
  
  return errors;
}
```

### Debugging Utilities
```javascript
function enableDebugMode() {
  PropertiesService.getScriptProperties().setProperty('debug', 'true');
}

function disableDebugMode() {
  PropertiesService.getScriptProperties().deleteProperty('debug');
}

function isDebugMode() {
  return PropertiesService.getScriptProperties().getProperty('debug') === 'true';
}

function debugLog(message, data = null) {
  if (isDebugMode()) {
    console.log(`[DEBUG] ${message}`, data);
  }
}
```

---

*This guide provides comprehensive Google Apps Script integration patterns for WebEngage automation, covering user management, event tracking, bulk operations, and best practices for enterprise implementations.* 