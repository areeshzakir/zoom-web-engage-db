import csv
import json
import math
import re
from datetime import datetime
from io import StringIO
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import streamlit as st


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

PLUTUS_ATTENDEE_LABEL = "Plutus Webinar Attendees"
PLUTUS_REGISTRANT_LABEL = "Plutus Webinar Registrations"

BOOLEAN_TRUE = {"yes", "true", "1", "y"}
BOOLEAN_FALSE = {"no", "false", "0", "n"}

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
    ]:
        work[column] = work[column].astype(str).map(normalize_space)

    for column in ["Join Time", "Leave Time", "Registration Time"]:
        work[column] = work[column].replace("--", "")

    work["User Name (Original Name)"] = work["User Name (Original Name)"].map(proper_case)
    work["First Name"] = work["First Name"].map(proper_case)
    work["Last Name"] = work["Last Name"].map(proper_case)
    work["Country/Region Name"] = work["Country/Region Name"].map(proper_case)
    work["Email"] = work["Email"].str.lower()

    work["Phone"] = work["Phone"].map(normalize_phone)

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

    result["Source Name"] = ""
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
        return ""
    idx = header.index("User Name (Original Name)")
    return proper_case(rows[0][idx])


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

    panelist_name = get_section_primary_name(sections.get("Panelist Details", {}))
    host_name = get_section_primary_name(sections.get("Host Details", {}))

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
    conductor = conductor_map.get(webinar_id) or panelist_name or host_name
    conductor = conductor or ""
    conductor = proper_case(conductor)
    approved_set = {name.lower() for name in approved_conductors}
    if conductor and conductor.lower() not in approved_set:
        conductor_warning = f"Conductor '{conductor}' not in approved list"
    else:
        conductor_warning = ""

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
    df["UserID"] = df["UserID"].map(build_user_id)
    return df[REGISTRATION_SCHEMA]


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


def main() -> None:
    st.set_page_config(page_title="Webinar Attendee Cleaner", layout="wide")
    st.title("Zoom Webinar → WebEngage Cleaner")
    st.caption("Upload raw Zoom attendee report CSVs and export WebEngage-ready data.")

    dataset_type = st.radio(
        "Workflow",
        (PLUTUS_ATTENDEE_LABEL, PLUTUS_REGISTRANT_LABEL),
        horizontal=True,
    )

    with st.sidebar:
        st.header("Configuration")
        category_json = st.text_area(
            "Category token map (JSON)",
            value=json.dumps(DEFAULT_CATEGORY_TOKEN_MAP, indent=2),
            height=200,
        )
        conductor_json = st.text_area(
            "Conductor map (Webinar ID → Name)",
            value=json.dumps(DEFAULT_CONDUCTOR_MAP, indent=2),
            height=160,
        )
        approved_conductors = st.text_area(
            "Approved conductor names (comma separated)",
            value=", ".join(DEFAULT_APPROVED_CONDUCTORS),
            height=80,
        )
        if dataset_type == PLUTUS_ATTENDEE_LABEL:
            threshold = st.slider("Datetime success threshold", 0.8, 1.0, 0.99, 0.01)
        else:
            threshold = None

    upload_label = (
        "Raw Zoom attendee CSV"
        if dataset_type == PLUTUS_ATTENDEE_LABEL
        else "Raw Zoom registrant CSV"
    )
    uploaded = st.file_uploader(upload_label, type=["csv"])

    if uploaded is None:
        st.info("Upload a raw Zoom CSV file to begin.")
        return

    try:
        category_map = parse_json_config(category_json, DEFAULT_CATEGORY_TOKEN_MAP)
        conductor_map = parse_json_config(conductor_json, DEFAULT_CONDUCTOR_MAP)
    except ValueError as err:
        st.error(str(err))
        return

    approved_names = [name.strip() for name in approved_conductors.split(",") if name.strip()]

    button_label = (
        "Process attendee file"
        if dataset_type == PLUTUS_ATTENDEE_LABEL
        else "Process registrant file"
    )

    if st.button(button_label, type="primary"):
        with st.spinner("Cleaning in progress..."):
            try:
                if dataset_type == PLUTUS_ATTENDEE_LABEL:
                    final_df, metadata, logs, stats = process_uploaded_file(
                        uploaded.getvalue(),
                        category_map,
                        conductor_map,
                        threshold if threshold is not None else 0.99,
                        approved_names,
                    )
                else:
                    final_df, metadata, logs, stats = process_registration_file(
                        uploaded.getvalue(),
                        category_map,
                        conductor_map,
                    )
            except Exception as err:  # pragma: no cover - user interaction
                st.error(str(err))
                return

        processed_label = (
            "attendee" if dataset_type == PLUTUS_ATTENDEE_LABEL else "registrant"
        )
        st.success(f"Processed {len(final_df)} clean {processed_label} records")

        meta_cols = st.columns(len(metadata))
        for (label, value), col in zip(metadata.items(), meta_cols):
            col.metric(label, value or "—")

        st.subheader("Preview")
        st.dataframe(final_df, use_container_width=True)

        download_name = (
            "webengage_clean.csv"
            if dataset_type == PLUTUS_ATTENDEE_LABEL
            else "webengage_registration_clean.csv"
        )
        csv_buffer = StringIO()
        final_df.to_csv(csv_buffer, index=False)
        st.download_button(
            "Download cleaned CSV",
            data=csv_buffer.getvalue().encode("utf-8"),
            file_name=download_name,
            mime="text/csv",
        )

        st.subheader("Diagnostics")
        if dataset_type == PLUTUS_ATTENDEE_LABEL:
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
        else:
            reg_ratio = stats.get("registration_parsed", 0) / max(
                stats.get("registration_total", 1), 1
            )
            st.write(f"Registrations parsed: {int(stats.get('registration_parsed', 0))} / {int(stats.get('registration_total', 0))}")
            st.write(f"Deduplicated from {int(stats.get('raw_rows', 0))} to {int(stats.get('dedup_rows', 0))} rows")
            st.write(f"Registration time parse ratio: {reg_ratio:.2%}")
        invalid_phones = stats.get("invalid_phone_rows")
        if invalid_phones:
            st.warning(f"Dropped {int(invalid_phones)} rows with invalid phone numbers.")

        conductor_warning = metadata.get("Conductor Warning")
        if conductor_warning:
            st.warning(conductor_warning)

        st.subheader("Log")
        for entry in logs:
            st.write(entry)


if __name__ == "__main__":  # pragma: no cover - Streamlit runtime
    main()
