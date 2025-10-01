# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a **Zoom Webinar Data Ingestion and Processing Project** that handles the complete pipeline from raw Zoom webinar exports to WebEngage marketing automation. The system processes CSV files containing webinar attendee and registration data, normalizes them according to strict SOPs, and integrates with WebEngage for customer engagement.

## Architecture Components

### Core Processing Engine (`streamlit_app.py`)
- **Streamlit web application** providing the main user interface
- Handles two workflows: "Webinar Attendees" and "Webinar Registrations"
- Implements strict data validation and normalization according to SOP requirements
- Features section-based CSV parsing (Topic, Host Details, Panelist Details, Attendee Details)
- Deduplication logic based on phone/email priority with time aggregation rules
- Real-time data quality gates and validation (datetime parsing, phone number validation)

### Google Apps Script Integration (`gs code`)
- **WebEngage automation script** for Google Sheets integration
- Triggers on form submissions to automatically create users and track events
- Implements collision-safe event handling with unique function naming
- Features comprehensive error handling and audit logging
- Configurable conductor mapping and category token resolution

### WebEngage API Documentation
- Complete REST API integration guide for marketing automation
- User management, event tracking, and bulk operations
- Rate limiting and error handling patterns
- Authentication and security best practices

### Data Processing Standards (SOP)
- **Deterministic processing pipeline** with 11 ordered steps
- Strict schema validation with required 14-column attendee format
- Data quality gates including 99% datetime parse success threshold
- Deduplication rules with time-in-session aggregation
- Proper case normalization and canonical boolean values

## Common Development Commands

### Running the Application
```bash
# Start the Streamlit web interface
streamlit run streamlit_app.py

# Run with specific port
streamlit run streamlit_app.py --server.port 8501
```

### Development Dependencies
The project requires these Python packages (install as needed):
```bash
pip install streamlit pandas
```

### Data Processing
```bash
# Process a single CSV file through the Streamlit interface
# Upload via the web UI at http://localhost:8501

# The application accepts raw Zoom webinar CSV exports with sections:
# - Topic (webinar metadata)
# - Host Details
# - Panelist Details  
# - Attendee Details (main processing target)
```

### Google Apps Script Deployment
```javascript
// Deploy the 'gs code' to Google Apps Script
// Set up installable triggers for form submissions
// Configure constants: WEBINAR_SHEET_ID, WEBINAR_WEBENGAGE_LICENSE_CODE, WEBINAR_WEBENGAGE_API_KEY
```

## Data Flow Architecture

1. **Ingestion**: Raw Zoom CSV with multiple sections
2. **Section Parsing**: Identifies and extracts Topic, Host, Panelist, and Attendee data
3. **Schema Validation**: Enforces exact 14-column attendee format
4. **Normalization**: Cleans names, phones, emails, timestamps per SOP rules
5. **Deduplication**: Groups by phone (priority) or email with time aggregation
6. **Enrichment**: Adds category, conductor, webinar metadata from Topic section
7. **Output**: Clean 18-column format ready for WebEngage ingestion

## Key Configuration Maps

### Category Token Mapping
```json
{
  "acca": "ACCA",
  "cma": "CMA", 
  "cfa": "CFA",
  "cpa": "CPA"
}
```

### Conductor Mapping
Maps Webinar ID to conductor name, with fallback to Panelist or Host names.

### Approved Conductors
- Sukhpreet Monga
- Satyarth Dwivedi  
- Khushi Gera

## Data Quality Standards

- **Phone Validation**: Must be exactly 10 digits after normalization
- **DateTime Parsing**: Day-first format with 99% success rate requirement
- **Boolean Normalization**: "Yes"/"No" canonical format
- **Deduplication**: Phone-based grouping with time-in-session summation
- **UserID Generation**: Phone number with "91" prefix

## WebEngage Integration

The system integrates with WebEngage for:
- **User Creation**: Automatic user profile creation with attributes
- **Event Tracking**: "Plutus Webinar Attended" events with rich metadata
- **Bulk Operations**: Batch processing for large datasets
- **Rate Limiting**: 5,000 requests per minute with exponential backoff

## File Processing Rules

### Input Requirements
- CSV files with BOM handling (UTF-8-sig)
- Section-based structure with single-cell section headers
- Exact column matching for Attendee Details section
- Support for optional "Source Name" column (automatically dropped)

### Output Guarantees
- Exactly 18 columns in predefined order
- All dates in DD/MM/YYYY format (webinar date) or DD/MM/YYYY hh:mm:ss AM/PM format (timestamps)
- Phone numbers as digits-only strings
- UserID matches Phone field
- Boolean fields as "Yes"/"No" strings

## Troubleshooting Common Issues

### Schema Validation Failures
- Verify CSV has exact column headers matching SOP specification
- Check for extra/missing columns in Attendee Details section
- Ensure proper section structure with single-cell headers

### DateTime Parsing Issues  
- Adjust parse threshold below 99% if source data quality is poor
- Check for consistent date formats in source data
- Verify day-first parsing assumption matches source format

### WebEngage API Errors
- Verify API key and license code configuration
- Check rate limiting - implement delays between bulk operations
- Validate user data completeness (phone/email required for user creation)

### Google Apps Script Issues
- Ensure installable triggers are set up correctly
- Check sheet permissions and data access
- Verify WebEngage API credentials in script constants

## Testing and Validation

The system includes comprehensive validation at multiple stages:
- Input schema validation (Gate A)
- Clean output schema validation (Gate B) 
- Boolean value validation (Gate C)
- DateTime parsing success validation (Gate D)
- Phone number format validation (Gate E)

All validations are logged with detailed statistics for monitoring data quality and processing success rates.