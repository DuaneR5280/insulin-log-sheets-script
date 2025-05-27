import gspread
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import re
import unicodedata
import os

# Set up
from dotenv import load_dotenv
load_dotenv()

gc = gspread.service_account(filename='service_account.json')
sheet_id = os.getenv('SHEET_ID')

sh = gc.open_by_key(sheet_id)
worksheets = sh.worksheets()
sheet_names = [ws.title for ws in worksheets if ws.title[0].isdigit()]

# Trends
BG_TREND_PATTERN = re.compile(r"(\d+)\s*([⬆️⬇️➡️⬅️↗️↘️↖️↙️]?)")

def normalize_emoji(e: str) -> str:
    """
    Normalize an emoji string by stripping variation selectors and normalizing
    the Unicode representation.
    
    Variation selectors are special Unicode characters that allow for different
    visual representations of the same emoji. For example, the emoji "1️⃣" is
    represented as the character "1" followed by the variation selector "️".
    This function removes these selectors, so that the emoji is represented only
    by its base character.
    
    The Unicode normalization is done using the NFKD normalization form, which
    is a compatibility decomposition. This means that the resulting string can
    be compared to other strings that contain the same emoji, even if they were
    originally represented differently.
    
    :param e: The emoji string to normalize.
    :return: The normalized emoji string.
    """
    return ''.join(c for c in unicodedata.normalize('NFKD', e) if not unicodedata.category(c).startswith('M'))

EMOJI_TO_TREND = {
    normalize_emoji(k): v for k, v in {
    "⬆️⬆️": "rapidly rising",
    "⬇️⬇️": "rapidly falling",
    "⬆️": "rising",
    "⬇️": "falling",
    "↗️": "slowly rising",
    "↘️": "slowly falling",
    "➡️": "steady",
    }.items()
}


@dataclass
class InsulinLog:
    date: str
    time: str
    blood_glucose: int
    carbs: int | float
    insulin: int | float
    notes: str = ""
    ts: datetime = field(init=False)
    trend: Optional[str] = field(default=None)
    trend_arrow: Optional[str] = field(default=None)

    def __post_init__(self):
        """
        Post-init method to set `ts` attribute based on `date` and `time` attributes.
        Also, if `trend_arrow` is set, it looks up the trend description in the
        `EMOJI_TO_TREND` dictionary and sets `trend` attribute accordingly.
        """
        if self.trend_arrow:
            normalized_arrow = normalize_emoji(self.trend_arrow)
            self.trend = EMOJI_TO_TREND.get(normalized_arrow, None)
        self.ts = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
        

    def __str__(self):
        return f"{self.date} {self.time} {self.blood_glucose} {self.carbs} {self.insulin} {self.notes}"


# Parse
def extract_bg_and_trend(value: str | int) -> tuple[int, str | None]:
    """
    Extract blood glucose value and trend arrow from a string value.

    Args:
        value: String or integer value to be parsed.

    Returns:
        Tuple of two values: blood glucose value as integer, and trend arrow as string or None.
    """
    if not value:
        return 0, None
    value = str(value).strip()
    match = BG_TREND_PATTERN.match(value)
    if match:
        bg = int(match.group(1))
        trend_arrow = match.group(2) or None
        return bg, trend_arrow
    try:
        return int(value), None
    except ValueError:
        return 0, None
        

