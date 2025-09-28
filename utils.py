# utils.py
import math
from datetime import datetime, timedelta, time

NSW_PUBLIC_HOLIDAYS = {
    "2025-01-01", "2025-01-27", "2025-04-18", "2025-04-19", "2025-04-20", "2025-04-21",
    "2025-04-25", "2025-06-09", "2025-10-06", "2025-12-25", "2025-12-26"
}
rate_constants = {
    "Afternoon Shift": 4.84, "Night Shift": 5.69, "Early Morning": 4.84,
    "Special Loading": 5.69, "OT 150%": 74.72763, "OT 200%": 99.63684,
    "ADO Adjustment": 49.81842, "Sat Loading 50%": 24.90921, "Sun Loading 100%": 49.81842,
    "Public Holiday": 49.81842, "PH Loading 50%": 24.90921, "PH Loading 100%": 49.81842,
    "Sick With MC": 49.81842, "Ordinary Hours": 49.81842
}

def parse_time(text: str):
    text = (text or "").strip()
    if not text: return None
    try:
        if ":" in text:
            return datetime.strptime(text, "%H:%M").time()
        if text.isdigit() and len(text) in [3,4]:
            h, m = int(text[:-2]), int(text[-2:])
            return time(h, m)
    except:  # noqa: E722
        return None
    return None

def parse_duration(text: str) -> float:
    text = (text or "").strip()
    if not text: return 0
    try:
        if ":" in text:
            h, m = map(int, text.split(":"))
            return h + m/60
        if text.isdigit():
            h, m = int(text[:-2]), int(text[-2:])
            return h + m/60
    except:  # noqa: E722
        return 0
    return 0

def calculate_row(day, values, sick, penalty_value, special_value, unit_val):
    # values: [rs_on, as_on, rs_off, as_off, worked, extra]
    ot_rate = 0
    if values[0].upper() == "ADO" and unit_val >= 0:
        ot_rate = round(unit_val * rate_constants["ADO Adjustment"], 2)
    elif values[0].upper() not in ["OFF", "ADO"] and unit_val >= 0:
        ot_rate = round(unit_val * (rate_constants["OT 200%"] if day in ["Saturday","Sunday"] else rate_constants["OT 150%"]), 2)
    else:
        if day == "Saturday":
            ot_rate = round(unit_val * (rate_constants["Sat Loading 50%"] + rate_constants["Ordinary Hours"]), 2)
        elif day == "Sunday":
            ot_rate = round(unit_val * (rate_constants["Sun Loading 100%"] + rate_constants["Ordinary Hours"]), 2)
        else:
            if penalty_value in ["Afternoon","Morning"]:
                ot_rate = round(unit_val * (rate_constants["Afternoon Shift"] + rate_constants["Ordinary Hours"]), 2)
            elif penalty_value == "Night":
                ot_rate = round(unit_val * (rate_constants["Night Shift"] + rate_constants["Ordinary Hours"]), 2)
            else:
                ot_rate = round(unit_val * rate_constants["Ordinary Hours"], 2)

    worked_hours = parse_duration(values[4]) or 8
    penalty_hours = math.floor(worked_hours)

    penalty_rate = 0
    if penalty_value == "Afternoon": penalty_rate = round(penalty_hours * rate_constants["Afternoon Shift"], 2)
    elif penalty_value == "Night":   penalty_rate = round(penalty_hours * rate_constants["Night Shift"], 2)
    elif penalty_value == "Morning": penalty_rate = round(penalty_hours * rate_constants["Early Morning"], 2)

    special_loading = round(rate_constants["Special Loading"], 2) if special_value == "Yes" else 0
    sick_rate = round(8 * rate_constants["Sick With MC"], 2) if sick else 0
    daily_rate = 0 if values[0].upper() in ["OFF","ADO"] else round(8 * rate_constants["Ordinary Hours"], 2)

    if any(v.upper() == "ADO" for v in values):
        daily_rate += round(4 * rate_constants["Ordinary Hours"], 2)

    loading = 0
    if values[0].upper() not in ["OFF","ADO"]:
        if day == "Saturday": loading = round(8 * rate_constants["Sat Loading 50%"], 2)
        elif day == "Sunday": loading = round(8 * rate_constants["Sun Loading 100%"], 2)

    daily_count = ot_rate + penalty_rate + special_loading + sick_rate + daily_rate + loading
    return ot_rate, penalty_rate, special_loading, sick_rate, daily_rate, loading, daily_count
