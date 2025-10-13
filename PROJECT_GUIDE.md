# Zoom → WebEngage Ingestion Platform – End-to-End Guide

## Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture & Flow](#system-architecture--flow)
3. [Supported Products & Profiles](#supported-products--profiles)
4. [Data Processing Pipelines](#data-processing-pipelines)
5. [Streamlit Application Features](#streamlit-application-features)
6. [WebEngage Integration](#webengage-integration)
7. [Input & Output Schemas](#input--output-schemas)
8. [Deployment & Operations](#deployment--operations)
9. [Diagnostics & Troubleshooting](#diagnostics--troubleshooting)

---

## Project Overview

This Streamlit-powered platform converts raw Zoom webinar and bootcamp CSV exports into WebEngage-ready datasets and (optionally) fires the corresponding WebEngage user and event APIs. The app encapsulates all data cleansing, enrichment, validation, deduplication, and event construction logic through reusable profiles for each product/use-case combination.

### Key Capabilities
- **Profile registry** covering Plutus and TLS programs with 17 pre-configured workflows
- **Three pipeline types**: attendee processing, registration processing, and dual bootcamp (registration + attendance)
- **High data fidelity** through schema validation, datetime parsing thresholds, conductor verification, and phone-number hygiene
- **Integrated event delivery** to WebEngage (user upsert + event publish) with detailed success/failure reporting
- **Downloadable clean datasets** for offline usage when event firing is skipped or as a secondary audit trail

---

## System Architecture & Flow

1. **Profile selection** – The sidebar registry determines which workflow configuration is loaded (event names, category mode, download filename, etc.).
2. **Raw CSV ingestion** – Users upload the unmodified Zoom export for attendees, registrants, or bootcamp sessions.
3. **Structured parsing** – The file is split into logical sections (Topic, Host, Panelist, Attendee/Registrant) and validated against expected column layouts.
4. **Normalization & enrichment** – Names, phones, emails, datetimes, and metadata are standardized; categories and conductors are resolved using profile defaults and user overrides.
5. **Deduplication & schema assurance** – Records are aggregated primarily by phone, secondarily by email, and reshaped into canonical output schemas.
6. **Optional WebEngage firing** – When enabled, each record triggers a user upsert followed by the configured event(s), with per-row telemetry.
7. **Results delivery** – The app renders metrics, diagnostics, warnings, preview tables, and offers a CSV download of the cleaned dataset.

---

## Supported Products & Profiles

| Product | Workflow | Type | WebEngage Event(s) | Download Name |
| --- | --- | --- | --- | --- |
| Plutus | Webinar Attended | `webinar_attended` | Plutus Webinar Attended | `plutus_webinar_attended.csv` |
| Plutus | Webinar Registered | `registration` | Plutus Webinar Registered | `plutus_webinar_registered.csv` |
| Plutus | Bootcamp | `bootcamp_dual` | Plutus Bootcamp Registered + Attended | `plutus_bootcamp.csv` |
| TLS | Webinar Attended – CD/IP/MA/TF/ADR/Misc | `webinar_attended` | TLS Webinar Attended [TRACK] | `tls_webinar_attended_[track].csv` |
| TLS | Webinar Registered – CD/IP/MA/TF/ADR/Misc | `registration` | TLS Webinar Registered [TRACK] | `tls_webinar_registered_[track].csv` |
| TLS | Bootcamp – Misc | `webinar_attended` | TLS Misc Bootcamp Attended | `tls_misc_bootcamp.csv` |

**Category Modes**
- *Auto*: Plutus webinar pipelines derive category tokens from the topic via configurable keyword mappings.
- *Fixed*: TLS workflows expose curated category/track options; overrides are still supported.

**Bootcamp Handling**
- Plutus bootcamp runs the dual pipeline (registration + attendance) and infers Day 1/Day 2 from the topic using regex, with weekend-based fallback logic.
- TLS bootcamp currently uses the attendee pipeline with track fixed to “Bootcamp”.

---

## Data Processing Pipelines

### 1. Webinar Attended (`webinar_attended`)
- **Section validation**: Ensures Attendee Details are present and match the 14-column SOP.
- **Normalization**: Proper-cases names, lowercases emails, standardizes phone numbers (10-digit core with `91` prefix), and parses join/leave timestamps.
- **Deduplication**: Aggregates duplicate attendees by phone/email, retaining earliest join, latest leave, and maximum session duration.
- **Metadata enrichment**: Attaches webinar date, conductor, derived category, Zoom ID/name, and user ID (`91` + sanitized phone).
- **Output**: 22-column clean dataframe matching the `CLEAN_SCHEMA`, optionally augmented with “Bootcamp Day” for dual pipelines.

### 2. Registration (`registration`)
- **Schema enforcement**: Validates the 8-column registration layout contained in the Attendee Details section of Zoom registrant exports.
- **Normalization & deduplication**: Mirrors attendee hygiene, prioritizing first successful registration per phone/email.
- **Metadata enrichment**: Associates webinar identifiers, dates, and derived categories to prepare the event payload.
- **Output**: 14-column dataframe aligning with `REGISTRATION_SCHEMA` and ready for event generation or download.

### 3. Bootcamp Dual (`bootcamp_dual`)
- **Day inference**: Extracts “Day 1/Day 2” from webinar titles (`Day`, `Day-`, `Day_` variations) with fallback to weekend heuristics.
- **Dual payloads**: After cleaning, each record produces both registration and attendance WebEngage events using consistent BootcampDay labels (`Day1` for payloads, `Day 1` in CSV).
- **Warnings**: Surfaces errors when day detection fails or defaults are applied.

Across all pipelines, the app captures processing statistics (parse success ratios, dedup counts), warnings (invalid phones, unapproved conductors), and metadata metrics for on-screen review.

---

## Streamlit Application Features

- **Dynamic sidebar** with product/use-case selectors, category configuration (JSON token maps or dropdown overrides), conductor mapping overrides, approved conductor lists, datetime parse threshold slider, and WebEngage credential inputs.
- **Adaptive uploader** renaming based on pipeline type (`Raw Zoom attendee CSV`, `Raw Zoom registrant CSV`, or bootcamp-specific copy).
- **Processing controls** featuring clear CTA buttons and spinners while transformations run.
- **Result dashboard** providing:
  - Success toast summarizing processed record counts
  - Metadata metrics (workflow, product, category, conductor, bootcamp day, event names)
  - Data preview grid with container-width display
  - Diagnostics section highlighting parse ratios, dedup summaries, and warnings
  - WebEngage event summaries with per-row failure grids when firing is enabled
  - Log panel enumerating each transformation step applied
- **CSV download** button exporting the cleaned dataset with profile-specific filenames.

---

## WebEngage Integration

### Authentication
- Requires REST API Key and License Code, supplied either via Streamlit Secrets (`st.secrets['webengage']`) or inline inputs.
- Secrets fallback: local `.streamlit/secrets.toml` reader supports development without exposing credentials.

### User Upsert
- For every record, the system normalizes payloads via `build_user_payload`, setting `userId` as `91` + sanitized phone and attaching name/email/phone attributes plus opt-in flags.

### Event Payloads
- **Attendee events** (`build_attendee_event_payload`): send join/leave times, session duration, conductor, webinar metadata, category/track, and product tags.
- **Registration events** (`build_registration_event_payload`): include registration timestamp, approval status, source, and webinar identifiers alongside product/track metadata.
- **Bootcamp events** (`build_bootcamp_registration_event_payload` & `build_bootcamp_attended_event_payload`): mirror attendee/registration payloads with an added `BootcampDay` attribute and inherited extra attributes from the profile registry.

### Delivery Reporting
- `fire_*` helpers upsert the user first, then emit the event. Failures are captured with row index, userId, HTTP status, and API message, surfaced in dedicated dataframes for quick triage.
- Bootcamp dual firing tracks registration and attendance success counts separately.

---

## Input & Output Schemas

### Zoom Input Expectations
```
Topic
Topic,Webinar ID,Actual Start Time,Duration,...

Host Details
User Name,Email,Join Time,...

Panelist Details
User Name,Email,Join Time,...

Attendee Details / Registrant Details
Attended,User Name (Original Name),First Name,...
```

### Cleaned Output (Attendee Pipeline)
1. Webinar Date
2. Bootcamp Day
3. Category
4. Webinar ID
5. Attended
6. User Name (Original Name)
7. First Name
8. Last Name
9. Email
10. Phone (prefixed with `91`)
11. Registration Time
12. Approval Status
13. Registration Source
14. Attendance Type
15. Join Time
16. Leave Time
17. Time in Session (minutes)
18. Is Guest
19. Country/Region Name
20. UserID
21. Webinar name
22. Webinar conductor

### Cleaned Output (Registration Pipeline)
1. User Name (Original Name)
2. First Name
3. Last Name
4. Email
5. Registration Time
6. Approval Status
7. Phone (prefixed with `91`)
8. Registration Source
9. Attendance Type
10. UserID
11. Webinar ID
12. Webinar name
13. Webinar Date

---

## Deployment & Operations

### Local Development
```bash
python3 -m pip install -r requirements.txt
streamlit run streamlit_app.py
```
- Optional: populate `.streamlit/secrets.toml` with WebEngage credentials under the `webengage` table for local firing.

### Streamlit Cloud
1. Push repository (including `requirements.txt`) to GitHub.
2. Deploy on Streamlit Cloud by pointing to the `main` branch.
3. Configure secrets (`REST API Key`, `License Code`) via the Streamlit Cloud Secrets manager.
4. Launch the public URL; the app auto-detects secrets and hides them from the UI.

### Operational Tips
- Retain raw Zoom exports in case reprocessing is required.
- Use “Clean only” mode for validation before enabling WebEngage firing in production.
- Review event failure tables immediately after firing to retry affected rows.

---

## Diagnostics & Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| Datetime parse ratio below threshold | Non-standard timestamp formats | Adjust threshold slider or normalize input timestamps before upload |
| “Missing Attendee Details section” error | Incomplete Zoom export | Re-export the full attendee/registrant report with all sections |
| High invalid phone drops | Numbers not 10 digits / formatting issues | Clean source data, ensure country code not embedded, or capture alternate phones |
| Conductor warning banner | Name not present in approved list/map | Update sidebar JSON map or append to approved list, then reprocess |
| WebEngage user/event failures | Incorrect credentials or API downtime | Verify secrets, inspect error dataframe for status codes, retry after fixes |
| Bootcamp day warning | Title lacks “Day 1/2” signal | Rename session in Zoom or rely on weekend fallback; update manually if needed |

---

*Last Updated: 2025-10-09*
