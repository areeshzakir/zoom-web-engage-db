import csv
import json
import math
import re
import time
from datetime import datetime, timezone, timedelta
from io import StringIO
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import requests
import streamlit as st
import tomllib
from streamlit.errors import StreamlitSecretNotFoundError


REQUIRED_ATTENDEE_COLUMNS = [
    "Attended",
    "User Name (Original Name)",
    "First Name",
    "Last Name",
    "Email",
    "Phone",
    "Registration Time",
    "Approval Status",
    "Join Time",
    "Leave Time",
    "Time in Session (minutes)",
    "Is Guest",
    "Country/Region Name",
    "Source Name",
]

CLEAN_SCHEMA = [
    "Webinar Date",
    "Bootcamp Day",
    "Category",
    "Webinar ID",
    "Attended",
    "User Name (Original Name)",
    "First Name",
    "Last Name",
    "Email",
    "Phone",
    "Registration Time",
    "Approval Status",
    "Registration Source",
    "Attendance Type",
    "Join Time",
    "Leave Time",
    "Time in Session (minutes)",
    "Is Guest",
    "Country/Region Name",
    "UserID",
    "Webinar name",
    "Webinar conductor",
]

REGISTRATION_SCHEMA = [
    "User Name (Original Name)",
    "First Name",
    "Last Name",
    "Email",
    "Registration Time",
    "Approval Status",
    "Phone",
    "Registration Source",
    "Attendance Type",
    "UserID",
    "Webinar ID",
    "Webinar name",
    "Webinar Date",
]

SECTION_NAMES = {"Topic", "Host Details", "Panelist Details", "Attendee Details", "Registrant Details"}

DEFAULT_CATEGORY_TOKEN_MAP = {
    "acca": "ACCA",
    "cma": "CMA",
    "cfa": "CFA",
    "cpa": "CPA",
}

DEFAULT_CONDUCTOR_MAP = {
    "989 8318 8454": "Sukhpreet Monga",
}

DEFAULT_APPROVED_CONDUCTORS = [
    "Sukhpreet Monga",
    "Satyarth Dwivedi",
    "Khushi Gera",
]

WEBENGAGE_HOST = "https://api.webengage.com"
IST_TZ = timezone(timedelta(hours=5, minutes=30))

PLUTUS_ATTENDEE_EVENT_NAME = "Plutus_Webinar_Attended"
PLUTUS_REGISTRATION_EVENT_NAME = "Plutus_Webinar_Registered"
PLUTUS_BOOTCAMP_ATTENDED_EVENT_NAME = "Plutus_Bootcamp_Attended"
PLUTUS_BOOTCAMP_REGISTERED_EVENT_NAME = "Plutus_Bootcamp_Registered"