def parse_to_insulin_logs(rows: List[dict]) -> List[InsulinLog]:
    """
    Parse a list of dict-rows into a list of InsulinLog instances.

    This function takes a list of dict-rows, where each row is expected to have
    the same columns, and tries to extract the following information from each
    row:

    - Date
    - Time
    - Blood glucose
    - Trend arrow
    - Carbs
    - Insulin
    - Notes

    The function groups the rows by date and meal time, and then creates an
    InsulinLog instance for each date-meal time entry. The InsulinLog instance
    is created with the extracted information, and the resulting list of
    InsulinLog instances is returned.

    Note that the function expects the columns to be in a certain order, and
    that the columns are named in a certain way. If the columns are not named
    correctly, or if the columns are not in the correct order, the function
    will not work correctly.

    :param rows: A list of dict-rows.
    :return: A list of InsulinLog instances.
    """
    logs = []

    # Early exit if no data
    if not rows:
        return logs

    # Fixed metadata columns
    fixed_columns = {'Status', 'Date', 'Results', 'Comments'}

    # Get all columns from first row keys, minus fixed ones
    all_columns = set(rows[0].keys())
    meal_columns = list(all_columns - fixed_columns)

    # Sort meal columns
    meal_columns.sort()

    grouped = {}

    for row in rows:
        date = row.get('Date')
        result = row.get('Results')
        if not date or not result:
            continue

        if date not in grouped:
            grouped[date] = {
                'Time': {},
                'BG': {},
                'TrendArrow': {},
                'Carbs': {},
                'Insulin': {},
                'Comments': ''
            }

        if result == 'Time':
            for meal in meal_columns:
                val = row.get(meal)
                if val and str(val).strip():
                    grouped[date]['Time'][meal] = str(val).strip()
            grouped[date]['Comments'] = row.get('Comments', '').strip()

        elif result == 'BG':
            for meal in meal_columns:
                val = row.get(meal)
                if val and str(val).strip():
                    try:
                        bg, trend_arrow = extract_bg_and_trend(val)
                        grouped[date]['BG'][meal] = bg
                        grouped[date]['TrendArrow'][meal] = trend_arrow
                    except (ValueError, TypeError):
                        grouped[date]['BG'][meal] = 0

        elif result == 'Carbs':
            for meal in meal_columns:
                val = row.get(meal)
                if val and str(val).strip():
                    try:
                        num = float(val)
                        grouped[date]['Carbs'][meal] = int(num) if num.is_integer() else num
                    except (ValueError, TypeError):
                        grouped[date]['Carbs'][meal] = 0

        elif result == 'Insulin':
            for meal in meal_columns:
                val = row.get(meal)
                if val and str(val).strip():
                    try:
                        num = float(val)
                        grouped[date]['Insulin'][meal] = int(num) if num.is_integer() else num
                    except (ValueError, TypeError):
                        grouped[date]['Insulin'][meal] = 0

    # Create InsulinLog instances for each date-meal time entry
    for date, data in grouped.items():
        times = data['Time']
        for meal, time_str in times.items():
            bg = data['BG'].get(meal, 0)
            carbs = data['Carbs'].get(meal, 0)
            insulin = data['Insulin'].get(meal, 0)
            notes = data['Comments']
            trend_arrow = data['TrendArrow'].get(meal, None)
            log = InsulinLog(
                date=date,
                time=time_str,
                blood_glucose=bg,
                trend_arrow=trend_arrow,
                carbs=carbs,
                insulin=insulin,
                notes=notes
            )
            logs.append(log)

    return logs

def parse_sheets(sheets: list) -> list:

    sheet_logs = []

    for sheet_name in sheets:
        ws = sh.worksheet(sheet_name)
        rows = ws.get_all_records()
        logs = parse_to_insulin_logs(rows)
        sheet_logs.extend(logs)

    return sorted(sheet_logs, key=lambda log: log.ts)        


def compare_logs(log1: list[InsulinLog], log2: list[dict]) -> list:
    # Compare with old logs to see if already entered manually
    existing_timestamps = set()

    for row in log2:
        dt_str = row.get('Date Time') or f"{row.get('Date')} {row.get('Time')}"

        try:
            dt = datetime.strptime(dt_str.strip(), "%m/%d/%Y %H:%M:%S")
            existing_timestamps.add(dt)
        except ValueError:
            continue

    return [log for log in log1 if log.ts not in existing_timestamps]


def log_to_row(log: InsulinLog) -> list:
    return [
        log.ts.date().isoformat(),
        log.ts.time().strftime("%H:%M:%S"),
        "",  # Date Time (sheet formula may update this)
        log.blood_glucose,
        log.trend or "",  # Trend Arrow (sheet formula may update this)
        "",  # Trend (optional, if formula-based in sheet)
        log.carbs if log.carbs else "",
        log.insulin if log.insulin else "",
        log.notes or "",
    ]


if __name__ == "__main__":
    # Parse existing sheet data
    sorted_logs = parse_sheets(sheet_names)
    
    # Log sheet data (new sheet we're inputting existing data into)
    log_ws = sh.worksheet('Log')
    log_sheet = log_ws.get_all_records()
    # Filter out empty rows
    valid_logs = [log for log in log_sheet if log.get('Date')]
    # Compare with existing logs for data already entered
    new_logs = compare_logs(sorted_logs, valid_logs)

    # Prepare rows for insertion
    rows_to_append = [log_to_row(log) for log in new_logs]

    # Only append if there's something to add
    if rows_to_append:
        log_ws.append_rows(rows_to_append, value_input_option="USER_ENTERED")
