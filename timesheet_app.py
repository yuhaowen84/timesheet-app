import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time

# --- Constants ---
rate_constants = {
    "Afternoon Shift": 4.84, "Night Shift": 5.69, "Early Morning": 4.84,
    "Special Loading": 5.69, "OT 150%": 74.72763, "OT 200%": 99.63684,
    "ADO Adjustment": 49.81842, "Sat Loading 50%": 24.90921, "Sun Loading 100%": 49.81842,
    "Public Holiday": 49.81842, "PH Loading 50%": 24.90921, "PH Loading 100%": 49.81842,
    "Sick With MC": 49.81842, "Ordinary Hours": 49.81842
}

def parse_time(text):
    try:
        if ":" in text:
            return datetime.strptime(text, "%H:%M").time()
        elif text.isdigit() and len(text) in [3, 4]:
            h = int(text[:-2]); m = int(text[-2:])
            return time(hour=h, minute=m)
    except:
        return None
    return None

def parse_duration(text):
    try:
        if ":" in text:
            h, m = map(int, text.split(":"))
            return h + m / 60
        elif text.isdigit():
            h = int(text[:-2]); m = int(text[-2:])
            return h + m / 60
    except:
        return 0
    return 0

def calculate_row(day, values, sick, penalty_value, special_value, unit_val):
    ot_rate = 0
    if values[0].upper() == "ADO":
        ot_rate = round(unit_val * rate_constants["ADO Adjustment"], 2)
    elif values[0].upper() not in ["OFF", "ADO"]:
        if day in ["Saturday", "Sunday"]:
            ot_rate = round(unit_val * rate_constants["OT 200%"], 2)
        else:
            ot_rate = round(unit_val * rate_constants["OT 150%"], 2)

    penalty_rate = 0
    if penalty_value == "Afternoon":
        penalty_rate = round(8 * rate_constants["Afternoon Shift"], 2)
    elif penalty_value == "Night":
        penalty_rate = round(8 * rate_constants["Night Shift"], 2)
    elif penalty_value == "Morning":
        penalty_rate = round(8 * rate_constants["Early Morning"], 2)

    special_loading = round(rate_constants["Special Loading"], 2) if special_value == "Yes" else 0
    sick_rate = round(8 * rate_constants["Sick With MC"], 2) if sick else 0
    daily_rate = 0 if values[0].upper() in ["OFF", "ADO"] else round(8 * rate_constants["Ordinary Hours"], 2)

    if any(v.upper() == "ADO" for v in values):
        daily_rate += round(4 * rate_constants["Ordinary Hours"], 2)

    loading = 0
    if values[0].upper() not in ["OFF", "ADO"]:
        if day == "Saturday":
            loading = round(8 * rate_constants["Sat Loading 50%"], 2)
        elif day == "Sunday":
            loading = round(8 * rate_constants["Sun Loading 100%"], 2)

    daily_count = ot_rate + penalty_rate + special_loading + sick_rate + daily_rate + loading
    return ot_rate, penalty_rate, special_loading, sick_rate, daily_rate, loading, daily_count

# --- Streamlit App ---
st.title("📊 Timesheet Calculator (Grid Style with Totals)")

start_date = st.date_input("Select Start Date")

if start_date:
    rows = []
    any_ado = False

    with st.form("timesheet_form"):
        st.markdown("### Timesheet Input")
        for i in range(14):
            date = start_date + timedelta(days=i)
            weekday = date.strftime("%A")
            date_str = date.strftime("%Y-%m-%d")

            st.markdown(f"**{weekday} {date_str}**")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            rs_on = c1.text_input("R Sign-on", key=f"rs_on_{i}")
            as_on = c2.text_input("A Sign-on", key=f"as_on_{i}")
            rs_off = c3.text_input("R Sign-off", key=f"rs_off_{i}")
            as_off = c4.text_input("A Sign-off", key=f"as_off_{i}")
            worked = c5.text_input("Worked", key=f"worked_{i}")
            extra = c6.text_input("Extra", key=f"extra_{i}")

            sick = st.checkbox("Sick", key=f"sick_{i}")

            values = [rs_on, as_on, rs_off, as_off, worked, extra]
            unit = 0 if any(v.upper() in ["OFF","ADO"] for v in values) or sick else parse_duration(worked or "8") - 8 + parse_duration(extra or "0")

            # penalty & special
            penalty, special = "No", "No"
            as_on_time = parse_time(as_on)
            if as_on_time and not sick and weekday not in ["Saturday","Sunday"]:
                if as_on_time.hour >= 18 or as_on_time.hour < 4: penalty="Night"
                elif as_on_time.hour < 6: penalty="Morning"
                elif 12 <= as_on_time.hour < 18: penalty="Afternoon"
            if as_on_time and time(1,1) <= as_on_time <= time(3,59): special="Yes"

            ot, pr, sl, sr, dr, lr, dcount = calculate_row(weekday, values, sick, penalty, special, round(unit,2))
            if any(v.upper()=="ADO" for v in values): any_ado = True

            rows.append([weekday, date_str, unit, penalty, special, ot, pr, sl, sr, dr, lr, dcount])

        submitted = st.form_submit_button("Calculate")

    if submitted:
        df = pd.DataFrame(rows, columns=[
            "Weekday","Date","Unit","Penalty","Special",
            "OT Rate","Penalty Rate","Special Ldg","Sick Rate","Daily Rate","Loading","Daily Count"
        ])

        # Totals
        totals = [df[c].sum() for c in df.columns[5:]]
        if not any_ado:
            deduction = 0.5 * rate_constants["Ordinary Hours"] * 8
            totals[-1] -= deduction
            st.warning(f"Applied long-fortnight deduction: -{deduction:.2f}")

        # Append totals row
        total_row = ["TOTAL","", "", "", ""] + totals
        df.loc[len(df)] = total_row

        st.dataframe(df, use_container_width=True)