PROFILE_REGISTRY = {
    "Plutus": {
        "Webinar Attended": {
            "label": "Plutus Webinar Attended",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": PLUTUS_ATTENDEE_EVENT_NAME,
                "extra_event_attributes": {"Product": "Plutus"},
            },
            "category_mode": "auto",
            "default_category": None,
            "default_category_map": DEFAULT_CATEGORY_TOKEN_MAP,
            "default_conductor_map": DEFAULT_CONDUCTOR_MAP,
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "plutus_webinar_attended.csv",
            "button_label": "Process attendee file",
        },
        "Webinar Registered": {
            "label": "Plutus Webinar Registered",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": PLUTUS_REGISTRATION_EVENT_NAME,
                "extra_event_attributes": {"Product": "Plutus"},
            },
            "category_mode": "auto",
            "default_category": None,
            "default_category_map": DEFAULT_CATEGORY_TOKEN_MAP,
            "default_conductor_map": DEFAULT_CONDUCTOR_MAP,
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "plutus_webinar_registered.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Bootcamp": {
            "label": "Plutus Bootcamp",
            "workflow_type": "bootcamp_dual",
            "event": {
                "attended_event_name": PLUTUS_BOOTCAMP_ATTENDED_EVENT_NAME,
                "registration_event_name": PLUTUS_BOOTCAMP_REGISTERED_EVENT_NAME,
                "extra_event_attributes": {"Product": "Plutus", "Program": "Bootcamp"},
            },
            "category_mode": "fixed",
            "default_category": "Bootcamp",
            "category_choices": ["Bootcamp", "Plutus Bootcamp"],
            "default_category_map": {},
            "default_conductor_map": DEFAULT_CONDUCTOR_MAP,
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "plutus_bootcamp.csv",
            "button_label": "Process bootcamp file",
            "upload_label": "Raw Zoom bootcamp attendee CSV",
        },
    },
    "TLS": {
        "Webinar Attended – CD": {
            "label": "TLS Webinar Attended CD",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Webinar Attended CD",
                "extra_event_attributes": {"Product": "TLS", "Track": "Contract Drafting"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Contract Drafting"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_attended_cd.csv",
        },
        "Webinar Attended – IP": {
            "label": "TLS Webinar Attended IP",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Webinar Attended IP",
                "extra_event_attributes": {"Product": "TLS", "Track": "Intellectual Property"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Intellectual Property"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_attended_ip.csv",
        },
        "Webinar Attended – MA": {
            "label": "TLS Webinar Attended MA",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Webinar Attended MA",
                "extra_event_attributes": {"Product": "TLS", "Track": "Mergers and Acquisitions"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Mergers and Acquisitions"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_attended_ma.csv",
        },
        "Webinar Attended – TF": {
            "label": "TLS Webinar Attended TF",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Webinar Attended TF",
                "extra_event_attributes": {"Product": "TLS", "Track": "Trademark Filing"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Trademark Filing"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_attended_tf.csv",
        },
        "Webinar Attended – ADR": {
            "label": "TLS Webinar Attended ADR",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Webinar Attended ADR",
                "extra_event_attributes": {"Product": "TLS", "Track": "Alternate Dispute Resolution"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Alternate Dispute Resolution"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_attended_adr.csv",
        },
        "Webinar Attended – Misc": {
            "label": "TLS Misc Webinar",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Misc Webinar Attended",
                "extra_event_attributes": {"Product": "TLS", "Track": "Miscellaneous"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Miscellaneous"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_misc_webinar.csv",
        },
        "Bootcamp – Misc": {
            "label": "TLS Misc Bootcamp",
            "workflow_type": "webinar_attended",
            "event": {
                "attended_event_name": "TLS Misc Bootcamp Attended",
                "extra_event_attributes": {"Product": "TLS", "Track": "Bootcamp"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Bootcamp"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_misc_bootcamp.csv",
        },
        "Webinar Registered – CD": {
            "label": "TLS Webinar Registered CD",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Webinar Registered CD",
                "extra_event_attributes": {"Product": "TLS", "Track": "Contract Drafting"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Contract Drafting"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_cd.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Webinar Registered – IP": {
            "label": "TLS Webinar Registered IP",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Webinar Registered IP",
                "extra_event_attributes": {"Product": "TLS", "Track": "Intellectual Property"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Intellectual Property"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_ip.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Webinar Registered – MA": {
            "label": "TLS Webinar Registered MA",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Webinar Registered MA",
                "extra_event_attributes": {"Product": "TLS", "Track": "Mergers and Acquisitions"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Mergers and Acquisitions"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_ma.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Webinar Registered – TF": {
            "label": "TLS Webinar Registered TF",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Webinar Registered TF",
                "extra_event_attributes": {"Product": "TLS", "Track": "Trademark Filing"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Trademark Filing"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_tf.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Webinar Registered – ADR": {
            "label": "TLS Webinar Registered ADR",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Webinar Registered ADR",
                "extra_event_attributes": {"Product": "TLS", "Track": "Alternate Dispute Resolution"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Alternate Dispute Resolution"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_adr.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
        "Webinar Registered – Misc": {
            "label": "TLS Misc Webinar Registered",
            "workflow_type": "registration",
            "event": {
                "registration_event_name": "TLS Misc Webinar Registered",
                "extra_event_attributes": {"Product": "TLS", "Track": "Miscellaneous"},
            },
            "category_mode": "fixed",
            "default_category": "TLS",
            "category_choices": ["TLS", "Miscellaneous"],
            "default_category_map": {},
            "default_conductor_map": {},
            "approved_conductors": DEFAULT_APPROVED_CONDUCTORS,
            "download_name": "tls_webinar_registered_misc.csv",
            "button_label": "Process registrant file",
            "upload_label": "Raw Zoom registrant CSV",
        },
    },
}


def load_local_secrets() -> Dict[str, str]:
    local_path = Path(__file__).resolve().parent / ".streamlit" / "secrets.toml"
    if local_path.exists():
        try:
            with local_path.open("rb") as fh:
                data = tomllib.load(fh)
            cfg = data.get("webengage", {})
            return {"api_key": cfg.get("api_key", ""), "license_code": cfg.get("license_code", "")}
        except (OSError, tomllib.TOMLDecodeError):
            return {"api_key": "", "license_code": ""}
    return {"api_key": "", "license_code": ""}

PLUTUS_ATTENDEE_LABEL = "Plutus Webinar Attendees"
PLUTUS_REGISTRANT_LABEL = "Plutus Webinar Registrations"
PLUTUS_BOOTCAMP_LABEL = "Plutus Bootcamp"

BOOLEAN_TRUE = {"yes", "true", "1", "y"}
BOOLEAN_FALSE = {"no", "false", "0", "n"}


def get_product_options() -> List[str]:
    return list(PROFILE_REGISTRY.keys())


def get_use_case_options(product: str) -> List[str]:
    return list(PROFILE_REGISTRY.get(product, {}).keys())


def get_profile(product: str, use_case: str) -> Dict[str, object]:
    return PROFILE_REGISTRY[product][use_case]

REGISTRATION_REQUIRED_COLUMNS = [
    "First Name",
    "Last Name",
    "Email",
    "Registration Time",
    "Approval Status",
    "Phone",
    "Source Name",
    "Attendance Type",
]


def clean_dict(payload: Dict[str, object]) -> Dict[str, object]:
    return {k: v for k, v in payload.items() if v not in (None, "")}


def to_event_time(date_str: str) -> str:
    """DEPRECATED: Not used anymore - WebEngage bulk-events API doesn't accept eventTime parameter.
    
    Previously used to convert date string to ISO 8601 format. 
    Kept for reference only. Dates are now stored in eventData.WebinarDate field.
    """
    if not date_str or not date_str.strip():
        # Return current time using Python's isoformat() which matches JS toISOString()
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Try parsing with different formats
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(date_str.strip(), fmt)
            
            # For date-only formats (first 3), set time to noon IST to avoid date boundary issues
            if fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                # Set to noon IST (12:00 PM) instead of midnight to avoid date changes
                dt = dt.replace(hour=12, minute=0, second=0, microsecond=0)
            
            # Convert to UTC assuming input is in IST
            if dt.tzinfo is None:
                # Assume the date is in IST, convert to UTC
                dt_ist = dt.replace(tzinfo=IST_TZ)
                dt_utc = dt_ist.astimezone(timezone.utc)
            else:
                dt_utc = dt.astimezone(timezone.utc)
            
            # Use Python's isoformat() and replace timezone with Z
            return dt_utc.isoformat().replace("+00:00", "Z")
        except ValueError:
            continue
    
    # If all parsing attempts fail, return current time in UTC
    # Use Python's isoformat() for consistency
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_record(record: Dict[str, object]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in record.items():
        if value is None or (isinstance(value, float) and math.isnan(value)):
            normalized[key] = ""
        else:
            normalized[key] = str(value)
    return normalized


class WebEngageClient:
    def __init__(self, api_key: str, license_code: str, host: str = WEBENGAGE_HOST):
        self.api_key = api_key
        self.license_code = license_code
        self.host = host.rstrip("/")
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # Rate limiting: WebEngage allows 5000 requests per minute
        # We'll use a conservative rate of 80 requests per second (4800/min)
        self.min_request_interval = 0.0125  # 80 requests per second
        self.last_request_time = 0
        self.max_retries = 3
        self.retry_delay = 1  # Initial retry delay in seconds

    def _post(self, path: str, payload: Dict[str, object]) -> Tuple[bool, str, int]:
        url = f"{self.host}/v1/accounts/{self.license_code}/{path.lstrip('/') }"
        
        # Implement rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                self.last_request_time = time.time()
                response = self.session.post(url, headers=self.headers, json=payload, timeout=15)
                
                if 200 <= response.status_code < 300:
                    return True, "OK", response.status_code
                
                # Handle rate limiting specifically
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        wait_time = self.retry_delay * (2 ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        return False, "Rate limit exceeded for the API", 429
                
                # Handle other errors
                try:
                    body = response.json()
                    message = body.get("message") or body.get("response", {}).get("message") or str(body)
                except ValueError:
                    message = response.text
                return False, message, response.status_code
                
            except requests.RequestException as exc:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))
                    continue
                return False, str(exc), 0
        
        return False, "Max retries exceeded", 0

    def upsert_user(self, payload: Dict[str, object]) -> Tuple[bool, str, int]:
        return self._post("users", payload)

    def fire_event(self, payload: Dict[str, object]) -> Tuple[bool, str, int]:
        return self._post("events", payload)

    # Bulk endpoints
    def bulk_upsert_users(self, users: List[Dict[str, object]]) -> Tuple[bool, str, int]:
        return self._post("bulk-users", {"users": users})

    def bulk_fire_events(self, events: List[Dict[str, object]]) -> Tuple[bool, str, int]:
        return self._post("bulk-events", {"events": events})


def read_csv_rows(raw_bytes: bytes) -> List[List[str]]:
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.reader(StringIO(text))
    return [list(row) for row in reader]


def split_sections(rows: List[List[str]]) -> Dict[str, Dict[str, List[List[str]]]]:
    sections: Dict[str, Dict[str, List[List[str]]]] = {}
    idx = 0
    total = len(rows)
    while idx < total:
        raw = rows[idx]
        stripped = [cell.strip() for cell in raw]
        if not any(stripped):
            idx += 1
            continue
        label = None
        header: List[str] = []
        if len(stripped) == 1 and stripped[0] in SECTION_NAMES:
            label = stripped[0]
            idx += 1
            if idx >= total:
                break
            header = [cell.strip() for cell in rows[idx]]
            idx += 1
        elif stripped[0] == "Topic" and "Topic" not in sections:
            label = "Topic"
            header = [cell.strip() for cell in raw]
            idx += 1
        else:
            idx += 1
            continue

        data_rows: List[List[str]] = []
        while idx < total:
            next_raw = rows[idx]
            next_stripped = [cell.strip() for cell in next_raw]
            if not any(next_stripped):
                idx += 1
                continue
            starter = next_stripped[0]
            if (len(next_stripped) == 1 and starter in SECTION_NAMES) or (
                starter == "Topic" and len(next_raw) > 1 and label != "Topic"
            ):
                break
            row = list(next_raw[: len(header)])
            if len(row) < len(header):
                row.extend([""] * (len(header) - len(row)))
            else:
                row = row[: len(header)]
            data_rows.append([cell.strip() for cell in row])
            idx += 1
        sections[label] = {"header": header, "rows": data_rows}
    return sections


def validate_attendee_header(header: List[str]) -> None:
    normalized = [col.strip() for col in header]
    if normalized[: len(REQUIRED_ATTENDEE_COLUMNS)] != REQUIRED_ATTENDEE_COLUMNS:
        raise ValueError("Attendee header does not match SOP specification")
    if len(normalized) not in (len(REQUIRED_ATTENDEE_COLUMNS), len(REQUIRED_ATTENDEE_COLUMNS) + 1):
        raise ValueError("Attendee header contains unexpected columns")
    if len(normalized) == len(REQUIRED_ATTENDEE_COLUMNS) + 1 and normalized[-1] != "Source Name":
        raise ValueError("Only 'Source Name' is allowed as optional attendee column")


def validate_registration_header(header: List[str]) -> None:
    normalized = [col.strip() for col in header]
    if normalized != REGISTRATION_REQUIRED_COLUMNS:
        raise ValueError("Registration header does not match expected schema")


def normalize_space(text: str) -> str:
    text = text.strip()
    return re.sub(r"\s+", " ", text)


def proper_case(text: str) -> str:
    if not text:
        return text
    return " ".join(word.capitalize() for word in normalize_space(text).split(" "))


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if len(digits) >= 10:
        digits = digits[-10:]
    if len(digits) != 10:
        return ""
    return digits


def build_user_id(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return ""
    tail = digits[-10:]
    tail = tail.zfill(10)
    return f"91{tail}"


def canonicalize_name(name: str, approved_lookup: Dict[str, str]) -> str:
    cleaned = re.sub(r"\(.*?\)", "", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    key = cleaned.lower()
    if key in approved_lookup:
        return approved_lookup[key]
    return proper_case(cleaned)


def normalize_bool(value: str) -> Tuple[bool, str]:
    token = (value or "").strip().lower()
    if token in BOOLEAN_TRUE:
        return True, "Yes"
    if token in BOOLEAN_FALSE:
        return False, "No"
    return False, ""


def parse_datetime(value: str) -> Tuple[datetime, str]:
    if not value or not value.strip():
        return None, ""
    dt = pd.to_datetime(value, dayfirst=True, errors="coerce")
    if pd.isna(dt):
        return None, ""
    dt_native = dt.to_pydatetime()
    return dt_native, dt_native.strftime("%d/%m/%Y %I:%M:%S %p")


def first_non_blank(values: Iterable[str]) -> str:
    for item in values:
        if isinstance(item, str) and item.strip():
            return item
    return ""


def normalize_attendees(df: pd.DataFrame, stats: Dict[str, float]) -> pd.DataFrame:
    work = df.fillna("").copy()
    for column in [
        "Attended",
        "User Name (Original Name)",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Registration Time",
        "Approval Status",
        "Join Time",
        "Leave Time",
        "Time in Session (minutes)",
        "Is Guest",
        "Country/Region Name",
        "Source Name",
        "Attendance Type",
    ]:
        if column in work.columns:
            work[column] = work[column].astype(str).map(normalize_space)

    for column in ["Join Time", "Leave Time", "Registration Time"]:
        work[column] = work[column].replace("--", "")

    work["User Name (Original Name)"] = work["User Name (Original Name)"].map(proper_case)
    work["First Name"] = work["First Name"].map(proper_case)
    work["Last Name"] = work["Last Name"].map(proper_case)
    work["Country/Region Name"] = work["Country/Region Name"].map(proper_case)
    work["Email"] = work["Email"].str.lower()

    work["Phone"] = work["Phone"].map(normalize_phone)
    if "Source Name" in work.columns:
        work["Registration Source"] = work["Source Name"].map(normalize_space)
    else:
        work["Registration Source"] = ""

    email_to_phone: Dict[str, str] = {}
    for email, phone in zip(work["Email"], work["Phone"]):
        if email and phone and email not in email_to_phone:
            email_to_phone[email] = phone
    work.loc[
        work["Phone"].eq("") & work["Email"].isin(email_to_phone.keys()),
        "Phone",
    ] = work.loc[
        work["Phone"].eq("") & work["Email"].isin(email_to_phone.keys()),
        "Email",
    ].map(email_to_phone)

    valid_mask = work["Phone"].str.len() == 10
    invalid_count = int((~valid_mask).sum())
    if invalid_count:
        stats["invalid_phone_rows"] = stats.get("invalid_phone_rows", 0) + invalid_count
    work = work[valid_mask].copy()

    attended_bool, attended_str = zip(*(normalize_bool(v) for v in work["Attended"]))
    work["Attended_bool"] = attended_bool
    work["Attended"] = attended_str

    guest_bool, guest_str = zip(*(normalize_bool(v) for v in work["Is Guest"]))
    work["Is Guest_bool"] = guest_bool
    work["Is Guest"] = guest_str

    join_inputs = work["Join Time"].tolist()
    leave_inputs = work["Leave Time"].tolist()
    reg_inputs = work["Registration Time"].tolist()

    join_dt, join_fmt = zip(*(parse_datetime(v) for v in join_inputs))
    work["_join_dt"] = join_dt
    work["Join Time"] = join_fmt
    leave_dt, leave_fmt = zip(*(parse_datetime(v) for v in leave_inputs))
    work["_leave_dt"] = leave_dt
    work["Leave Time"] = leave_fmt
    reg_dt, reg_fmt = zip(*(parse_datetime(v) for v in reg_inputs))
    work["Registration Time"] = reg_fmt

    work["_tis_minutes"] = pd.to_numeric(
        work["Time in Session (minutes)"].replace({"": "0", "--": "0"}),
        errors="coerce",
    ).fillna(0.0)
    work["Time in Session (minutes)"] = work["_tis_minutes"].map(lambda x: str(int(math.floor(x))))

    stats["join_parsed"] = sum(dt is not None for dt in join_dt)
    stats["join_total"] = sum(bool(v) for v in join_inputs)
    stats["leave_parsed"] = sum(dt is not None for dt in leave_dt)
    stats["leave_total"] = sum(bool(v) for v in leave_inputs)
    stats["registration_parsed"] = sum(dt is not None for dt in reg_dt)
    stats["registration_total"] = sum(bool(v) for v in reg_inputs)

    return work


def aggregate_group(group: pd.DataFrame) -> Dict[str, str]:
    group_sorted = group.sort_values(by="_join_dt", ascending=True)
    result: Dict[str, str] = {}

    result["Time in Session (minutes)"] = str(int(math.floor(group["_tis_minutes"].sum())))

    join_candidates = group["_join_dt"].dropna()
    leave_candidates = group["_leave_dt"].dropna()
    result["Join Time"] = (
        join_candidates.min().strftime("%d/%m/%Y %I:%M:%S %p") if not join_candidates.empty else ""
    )
    result["Leave Time"] = (
        leave_candidates.max().strftime("%d/%m/%Y %I:%M:%S %p") if not leave_candidates.empty else ""
    )

    result["Attended"] = "Yes" if group["Attended_bool"].any() else "No"

    if group["Is Guest_bool"].any():
        result["Is Guest"] = "Yes"
    elif (group["Is Guest"].eq("No")).all():
        result["Is Guest"] = "No"
    else:
        result["Is Guest"] = ""

    for column in [
        "User Name (Original Name)",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Registration Time",
        "Approval Status",
        "Country/Region Name",
    ]:
        result[column] = first_non_blank(group_sorted[column])

    for column in [
        "Registration Source",
        "Attendance Type",
    ]:
        if column in group_sorted.columns:
            result[column] = first_non_blank(group_sorted[column])
        else:
            result[column] = ""
    result["UserID"] = build_user_id(result["Phone"])
    return result


def deduplicate_attendees(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["__row_id"] = range(len(work))

    grouped_rows: List[Dict[str, str]] = []

    phone_groups = work.groupby("Phone", sort=False)
    for phone_value, phone_group in phone_groups:
        if phone_value:
            grouped_rows.append(aggregate_group(phone_group))
            continue

        email_groups = phone_group.groupby("Email", sort=False)
        for email_value, email_group in email_groups:
            if email_value:
                grouped_rows.append(aggregate_group(email_group))
                continue
            for _, single_row_group in email_group.groupby("__row_id", sort=False):
                grouped_rows.append(aggregate_group(single_row_group))

    return pd.DataFrame(grouped_rows)


def normalize_registrants(df: pd.DataFrame, stats: Dict[str, float]) -> pd.DataFrame:
    work = df.fillna("").copy()
    for column in REGISTRATION_REQUIRED_COLUMNS:
        work[column] = work[column].astype(str).map(normalize_space)

    work["First Name"] = work["First Name"].map(proper_case)
    work["Last Name"] = work["Last Name"].map(proper_case)
    work["Email"] = work["Email"].str.lower()

    work["Phone"] = work["Phone"].map(normalize_phone)
    work["Registration Source"] = work["Source Name"].map(normalize_space)
    work["Attendance Type"] = work["Attendance Type"].map(lambda v: proper_case(v).title() if v else "")

    valid_mask = work["Phone"].str.len() == 10
    invalid_count = int((~valid_mask).sum())
    if invalid_count:
        stats["invalid_phone_rows"] = stats.get("invalid_phone_rows", 0) + invalid_count
    work = work[valid_mask].copy()

    full_names = []
    for first, last in zip(work["First Name"], work["Last Name"]):
        components = [part for part in [first, last] if part]
        full_names.append(" ".join(components))
    work["User Name (Original Name)"] = full_names

    reg_inputs = work["Registration Time"].tolist()
    reg_dt, reg_fmt = zip(*(parse_datetime(v) for v in reg_inputs))
    work["_reg_dt"] = reg_dt
    work["Registration Time"] = reg_fmt

    stats["registration_parsed"] = sum(dt is not None for dt in reg_dt)
    stats["registration_total"] = sum(bool(v) for v in reg_inputs)

    return work


def aggregate_registration_group(group: pd.DataFrame) -> Dict[str, str]:
    group_sorted = group.sort_values(by="_reg_dt", ascending=True)
    result: Dict[str, str] = {}

    reg_dates = group["_reg_dt"].dropna()
    if not reg_dates.empty:
        earliest = reg_dates.min()
        result["Registration Time"] = earliest.strftime("%d/%m/%Y %I:%M:%S %p")
    else:
        result["Registration Time"] = first_non_blank(group_sorted["Registration Time"])

    for column in [
        "User Name (Original Name)",
        "First Name",
        "Last Name",
        "Email",
        "Phone",
        "Approval Status",
        "Registration Source",
        "Attendance Type",
    ]:
        result[column] = first_non_blank(group_sorted[column])

    result["UserID"] = build_user_id(result["Phone"])
    return result


def deduplicate_registrants(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["__row_id"] = range(len(work))

    grouped_rows: List[Dict[str, str]] = []

    phone_groups = work.groupby("Phone", sort=False)
    for phone_value, phone_group in phone_groups:
        if phone_value:
            grouped_rows.append(aggregate_registration_group(phone_group))
            continue

        email_groups = phone_group.groupby("Email", sort=False)
        for email_value, email_group in email_groups:
            if email_value:
                grouped_rows.append(aggregate_registration_group(email_group))
                continue
            for _, single_row_group in email_group.groupby("__row_id", sort=False):
                grouped_rows.append(aggregate_registration_group(single_row_group))

    return pd.DataFrame(grouped_rows)


def build_user_payload(record: Dict[str, str]) -> Dict[str, object]:
    phone = record.get("Phone", "")
    mobile = f"91{phone}" if phone else ""
    attributes = clean_dict({
        "originalName": record.get("User Name (Original Name)", ""),
    })
    payload = {
        "userId": record.get("UserID"),
        "email": record.get("Email") or None,
        "firstName": record.get("First Name") or record.get("User Name (Original Name)") or None,
        "phone": mobile or None,
        "whatsappOptIn": True,
        "emailOptIn": True,
    }
    if attributes:
        payload["attributes"] = attributes
    return clean_dict(payload)


def build_attendee_event_payload(
    record: Dict[str, str],
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
) -> Dict[str, object]:
    event_data = clean_dict({
        "WebinarName": record.get("Webinar name", ""),
        "Conductor": record.get("Webinar conductor", ""),
        "Product": record.get("Category", ""),
        "WebinarDate": record.get("Webinar Date", ""),  # Store date in eventData instead
        "JoinTime": record.get("Join Time", ""),
        "LeaveTime": record.get("Leave Time", ""),
        "TimeInSessionMinutes": record.get("Time in Session (minutes)", ""),
        "UserNameOriginal": record.get("User Name (Original Name)", ""),
        "UserEmail": record.get("Email", ""),
        "WebinarId": record.get("Webinar ID", ""),
    })
    if extra_attrs:
        event_data.update(extra_attrs)
    return {
        "userId": record.get("UserID"),
        "eventName": event_name,
        # REMOVED eventTime - bulk-events API doesn't accept this parameter
        "eventData": event_data,
    }


def parse_topic(sections: Dict[str, Dict[str, List[List[str]]]]) -> Dict[str, str]:
    if "Topic" not in sections or not sections["Topic"]["rows"]:
        return {}
    header = sections["Topic"]["header"]
    row = sections["Topic"]["rows"][0]
    topic_info = {header[i]: row[i] for i in range(len(header))}
    topic_info["Topic"] = normalize_space(topic_info.get("Topic", ""))
    topic_info["Webinar ID"] = normalize_space(topic_info.get("Webinar ID", ""))
    return topic_info


def get_section_primary_name(section: Dict[str, List[List[str]]]) -> str:
    if not section or not section.get("rows"):
        return ""
    header = section["header"]
    rows = section["rows"]
    if "User Name (Original Name)" not in header:
        if header and "User Name" in header:
            idx = header.index("User Name")
            return proper_case(rows[0][idx]) if rows else ""
        return ""
    idx = header.index("User Name (Original Name)")
    return proper_case(rows[0][idx])


def get_all_panelist_names(section: Dict[str, List[List[str]]]) -> List[str]:
    if not section or not section.get("rows"):
        return []
    header = section["header"]
    rows = section["rows"]
    if "User Name (Original Name)" not in header:
        if "User Name" not in header:
            return []
        idx = header.index("User Name")
    else:
        idx = header.index("User Name (Original Name)")
    names: List[str] = []
    for row in rows:
        raw = row[idx] if idx < len(row) else ""
        cleaned = proper_case(raw)
        if cleaned and cleaned not in names:
            names.append(cleaned)
    return names


def get_all_host_names(section: Dict[str, List[List[str]]]) -> List[str]:
    if not section or not section.get("rows"):
        return []
    header = section["header"]
    rows = section["rows"]
    if "User Name (Original Name)" not in header:
        if "User Name" not in header:
            return []
        idx = header.index("User Name")
    else:
        idx = header.index("User Name (Original Name)")
    names: List[str] = []
    for row in rows:
        raw = row[idx] if idx < len(row) else ""
        cleaned = proper_case(raw)
        if cleaned and cleaned not in names:
            names.append(cleaned)
    return names


def resolve_category(topic: str, token_map: Dict[str, str]) -> str:
    topic_lower = topic.lower()
    for token, category in token_map.items():
        if token.lower() in topic_lower:
            return category
    return ""


def enrich_metadata(
    df: pd.DataFrame,
    sections: Dict[str, Dict[str, List[List[str]]]],
    category_map: Dict[str, str],
    conductor_map: Dict[str, str],
    approved_conductors: List[str],
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    topic_info = parse_topic(sections)
    topic_title = topic_info.get("Topic", "")
    webinar_id = topic_info.get("Webinar ID", "")
    actual_start = topic_info.get("Actual Start Time", "")

    panelist_section = sections.get("Panelist Details", {})
    panelist_name = get_section_primary_name(panelist_section)
    panelist_names = get_all_panelist_names(panelist_section)
    host_section = sections.get("Host Details", {})
    host_name = get_section_primary_name(host_section)
    host_names = get_all_host_names(host_section)

    if actual_start:
        parsed_start = pd.to_datetime(actual_start, dayfirst=True, errors="coerce")
        if pd.isna(parsed_start):
            webinar_date = ""
        else:
            dt = parsed_start.to_pydatetime()
            webinar_date = f"{dt.day}/{dt.month}/{dt.year}"
    else:
        webinar_date = ""

    category = resolve_category(topic_title, category_map)

    if webinar_id in conductor_map:
        conductor = conductor_map[webinar_id]
    elif panelist_names:
        conductor = ", ".join(panelist_names)
    elif host_names:
        conductor = ", ".join(host_names)
    else:
        conductor = panelist_name or host_name
    conductor = conductor or ""
    conductor = proper_case(conductor)

    approved_lookup = {name.lower(): name for name in approved_conductors}
    approved_set = set(approved_lookup.keys())
    conductor_warning = ""
    if conductor:
        raw_parts = [part.strip() for part in conductor.split(",") if part.strip()]
        normalized_parts = []
        for part in raw_parts:
            canonical = canonicalize_name(part, approved_lookup)
            normalized_parts.append(canonical)
        primary = [part for part in normalized_parts if part.lower() in approved_set]
        extras = [part for part in normalized_parts if part.lower() not in approved_set]
        conductor = ", ".join(primary + extras) if primary or extras else conductor
        unapproved = extras
        if unapproved:
            conductor_warning = f"Conductor(s) not in approved list: {', '.join(unapproved)}"

    df["Webinar Date"] = webinar_date
    df["Category"] = category
    df["Webinar ID"] = webinar_id
    df["Webinar name"] = topic_title
    df["Webinar conductor"] = conductor

    metadata = {
        "Webinar ID": webinar_id,
        "Topic": topic_title,
        "Actual Start Time": actual_start,
        "Derived Category": category,
        "Derived Conductor": conductor,
        "Conductor Warning": conductor_warning,
    }
    return df, metadata


def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    for column in CLEAN_SCHEMA:
        if column not in df.columns:
            df[column] = ""
    df["Phone"] = df["Phone"].map(lambda v: f"91{v}" if v else "")
    df["UserID"] = df["UserID"].map(build_user_id)
    return df[CLEAN_SCHEMA]


def enrich_registration_metadata(
    df: pd.DataFrame,
    sections: Dict[str, Dict[str, List[List[str]]]],
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    topic_info = parse_topic(sections)
    topic_title = topic_info.get("Topic", "")
    webinar_id = topic_info.get("ID", "") or topic_info.get("Webinar ID", "")
    scheduled = (
        topic_info.get("Actual Start Time")
        or topic_info.get("Scheduled Time")
        or topic_info.get("Scheduled Start Time")
        or ""
    )

    if scheduled:
        scheduled_dt = pd.to_datetime(scheduled, dayfirst=True, errors="coerce")
        if pd.isna(scheduled_dt):
            webinar_date = ""
        else:
            dt = scheduled_dt.to_pydatetime()
            webinar_date = f"{dt.day}/{dt.month}/{dt.year}"
    else:
        webinar_date = ""

    df["Webinar name"] = topic_title
    df["Webinar Date"] = webinar_date
    df["Webinar ID"] = webinar_id

    metadata = {
        "Webinar ID": webinar_id,
        "Topic": topic_title,
        "Scheduled Time": scheduled,
    }
    return df, metadata


def ensure_registration_schema(df: pd.DataFrame) -> pd.DataFrame:
    for column in REGISTRATION_SCHEMA:
        if column not in df.columns:
            df[column] = ""
    df["Phone"] = df["Phone"].map(lambda v: f"91{v}" if v else "")
    df["UserID"] = df["UserID"].map(build_user_id)
    return df[REGISTRATION_SCHEMA]
def main() -> None:
    st.set_page_config(page_title="Webinar Attendee Cleaner", layout="wide")
    st.title("Zoom Webinar → WebEngage Cleaner")
    st.caption("Upload raw Zoom attendee report CSVs and export WebEngage-ready data.")

    products = get_product_options()
    if not products:
        st.error("No products configured.")
        return

    selected_product = st.selectbox("Product", options=products)
    use_case_options = get_use_case_options(selected_product)
    if not use_case_options:
        st.error("No use cases configured for the selected product.")
        return

    use_case_labels = {
        key: PROFILE_REGISTRY[selected_product][key]["label"] for key in use_case_options
    }
    selected_use_case = st.selectbox(
        "Use case",
        options=use_case_options,
        format_func=lambda key: use_case_labels[key],
    )

    profile = get_profile(selected_product, selected_use_case)
    profile_label = profile["label"]
    workflow_type = profile["workflow_type"]
    event_config = profile.get("event", {})

    category_mode = profile.get("category_mode", "auto")
    profile_default_category_map = profile.get(
        "default_category_map",
        DEFAULT_CATEGORY_TOKEN_MAP if category_mode == "auto" else {},
    )
    default_category = profile.get("default_category")
    default_conductor_map = profile.get("default_conductor_map", {})
    default_approved_conductors = profile.get("approved_conductors", DEFAULT_APPROVED_CONDUCTORS)

    st.subheader(f"Workflow: {profile_label}")

    category_value: str | None = None

    with st.sidebar:
        st.header("Configuration")
        if category_mode == "auto":
            category_json = st.text_area(
                "Category token map (JSON)",
                value=json.dumps(profile_default_category_map, indent=2),
                height=200,
            )
            category_override_enabled = st.checkbox("Override category after cleaning", value=False)
            if category_override_enabled:
                manual_category = st.text_input(
                    "Custom category",
                    value=default_category or "",
                )
                category_value = manual_category.strip() or None
        else:
            st.caption("Category token map is not required for this workflow.")
            choices = [choice for choice in profile.get("category_choices", []) if choice]
            if not choices:
                choices = [default_category or "TLS"]
            default_choice = default_category or choices[0]
            try:
                default_index = choices.index(default_choice)
            except ValueError:
                default_index = 0
            selected_category_value = st.selectbox("Category", choices, index=default_index)
            custom_category_enabled = st.checkbox("Use custom category", value=False)
            if custom_category_enabled:
                manual_category = st.text_input("Custom category", value=selected_category_value)
                category_value = manual_category.strip() or selected_category_value
            else:
                category_value = selected_category_value
            category_json = json.dumps(profile_default_category_map, indent=2)

        conductor_json = st.text_area(
            "Conductor map (Webinar ID → Name)",
            value=json.dumps(default_conductor_map, indent=2),
            height=160,
        )
        approved_conductors_input = st.text_area(
            "Approved conductor names (comma separated)",
            value=", ".join(default_approved_conductors),
            height=80,
        )

        if workflow_type in ("webinar_attended", "bootcamp_dual"):
            threshold = st.slider("Datetime success threshold", 0.8, 1.0, 0.99, 0.01)
        else:
            threshold = None

        st.markdown("---")
        st.subheader("WebEngage API")
        try:
            secrets_cfg = st.secrets["webengage"]
        except (StreamlitSecretNotFoundError, KeyError):
            secrets_cfg = {}
        if not secrets_cfg:
            secrets_cfg = load_local_secrets()
        secret_api_key = secrets_cfg.get("api_key", "")
        secret_license = secrets_cfg.get("license_code", "")
        api_key_input = st.text_input(
            "REST API Key",
            value="",
            type="password",
            help="Leave blank to use st.secrets['webengage']['api_key'] if configured.",
        )
        license_code_input = st.text_input(
            "License Code",
            value="",
            type="password",
            help="Leave blank to use st.secrets['webengage']['license_code'] if configured.",
        )

        fire_action = st.radio(
            "After processing",
            ("Clean only", "Clean + fire WebEngage events"),
            index=0,
        )

        use_bulk = st.checkbox("Use bulk API (recommended)", value=True)
        bulk_batch_size = st.slider("Bulk batch size", min_value=10, max_value=50, value=25, step=5)
        final_retry = st.checkbox("Final cool-down retry for 429s", value=True)

    upload_label = profile.get("upload_label") or (
        "Raw Zoom registrant CSV" if workflow_type == "registration" else "Raw Zoom attendee CSV"
    )
    uploaded = st.file_uploader(upload_label, type=["csv"])

    if uploaded is None:
        st.info("Upload a raw Zoom CSV file to begin.")
        return

    try:
        category_map = parse_json_config(category_json, profile_default_category_map)
        conductor_map = parse_json_config(conductor_json, default_conductor_map)
    except ValueError as err:
        st.error(str(err))
        return

    approved_names = [name.strip() for name in approved_conductors_input.split(",") if name.strip()]
    api_key = api_key_input or secret_api_key
    license_code = license_code_input or secret_license
    should_fire = fire_action == "Clean + fire WebEngage events"

    button_label = profile.get("button_label", f"Process {profile_label}")

    if st.button(button_label, type="primary"):
        with st.spinner("Cleaning in progress..."):
            try:
                bootcamp_day_short = ""
                bootcamp_warning = ""
                if workflow_type in ("webinar_attended", "bootcamp_dual"):
                    final_df, metadata, logs, stats = process_uploaded_file(
                        uploaded.getvalue(),
                        category_map,
                        conductor_map,
                        threshold if threshold is not None else 0.99,
                        approved_names,
                    )
                elif workflow_type == "registration":
                    final_df, metadata, logs, stats = process_registration_file(
                        uploaded.getvalue(),
                        category_map,
                        conductor_map,
                    )
                else:
                    raise ValueError(f"Unsupported workflow type: {workflow_type}")

                if workflow_type == "bootcamp_dual":
                    final_df, metadata, bootcamp_day_short, _, bootcamp_warning = annotate_bootcamp_day(final_df, metadata)
                    final_df = final_df.reindex(columns=CLEAN_SCHEMA, fill_value="")

            except Exception as err:  # pragma: no cover - user interaction
                st.error(str(err))
                return

        if category_value:
            if "Category" in final_df.columns:
                final_df["Category"] = category_value
            metadata["Derived Category"] = category_value

        st.success(f"Processed {len(final_df)} records for {profile_label}")

        event_summary = None
        if should_fire:
            if not api_key or not license_code:
                st.error("WebEngage API key and license code are required to fire events.")
            elif not event_config:
                st.info("No WebEngage event configured for this workflow.")
            else:
                # Calculate expected processing time
                # For webinar_attended, only count attended records
                if workflow_type == "webinar_attended":
                    records_to_process = len(final_df[final_df["Attended"] == "Yes"])
                else:
                    # For bootcamp_dual and registration, count all records
                    records_to_process = len(final_df)
                    
                if use_bulk:
                    per_batch_calls = 3 if workflow_type == "bootcamp_dual" else 2
                    batches = max(1, math.ceil(records_to_process / bulk_batch_size))
                    total_api_calls = batches * per_batch_calls
                    est_seconds = total_api_calls * 0.5  # ~0.5s/request incl. network
                    st.info(f"📊 Bulk mode: {batches} batch(es) × {per_batch_calls} request(s) each ≈ {total_api_calls} calls (~{est_seconds:.0f}s).")
                else:
                    events_per_record = 3 if workflow_type == "bootcamp_dual" else 2
                    total_api_calls = records_to_process * events_per_record
                    expected_time_seconds = total_api_calls / 80
                    expected_time_minutes = expected_time_seconds / 60
                    if expected_time_minutes > 1:
                        st.info(f"📊 Processing {records_to_process} records will take approximately {expected_time_minutes:.1f} minutes due to API rate limiting (5000 requests/minute limit).")
                    else:
                        st.info(f"📊 Processing {records_to_process} records will take approximately {expected_time_seconds:.0f} seconds.")
                
                client = WebEngageClient(api_key=api_key, license_code=license_code)
                extra = event_config.get("extra_event_attributes")
                with st.spinner("Sending data to WebEngage..."):
                    if workflow_type == "webinar_attended":
                        # Filter for only attended records (Attended = "Yes")
                        attended_df = final_df[final_df["Attended"] == "Yes"].copy()
                        
                        # Show info about filtering
                        st.info(f"📋 Filtered {len(attended_df)} attended records from {len(final_df)} total records to send to WebEngage")
                        
                        if len(attended_df) == 0:
                            st.warning("No attended records (Attended = 'Yes') found to send to WebEngage")
                            event_summary = {
                                "total": 0,
                                "success": 0,
                                "event_failures": [],
                                "user_failures": [],
                            }
                        else:
                            event_summary = fire_attendee_events(
                                attended_df,
                                client,
                                event_config.get("attended_event_name", ""),
                                extra,
                                use_bulk=use_bulk,
                                batch_size=bulk_batch_size,
                                final_retry=final_retry,
                            )
                    elif workflow_type == "registration":
                        event_summary = fire_registration_events(
                            final_df,
                            client,
                            event_config.get("registration_event_name", ""),
                            extra,
                            use_bulk=use_bulk,
                            batch_size=bulk_batch_size,
                            final_retry=final_retry,
                        )
                    elif workflow_type == "bootcamp_dual":
                        # Count actual attendees for accurate messaging
                        attended_count = len(final_df[final_df["Attended"] == "Yes"]) if "Attended" in final_df.columns else len(final_df)
                        st.info(f"📋 Sending {len(final_df)} registration events and {attended_count} attended events to WebEngage (attended events only for Attended='Yes' records)")
                        
                        event_summary = fire_bootcamp_events(
                            final_df,
                            client,
                            bootcamp_day_short,
                            event_config.get("attended_event_name", PLUTUS_BOOTCAMP_ATTENDED_EVENT_NAME),
                            event_config.get("registration_event_name", PLUTUS_BOOTCAMP_REGISTERED_EVENT_NAME),
                            event_config.get("attended_extra_event_attributes", extra),
                            event_config.get("registration_extra_event_attributes", extra),
                            use_bulk=use_bulk,
                            batch_size=bulk_batch_size,
                            final_retry=final_retry,
                        )

        metadata_display = dict(metadata)
        metadata_display["Workflow"] = profile_label
        metadata_display["Product"] = selected_product
        metadata_display["Use Case"] = use_case_labels[selected_use_case]
        if workflow_type == "bootcamp_dual":
            metadata_display["Registration Event"] = event_config.get("registration_event_name", "")
            metadata_display["Attended Event"] = event_config.get("attended_event_name", "")
            metadata_display["Bootcamp Day"] = metadata.get("Bootcamp Day", "")
        elif workflow_type == "webinar_attended":
            metadata_display["Event Name"] = event_config.get("attended_event_name", "")
        elif workflow_type == "registration":
            metadata_display["Event Name"] = event_config.get("registration_event_name", "")

        if not final_df.empty and "Category" in final_df.columns:
            metadata_display["Applied Category"] = final_df["Category"].iloc[0]

        meta_cols = st.columns(len(metadata_display))
        for (label, value), col in zip(metadata_display.items(), meta_cols):
            col.metric(label, value or "—")

        st.subheader("Preview")
        st.dataframe(final_df, use_container_width=True)

        download_name = profile.get("download_name") or f"{profile_label.lower().replace(' ', '_')}.csv"
        csv_buffer = StringIO()
        final_df.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download cleaned CSV",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name=download_name,
            mime="text/csv",
        )

        st.subheader("Diagnostics")
        if workflow_type in ("webinar_attended", "bootcamp_dual"):
            join_ratio = stats.get("join_parsed", 0) / max(stats.get("join_total", 1), 1)
            leave_ratio = stats.get("leave_parsed", 0) / max(stats.get("leave_total", 1), 1)
            st.write(
                f"Join parse success: {stats.get('join_parsed', 0)} / {stats.get('join_total', 0)}"
            )
            st.write(
                f"Leave parse success: {stats.get('leave_parsed', 0)} / {stats.get('leave_total', 0)}"
            )
            st.write(f"Join success ratio: {join_ratio:.2%}")
            st.write(f"Leave success ratio: {leave_ratio:.2%}")
        elif workflow_type == "registration":
            reg_ratio = stats.get("registration_parsed", 0) / max(
                stats.get("registration_total", 1), 1
            )
            st.write(
                f"Registrations parsed: {int(stats.get('registration_parsed', 0))} / {int(stats.get('registration_total', 0))}"
            )
            st.write(
                f"Deduplicated from {int(stats.get('raw_rows', 0))} to {int(stats.get('dedup_rows', 0))} rows"
            )
            st.write(f"Registration time parse ratio: {reg_ratio:.2%}")

        invalid_phones = stats.get("invalid_phone_rows")
        if invalid_phones:
            st.warning(f"Dropped {int(invalid_phones)} rows with invalid phone numbers.")

        conductor_warning = metadata.get("Conductor Warning")
        if conductor_warning:
            st.warning(conductor_warning)
        if workflow_type == "bootcamp_dual" and bootcamp_warning:
            st.warning(bootcamp_warning)

        if event_summary is not None:
            st.subheader("WebEngage Results")
            if workflow_type == "bootcamp_dual":
                st.write(
                    f"{event_config.get('registration_event_name', 'Registration event')}: {event_summary['registration_success']} / {event_summary['total']}"
                )
                # Show attended success out of actual attendees, not total
                total_attended = event_summary.get('total_attended', event_summary['total'])
                st.write(
                    f"{event_config.get('attended_event_name', 'Attended event')}: {event_summary['attended_success']} / {total_attended}"
                )
                if event_summary["user_failures"]:
                    st.warning("Some user upsert requests failed.")
                    # Check for rate limiting issues
                    rate_limit_errors = [f for f in event_summary["user_failures"] if f.get("status") == 429]
                    if rate_limit_errors:
                        st.error(f"⚠️ {len(rate_limit_errors)} user requests hit rate limits despite automatic retries. Try processing in smaller batches.")
                    st.dataframe(pd.DataFrame(event_summary["user_failures"]))
                if event_summary["registration_failures"]:
                    st.error("Some registration events failed.")
                    # Check for date format issues
                    date_format_errors = [f for f in event_summary["registration_failures"] if "date format" in f.get("message", "").lower()]
                    if date_format_errors:
                        st.error(f"⚠️ {len(date_format_errors)} registration events failed due to date format issues. Check that webinar dates are properly formatted.")
                    st.dataframe(pd.DataFrame(event_summary["registration_failures"]))
                if event_summary["attended_failures"]:
                    st.error("Some attendance events failed.")
                    # Check for date format issues
                    date_format_errors = [f for f in event_summary["attended_failures"] if "date format" in f.get("message", "").lower()]
                    if date_format_errors:
                        st.error(f"⚠️ {len(date_format_errors)} attendance events failed due to date format issues. Check that webinar dates are properly formatted.")
                    st.dataframe(pd.DataFrame(event_summary["attended_failures"]))
            else:
                event_name_display = event_config.get("attended_event_name") or event_config.get("registration_event_name") or "Event"
                st.write(
                    f"{event_name_display}: {event_summary['success']} / {event_summary['total']}"
                )
                if event_summary["user_failures"]:
                    st.warning("Some user upsert requests failed.")
                    # Check for rate limiting issues
                    rate_limit_errors = [f for f in event_summary["user_failures"] if f.get("status") == 429]
                    if rate_limit_errors:
                        st.error(f"⚠️ {len(rate_limit_errors)} user requests hit rate limits despite automatic retries. Try processing in smaller batches.")
                    st.dataframe(pd.DataFrame(event_summary["user_failures"]))
                if event_summary.get("event_failures"):
                    st.error("Some event requests failed.")
                    # Check for date format issues
                    date_format_errors = [f for f in event_summary.get("event_failures", []) if "date format" in f.get("message", "").lower()]
                    if date_format_errors:
                        st.error(f"⚠️ {len(date_format_errors)} events failed due to date format issues. Check that webinar dates are properly formatted.")
                    st.dataframe(pd.DataFrame(event_summary["event_failures"]))

        st.subheader("Log")
        for entry in logs:
            st.write(entry)


def process_uploaded_file(
    uploaded_bytes: bytes,
    category_map: Dict[str, str],
    conductor_map: Dict[str, str],
    datetime_threshold: float,
    approved_conductors: List[str],
) -> Tuple[pd.DataFrame, Dict[str, str], List[str], Dict[str, float]]:
    logs: List[str] = []
    rows = read_csv_rows(uploaded_bytes)
    logs.append(f"Loaded {len(rows)} raw rows from CSV")
    sections = split_sections(rows)
    logs.append(f"Detected sections: {', '.join(sorted(sections.keys()))}")

    if "Attendee Details" not in sections:
        raise ValueError("Missing 'Attendee Details' section in input file")

    attendee_section = sections["Attendee Details"]
    validate_attendee_header(attendee_section["header"])
    logs.append("Attendee header validated against SOP")

    attendee_df = pd.DataFrame(attendee_section["rows"], columns=attendee_section["header"])
    stats: Dict[str, float] = {}
    attendee_df = normalize_attendees(attendee_df, stats)
    logs.append(f"Normalized {len(attendee_df)} attendee rows")

    join_ratio = stats.get("join_parsed", 0) / max(stats.get("join_total", 1), 1)
    leave_ratio = stats.get("leave_parsed", 0) / max(stats.get("leave_total", 1), 1)
    if join_ratio < datetime_threshold or leave_ratio < datetime_threshold:
        raise ValueError("Datetime parse success below configured threshold")
    logs.append(
        f"Join parse success: {stats.get('join_parsed', 0)}/{stats.get('join_total', 0)}; "
        f"Leave parse success: {stats.get('leave_parsed', 0)}/{stats.get('leave_total', 0)}"
    )

    aggregated_df = deduplicate_attendees(attendee_df)
    logs.append(f"Deduplicated to {len(aggregated_df)} attendee records")

    aggregated_df.drop(columns=["Source Name"], inplace=True, errors="ignore")

    aggregated_df, metadata = enrich_metadata(
        aggregated_df, sections, category_map, conductor_map, approved_conductors
    )
    logs.append("Applied webinar metadata enrichment")

    final_df = ensure_schema(aggregated_df)

    if not set(final_df.columns) == set(CLEAN_SCHEMA):
        raise ValueError("Final schema mismatch")

    if not set(final_df["Attended"].unique()) <= {"Yes", "No"}:
        raise ValueError("Attended column contains non canonical values")

    if not set(final_df["Is Guest"].dropna().replace({pd.NA: ""})) <= {"", "Yes", "No"}:
        raise ValueError("Is Guest column contains invalid values")

    return final_df, metadata, logs, stats


def process_registration_file(
    uploaded_bytes: bytes,
    category_map: Dict[str, str],
    conductor_map: Dict[str, str],
) -> Tuple[pd.DataFrame, Dict[str, str], List[str], Dict[str, float]]:
    logs: List[str] = []
    rows = read_csv_rows(uploaded_bytes)
    logs.append(f"Loaded {len(rows)} raw rows from CSV")
    sections = split_sections(rows)
    logs.append(f"Detected sections: {', '.join(sorted(sections.keys()))}")

    if "Attendee Details" not in sections:
        raise ValueError("Missing 'Attendee Details' section in input file")

    registrant_section = sections["Attendee Details"]
    validate_registration_header(registrant_section["header"])
    logs.append("Registration header validated")

    registrant_df = pd.DataFrame(registrant_section["rows"], columns=registrant_section["header"])
    stats: Dict[str, float] = {"raw_rows": float(len(registrant_df))}
    registrant_df = normalize_registrants(registrant_df, stats)
    logs.append(f"Normalized {len(registrant_df)} registration rows")

    dedup_df = deduplicate_registrants(registrant_df)
    stats["dedup_rows"] = float(len(dedup_df))
    logs.append(f"Deduplicated to {len(dedup_df)} registration records")

    dedup_df, metadata = enrich_registration_metadata(dedup_df, sections)
    logs.append("Applied webinar metadata enrichment")

    final_df = ensure_registration_schema(dedup_df)

    return final_df, metadata, logs, stats


def annotate_bootcamp_day(
    df: pd.DataFrame,
    metadata: Dict[str, str],
) -> Tuple[pd.DataFrame, Dict[str, str], str, str, str]:
    """
    Annotate bootcamp day by extracting from the topic/webinar name.
    Bootcamps are 2-day events, so this looks for "Day 1" or "Day 2" in the title.
    Returns: (df, metadata, day_short, day_display, warning)
    """
    # Get the topic/webinar name from metadata or dataframe
    topic = metadata.get("Topic", "")
    if not topic and "Webinar name" in df.columns:
        topic = df["Webinar name"].iloc[0] if not df.empty else ""
    
    if not topic:
        return df, metadata, "", "", "Could not determine bootcamp day - no topic/title found"
    
    try:
        # Search for day patterns in the topic
        # Look for patterns like "Day 1", "Day-1", "Day1", "DAY 1", etc.
        import re
        
        # Pattern to match Day 1 or Day 2 (with various formatting)
        day_pattern = re.compile(r'[Dd]ay[\s\-_]*([12])', re.IGNORECASE)
        match = day_pattern.search(topic)
        
        if match:
            day_num = match.group(1)
            if day_num == "1":
                day_short = "Day1"
                day_display = "Day 1"
            elif day_num == "2":
                day_short = "Day2"
                day_display = "Day 2"
            else:
                # Should not happen given our pattern, but just in case
                day_short = "Day1"
                day_display = "Day 1"
        else:
            # If no day pattern found in title, try to infer from date as fallback
            webinar_date = df["Webinar Date"].iloc[0] if not df.empty and "Webinar Date" in df.columns else ""
            if webinar_date:
                dt = pd.to_datetime(webinar_date, dayfirst=True, errors="coerce")
                if not pd.isna(dt):
                    # Weekend bootcamps: Saturday = Day 1, Sunday = Day 2
                    if dt.dayofweek == 5:  # Saturday
                        day_short = "Day1"
                        day_display = "Day 1"
                    elif dt.dayofweek == 6:  # Sunday
                        day_short = "Day2"
                        day_display = "Day 2"
                    else:
                        # Default to Day 1 if we can't determine
                        day_short = "Day1"
                        day_display = "Day 1"
                        return df, metadata, day_short, day_display, f"Warning: Could not find 'Day 1' or 'Day 2' in topic '{topic}'. Defaulting to {day_display} based on date."
                else:
                    return df, metadata, "", "", f"Could not find 'Day 1' or 'Day 2' in topic '{topic}' and webinar date is invalid"
            else:
                return df, metadata, "", "", f"Could not find 'Day 1' or 'Day 2' in topic '{topic}'"
        
        # Add bootcamp day column
        df["Bootcamp Day"] = day_display  # Use display version (with space) for CSV
        metadata["Bootcamp Day"] = day_display
        
        return df, metadata, day_short, day_display, ""
    except Exception as e:
        return df, metadata, "", "", f"Error determining bootcamp day: {str(e)}"


def build_registration_event_payload(
    record: Dict[str, str],
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
) -> Dict[str, object]:
    """Build WebEngage event payload for registration."""
    event_data = clean_dict({
        "WebinarName": record.get("Webinar name", ""),
        "WebinarId": record.get("Webinar ID", ""),
        "Product": record.get("Category", ""),
        "WebinarDate": record.get("Webinar Date", ""),  # Store date in eventData instead
        "RegistrationTime": record.get("Registration Time", ""),
        "ApprovalStatus": record.get("Approval Status", ""),
        "UserNameOriginal": record.get("User Name (Original Name)", ""),
        "UserEmail": record.get("Email", ""),
        "RegistrationSource": record.get("Registration Source", ""),
    })
    if extra_attrs:
        event_data.update(extra_attrs)
    return {
        "userId": record.get("UserID"),
        "eventName": event_name,
        # REMOVED eventTime - bulk-events API doesn't accept this parameter
        "eventData": event_data,
    }


def build_bootcamp_registration_event_payload(
    record: Dict[str, str],
    day_label: str,
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
) -> Dict[str, object]:
    """Build WebEngage event payload for bootcamp registration."""
    event_data = clean_dict({
        "WebinarName": record.get("Webinar name", ""),
        "WebinarId": record.get("Webinar ID", ""),
        "Product": record.get("Category", ""),
        "WebinarDate": record.get("Webinar Date", ""),  # Store date in eventData instead
        "BootcampDay": day_label,
        "RegistrationTime": record.get("Registration Time", ""),
        "ApprovalStatus": record.get("Approval Status", ""),
        "UserNameOriginal": record.get("User Name (Original Name)", ""),
        "UserEmail": record.get("Email", ""),
    })
    if extra_attrs:
        event_data.update(extra_attrs)
    return {
        "userId": record.get("UserID"),
        "eventName": event_name,
        # REMOVED eventTime - bulk-events API doesn't accept this parameter
        "eventData": event_data,
    }


def build_bootcamp_attended_event_payload(
    record: Dict[str, str],
    day_label: str,
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
) -> Dict[str, object]:
    """Build WebEngage event payload for bootcamp attendance."""
    event_data = clean_dict({
        "WebinarName": record.get("Webinar name", ""),
        "Conductor": record.get("Webinar conductor", ""),
        "Product": record.get("Category", ""),
        "WebinarDate": record.get("Webinar Date", ""),  # Store date in eventData instead
        "BootcampDay": day_label,
        "JoinTime": record.get("Join Time", ""),
        "LeaveTime": record.get("Leave Time", ""),
        "TimeInSessionMinutes": record.get("Time in Session (minutes)", ""),
        "UserNameOriginal": record.get("User Name (Original Name)", ""),
        "UserEmail": record.get("Email", ""),
        "WebinarId": record.get("Webinar ID", ""),
    })
    if extra_attrs:
        event_data.update(extra_attrs)
    return {
        "userId": record.get("UserID"),
        "eventName": event_name,
        # REMOVED eventTime - bulk-events API doesn't accept this parameter
        "eventData": event_data,
    }


def fire_attendee_events(
    df: pd.DataFrame,
    client: WebEngageClient,
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
    *,
    use_bulk: bool = False,
    batch_size: int = 25,
    final_retry: bool = True,
) -> Dict[str, object]:
    total = len(df)
    summary = {
        "total": total,
        "success": 0,
        "event_failures": [],
        "user_failures": [],
    }
    if total == 0:
        return summary

    progress = st.progress(0)
    status_text = st.empty()
    records = df.to_dict(orient="records")

    if use_bulk:
        status_text.text(f"Bulk processing {total} attended records (batch={batch_size})...")
        # Prebuild payloads
        users = [build_user_payload(normalize_record(r)) for r in records]
        events = [build_attendee_event_payload(normalize_record(r), event_name, extra_attrs) for r in records]
        i = 0
        dyn_batch = max(5, int(batch_size))
        while i < total:
            end = min(i + dyn_batch, total)
            u_batch = users[i:end]
            e_batch = events[i:end]
            u_ok, u_msg, u_status = client.bulk_upsert_users(u_batch)
            if not u_ok:
                if u_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on users; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                # fallback per-row for this slice
                for j, r in enumerate(records[i:end], start=i+1):
                    ok, msg, stc = client.upsert_user(build_user_payload(normalize_record(r)))
                    if not ok:
                        summary["user_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
            ev_ok, ev_msg, ev_status = client.bulk_fire_events(e_batch)
            if ev_ok:
                summary["success"] += len(e_batch)
            else:
                if ev_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on events; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                # fallback per-row to capture failures
                for j, r in enumerate(records[i:end], start=i+1):
                    payload = build_attendee_event_payload(normalize_record(r), event_name, extra_attrs)
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["success"] += 1
                    else:
                        err = {"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc}
                        if len(summary["event_failures"]) < 3:
                            err["webinar_date"] = r.get("Webinar Date", "")
                            err["event_payload_keys"] = list(payload.keys())
                        summary["event_failures"].append(err)
            i = end
            progress.progress(i / total)
            if i % max(10, dyn_batch) == 0 or i == total:
                status_text.text(f"Processed {i}/{total} records... Success: {summary['success']}, Failures: {len(summary['event_failures'])} (batch={dyn_batch})")
        # Final cool-down retry for 429s
        if final_retry:
            pend = [f for f in summary["event_failures"] if f.get("status") == 429]
            if pend:
                time.sleep(10)
                still: List[Dict[str, object]] = []
                for f in pend:
                    idx = int(f.get("row", 0)) - 1
                    payload = build_attendee_event_payload(normalize_record(records[idx]), event_name, extra_attrs)
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["success"] += 1
                    else:
                        still.append({"row": f["row"], "user_id": f.get("user_id"), "message": msg, "status": stc})
                # replace only 429 subset with remaining
                summary["event_failures"] = [f for f in summary["event_failures"] if f.get("status") != 429] + still
    else:
        # Process records with rate limiting (80 req/sec = 4800/min)
        status_text.text(f"Processing {total} attended records (rate limited to ~40 records/sec)...")
        # Debug
        if len(records) > 0:
            with st.expander("🔍 Debug Information", expanded=False):
                for k in range(min(3, len(records))):
                    smp = normalize_record(records[k])
                    st.text(f"Record {k+1}: Webinar Date='{smp.get('Webinar Date','')}' (stored in eventData.WebinarDate)")
        for idx, raw in enumerate(records, start=1):
            record = normalize_record(raw)
            user_payload = build_user_payload(record)
            user_ok, user_msg, user_status = client.upsert_user(user_payload)
            if not user_ok:
                summary["user_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": user_msg, "status": user_status})
            event_payload = build_attendee_event_payload(record, event_name, extra_attrs)
            event_ok, event_msg, event_status = client.fire_event(event_payload)
            if event_ok:
                summary["success"] += 1
            else:
                error_detail = {"row": idx, "user_id": record.get("UserID"), "message": event_msg, "status": event_status}
                if len(summary["event_failures"]) < 3:
                    error_detail["webinar_date"] = record.get("Webinar Date", "")
                    error_detail["event_payload_keys"] = list(event_payload.keys())
                summary["event_failures"].append(error_detail)
            progress.progress(idx / total)
            if idx % 10 == 0 or idx == total:
                status_text.text(f"Processed {idx}/{total} records... Success: {summary['success']}, Failures: {len(summary['event_failures'])}")
    
    progress.empty()
    status_text.empty()
    return summary


def fire_registration_events(
    df: pd.DataFrame,
    client: WebEngageClient,
    event_name: str,
    extra_attrs: Dict[str, str] | None = None,
    *,
    use_bulk: bool = False,
    batch_size: int = 25,
    final_retry: bool = True,
) -> Dict[str, object]:
    total = len(df)
    summary = {
        "total": total,
        "success": 0,
        "event_failures": [],
        "user_failures": [],
    }
    if total == 0:
        return summary

    progress = st.progress(0)
    status_text = st.empty()
    records = df.to_dict(orient="records")

    if use_bulk:
        status_text.text(f"Bulk processing {total} registration records (batch={batch_size})...")
        users = [build_user_payload(normalize_record(r)) for r in records]
        events = [build_registration_event_payload(normalize_record(r), event_name, extra_attrs) for r in records]
        i = 0
        dyn_batch = max(5, int(batch_size))
        while i < total:
            end = min(i + dyn_batch, total)
            u_batch = users[i:end]
            e_batch = events[i:end]
            u_ok, u_msg, u_status = client.bulk_upsert_users(u_batch)
            if not u_ok:
                if u_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on users; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                for j, r in enumerate(records[i:end], start=i+1):
                    ok, msg, stc = client.upsert_user(build_user_payload(normalize_record(r)))
                    if not ok:
                        summary["user_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
            ev_ok, ev_msg, ev_status = client.bulk_fire_events(e_batch)
            if ev_ok:
                summary["success"] += len(e_batch)
            else:
                if ev_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on events; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                for j, r in enumerate(records[i:end], start=i+1):
                    payload = build_registration_event_payload(normalize_record(r), event_name, extra_attrs)
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["success"] += 1
                    else:
                        summary["event_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
            i = end
            progress.progress(i / total)
            if i % max(10, dyn_batch) == 0 or i == total:
                status_text.text(f"Processed {i}/{total} records... Success: {summary['success']}, Failures: {len(summary['event_failures'])} (batch={dyn_batch})")
        if final_retry:
            pend = [f for f in summary["event_failures"] if f.get("status") == 429]
            if pend:
                time.sleep(10)
                still: List[Dict[str, object]] = []
                for f in pend:
                    idx = int(f.get("row", 0)) - 1
                    payload = build_registration_event_payload(normalize_record(records[idx]), event_name, extra_attrs)
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["success"] += 1
                    else:
                        still.append({"row": f["row"], "user_id": f.get("user_id"), "message": msg, "status": stc})
                summary["event_failures"] = [f for f in summary["event_failures"] if f.get("status") != 429] + still
    else:
        # Non-bulk path
        status_text.text(f"Processing {total} registration records (rate limited to ~40 records/sec)...")
        for idx, raw in enumerate(records, start=1):
            record = normalize_record(raw)
            user_payload = build_user_payload(record)
            user_ok, user_msg, user_status = client.upsert_user(user_payload)
            if not user_ok:
                summary["user_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": user_msg, "status": user_status})
            event_payload = build_registration_event_payload(record, event_name, extra_attrs)
            event_ok, event_msg, event_status = client.fire_event(event_payload)
            if event_ok:
                summary["success"] += 1
            else:
                summary["event_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": event_msg, "status": event_status})
            progress.progress(idx / total)
            if idx % 10 == 0 or idx == total:
                status_text.text(f"Processed {idx}/{total} records... Success: {summary['success']}, Failures: {len(summary['event_failures'])}")
    
    progress.empty()
    status_text.empty()
    return summary


def fire_bootcamp_events(
    df: pd.DataFrame,
    client: WebEngageClient,
    day_label: str,
    attended_event_name: str,
    registration_event_name: str,
    attended_extra: Dict[str, str] | None = None,
    registration_extra: Dict[str, str] | None = None,
    *,
    use_bulk: bool = False,
    batch_size: int = 25,
    final_retry: bool = True,
) -> Dict[str, object]:
    total = len(df)
    # Filter for actual attendees (Attended = "Yes")
    attended_df = df[df.get("Attended", "") == "Yes"] if "Attended" in df.columns else df
    total_attended = len(attended_df)
    
    summary = {
        "total": total,
        "total_attended": total_attended,  # Track actual attendees separately
        "registration_success": 0,
        "attended_success": 0,
        "user_failures": [],
        "registration_failures": [],
        "attended_failures": [],
        "bootcamp_day": day_label,
    }
    if total == 0:
        return summary

    progress = st.progress(0)
    status_text = st.empty()
    records = df.to_dict(orient="records")
    attended_records = attended_df.to_dict(orient="records")

    if use_bulk:
        status_text.text(f"Bulk processing {total} registrations, {total_attended} attended (batch={batch_size})...")
        # Build payloads for ALL users and registrations
        users = [build_user_payload(normalize_record(r)) for r in records]
        regs = [build_bootcamp_registration_event_payload(normalize_record(r), day_label, registration_event_name, registration_extra) for r in records]
        # Build attended payloads ONLY for attended records
        atts = [build_bootcamp_attended_event_payload(normalize_record(r), day_label, attended_event_name, attended_extra) for r in attended_records]
        # Process registrations (all records)
        i = 0
        dyn_batch = max(5, int(batch_size))
        while i < total:
            end = min(i + dyn_batch, total)
            u_batch = users[i:end]
            r_batch = regs[i:end]
            
            # Upsert users
            u_ok, u_msg, u_status = client.bulk_upsert_users(u_batch)
            if not u_ok:
                if u_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on users; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                for j, r in enumerate(records[i:end], start=i+1):
                    ok, msg, stc = client.upsert_user(build_user_payload(normalize_record(r)))
                    if not ok:
                        summary["user_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
            
            # Fire registration events for ALL records
            r_ok, r_msg, r_status = client.bulk_fire_events(r_batch)
            if not r_ok:
                if r_status == 429 and dyn_batch > 5:
                    dyn_batch = max(5, dyn_batch // 2)
                    status_text.text(f"429 on registration events; reducing batch to {dyn_batch} and retrying after backoff...")
                    time.sleep(5)
                    continue
                for j, r in enumerate(records[i:end], start=i+1):
                    payload = build_bootcamp_registration_event_payload(normalize_record(r), day_label, registration_event_name, registration_extra)
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["registration_success"] += 1
                    else:
                        summary["registration_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
            else:
                summary["registration_success"] += len(r_batch)
            
            i = end
            progress.progress(i / total)
            if i % max(10, dyn_batch) == 0 or i == total:
                status_text.text(f"Processed {i}/{total} registrations... Registration success: {summary['registration_success']} (batch={dyn_batch})")
        
        # Process attended events separately (only for attended records)
        if total_attended > 0:
            status_text.text(f"Processing {total_attended} attended events...")
            i_att = 0
            dyn_batch_att = max(5, int(batch_size))
            while i_att < total_attended:
                end_att = min(i_att + dyn_batch_att, total_attended)
                a_batch = atts[i_att:end_att]
                
                # Fire attended events ONLY for attended records
                a_ok, a_msg, a_status = client.bulk_fire_events(a_batch)
                if not a_ok:
                    if a_status == 429 and dyn_batch_att > 5:
                        dyn_batch_att = max(5, dyn_batch_att // 2)
                        status_text.text(f"429 on attended events; reducing batch to {dyn_batch_att} and retrying after backoff...")
                        time.sleep(5)
                        continue
                    # Fallback to individual calls for this batch
                    for j, r in enumerate(attended_records[i_att:end_att], start=i_att+1):
                        payload = build_bootcamp_attended_event_payload(normalize_record(r), day_label, attended_event_name, attended_extra)
                        ok, msg, stc = client.fire_event(payload)
                        if ok:
                            summary["attended_success"] += 1
                        else:
                            # Note: row number here refers to position in attended_df
                            summary["attended_failures"].append({"row": j, "user_id": r.get("UserID"), "message": msg, "status": stc})
                else:
                    summary["attended_success"] += len(a_batch)
                
                i_att = end_att
                if i_att % max(10, dyn_batch_att) == 0 or i_att == total_attended:
                    status_text.text(f"Processed {i_att}/{total_attended} attended events... Attended success: {summary['attended_success']} (batch={dyn_batch_att})")
        if final_retry:
            # retry 429s for registrations
            reg_429s = [f for f in summary["registration_failures"] if f.get("status") == 429]
            if reg_429s:
                time.sleep(10)
                still: List[Dict[str, object]] = []
                for f in reg_429s:
                    idx = int(f.get("row", 0)) - 1
                    payload = build_bootcamp_registration_event_payload(
                        normalize_record(records[idx]), day_label, registration_event_name, registration_extra
                    )
                    ok, msg, stc = client.fire_event(payload)
                    if ok:
                        summary["registration_success"] += 1
                    else:
                        still.append({"row": f["row"], "user_id": f.get("user_id"), "message": msg, "status": stc})
                summary["registration_failures"] = [f for f in summary["registration_failures"] if f.get("status") != 429] + still
            
            # retry 429s for attended events (using attended_records)
            att_429s = [f for f in summary["attended_failures"] if f.get("status") == 429]
            if att_429s:
                time.sleep(10)
                still: List[Dict[str, object]] = []
                for f in att_429s:
                    idx = int(f.get("row", 0)) - 1
                    # Note: row index refers to attended_records, not all records
                    if idx < len(attended_records):
                        payload = build_bootcamp_attended_event_payload(
                            normalize_record(attended_records[idx]), day_label, attended_event_name, attended_extra
                        )
                        ok, msg, stc = client.fire_event(payload)
                        if ok:
                            summary["attended_success"] += 1
                        else:
                            still.append({"row": f["row"], "user_id": f.get("user_id"), "message": msg, "status": stc})
                summary["attended_failures"] = [f for f in summary["attended_failures"] if f.get("status") != 429] + still
    else:
        # Non-bulk path
        status_text.text(f"Processing {total} registrations, {total_attended} attended (rate limited)...")
        for idx, raw in enumerate(records, start=1):
            record = normalize_record(raw)
            user_payload = build_user_payload(record)
            user_ok, user_msg, user_status = client.upsert_user(user_payload)
            if not user_ok:
                summary["user_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": user_msg, "status": user_status})
            
            # Fire registration event for ALL records
            reg_payload = build_bootcamp_registration_event_payload(record, day_label, registration_event_name, registration_extra)
            reg_ok, reg_msg, reg_status = client.fire_event(reg_payload)
            if reg_ok:
                summary["registration_success"] += 1
            else:
                summary["registration_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": reg_msg, "status": reg_status})
            
            # Fire attended event ONLY if Attended="Yes"
            if raw.get("Attended") == "Yes":
                att_payload = build_bootcamp_attended_event_payload(record, day_label, attended_event_name, attended_extra)
                att_ok, att_msg, att_status = client.fire_event(att_payload)
                if att_ok:
                    summary["attended_success"] += 1
                else:
                    summary["attended_failures"].append({"row": idx, "user_id": record.get("UserID"), "message": att_msg, "status": att_status})
            
            progress.progress(idx / total)
            if idx % 10 == 0 or idx == total:
                status_text.text(f"Processed {idx}/{total} records... Registration: {summary['registration_success']}/{total}, Attended: {summary['attended_success']}/{total_attended}")
    
    progress.empty()
    status_text.empty()
    return summary


def parse_json_config(raw: str, default: Dict[str, str]) -> Dict[str, str]:
    raw = raw.strip()
    if not raw:
        return default
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError
        return {str(k): str(v) for k, v in payload.items()}
    except ValueError as exc:  # pragma: no cover - user input
        raise ValueError("Configuration must be a JSON object") from exc


if __name__ == "__main__":  # pragma: no cover - Streamlit runtime
    main()
