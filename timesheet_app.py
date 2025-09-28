import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
import math

# ---------- Constants ----------
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

# ---------- Helpers ----------
def parse_time(text: str):
    text = "" if text is None else str(text).strip()
    if not text:
        return None
    if ":" in text:
        try:
            return datetime.strptime(text, "%H:%M").time()
        except:
            return None
    if text.isdigit() and len(text) in [3, 4]:
        try:
            h = int(text[:-2]); m = int(text[-2:])
            return time(hour=h, minute=m)
        except:
            return None
    return None

def parse_duration(text: str) -> float:
    text = "" if text is None else str(text).strip()
    if not text:
        return 0
    if ":" in text:
        try:
            h, m = map(int, text.split(":"))
            return h + m / 60
        except:
            return 0
    if text.isdigit():
        try:
            h = int(text[:-2]); m = int(text[-2:])
            return h + m / 60
        except:
            return 0
    return 0

def calculate_row(day, values, sick, penalty_value, special_value, unit_val):
    # values: [rs_on, as_on, rs_off, as_off, worked, extra]
    ot_rate = 0
    if values[0].upper() == "ADO" and unit_val >= 0:
        ot_rate = round(unit_val * rate_constants["ADO Adjustment"], 2)
    elif values[0].upper() not in ["OFF", "ADO"] and unit_val >= 0:
        if day in ["Saturday", "Sunday"]:
            ot_rate = round(unit_val * rate_constants["OT 200%"], 2)
        else:
            ot_rate = round(unit_val * rate_constants["OT 150%"], 2)
    else:
        # negative or OFF/ADO -> ordinary + applicable loading
        if day == "Saturday":
            ot_rate = round(unit_val * rate_constants["Sat Loading 50%"] + unit_val * rate_constants["Ordinary Hours"], 2)
        elif day == "Sunday":
            ot_rate = round(unit_val * rate_constants["Sun Loading 100%"] + unit_val * rate_constants["Ordinary Hours"], 2)
        else:
            if penalty_value in ["Afternoon", "Morning"]:
                ot_rate = round(unit_val * rate_constants["Afternoon Shift"] + unit_val * rate_constants["Ordinary Hours"], 2)
            elif penalty_value == "Night":
                ot_rate = round(unit_val * rate_constants["Night Shift"] + unit_val * rate_constants["Ordinary Hours"], 2)
            else:
                ot_rate = round(unit_val * rate_constants["Ordinary Hours"], 2)

    # Penalty hours: floor(worked), default 8 if blank/invalid
    worked_hours = parse_duration(values[4])
    if worked_hours == 0:
        worked_hours = 8
    penalty_hours = math.floor(worked_hours)

    penalty_rate = 0
    if penalty_value == "Afternoon":
        penalty_rate = round(penalty_hours * rate_constants["Afternoon Shift"], 2)
    elif penalty_value == "Night":
        penalty_rate = round(penalty_hours * rate_constants["Night Shift"], 2)
    elif penalty_value == "Morning":
        penalty_rate = round(penalty_hours * rate_constants["Early Morning"], 2)

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

# ---------- App ----------
st.title("📊 Timesheet Calculator (14-day Fortnight • Grid Input)")

start_date = st.date_input("Select Start Date")

if start_date:
    # Editable grid (one row per day)
    dates = [start_date + timedelta(days=i) for i in range(14)]
    df_input = pd.DataFrame({
        "Weekday": [d.strftime("%A") for d in dates],
        "Date":    [d.strftime("%Y-%m-%d") for d in dates],
        "R On":    ["" for _ in dates],
        "A On":    ["" for _ in dates],
        "R Off":   ["" for _ in dates],
        "A Off":   ["" for _ in dates],
        "Work":    ["" for _ in dates],
        "Extra":   ["" for _ in dates],
        "Sick":    [False for _ in dates],
        "Off":     [False for _ in dates],   # NEW
        "ADO":     [False for _ in dates],   # NEW
    })

    st.caption("Tip: Enter times as HH:MM or HHMM. Leave Work blank to default to 8h. Use Sick/Off/ADO toggles.")
    edited = st.data_editor(
        df_input,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Weekday": st.column_config.Column(width=110, disabled=True),
            "Date":    st.column_config.Column(width=110, disabled=True),
            "R On":    st.column_config.TextColumn(width=90, help="Rostered Sign-on (HH:MM or HHMM)"),
            "A On":    st.column_config.TextColumn(width=90, help="Actual Sign-on (HH:MM or HHMM)"),
            "R Off":   st.column_config.TextColumn(width=90, help="Rostered Sign-off (HH:MM or HHMM)"),
            "A Off":   st.column_config.TextColumn(width=90, help="Actual Sign-off (HH:MM or HHMM)"),
            "Work":    st.column_config.TextColumn(width=80, help="Total worked (blank→8)"),
            "Extra":   st.column_config.TextColumn(width=80, help="Extra time"),
            "Sick":    st.column_config.CheckboxColumn(width=60, help="Counts like OFF with Sick rate"),
            "Off":     st.column_config.CheckboxColumn(width=55, help='Acts as entering "OFF"'),
            "ADO":     st.column_config.CheckboxColumn(width=60, help='Acts as entering "ADO"'),
        }
    )

    if st.button("Calculate"):
        rows = []
        any_ado = False

        for _, r in edited.iterrows():
            weekday = str(r["Weekday"])
            date_str = str(r["Date"])
            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            # Raw values from grid
            values = [
                str(r["R On"] or "").strip(),
                str(r["A On"] or "").strip(),
                str(r["R Off"] or "").strip(),
                str(r["A Off"] or "").strip(),
                str(r["Work"] or "").strip(),
                str(r["Extra"] or "").strip(),
            ]
            sick = bool(r["Sick"])
            off_toggle = bool(r["Off"])
            ado_toggle = bool(r["ADO"])

            # Effective values with precedence: ADO > Sick/Off > none
            effective_values = values.copy()
            chosen_flag = None
            if ado_toggle:
                effective_values[0] = "ADO"
                chosen_flag = "ADO"
            elif sick or off_toggle:
                effective_values[0] = "OFF"
                chosen_flag = "OFF"

            # Holiday
            is_holiday = "Yes" if date_str in NSW_PUBLIC_HOLIDAYS else "No"

            # ---------- Unit (original logic) ----------
            unit = 0.0
            if any(v.upper() in ["OFF", "ADO"] for v in effective_values) or sick:
                unit = 0.0
            else:
                RS_ON  = parse_time(effective_values[0])
                AS_ON  = parse_time(effective_values[1])
                RS_OFF = parse_time(effective_values[2])
                AS_OFF = parse_time(effective_values[3])
                worked_f = parse_duration(effective_values[4])
                extra_f  = parse_duration(effective_values[5])

                if RS_ON and RS_OFF and AS_ON and AS_OFF:
                    rs_start = datetime.combine(date, RS_ON)
                    rs_end   = datetime.combine(date, RS_OFF)
                    if RS_OFF < RS_ON:
                        rs_end += timedelta(days=1)

                    as_start = datetime.combine(date, AS_ON)
                    as_end   = datetime.combine(date, AS_OFF)
                    if AS_OFF < AS_ON:
                        as_end += timedelta(days=1)

                    built_up = 0
                    if as_start < rs_start:  # lift-up
                        delta = (rs_end - as_end).total_seconds() / 3600
                    elif as_end > rs_end:    # lay-back
                        delta = abs((as_start - rs_start).total_seconds() / 3600)
                    elif as_start >= rs_start and as_end <= rs_end and (as_end - as_start) < (rs_end - rs_start):
                        delta = abs((rs_end - rs_start).total_seconds() / 3600) - 8
                        built_up = 1
                    else:
                        delta = 0.0

                    if worked_f and built_up == 0:
                        worked_use = worked_f
                    elif worked_f and built_up == 1:
                        worked_use = 8
                    else:
                        worked_use = 8

                    unit = delta + (worked_use - 8) + (extra_f or 0)
                else:
                    unit = 0.0

            # Round once, then use everywhere
            unit = round(unit, 2)

            # ---------- Penalty (use effective_values) ----------
            penalty = "No"
            AS_ON  = parse_time(effective_values[1])
            AS_OFF = parse_time(effective_values[3])
            if not any(v.upper() in ["OFF", "ADO"] for v in effective_values) and not sick and AS_ON and AS_OFF and weekday not in ["Saturday","Sunday"]:
                m1 = AS_ON.hour * 60 + AS_ON.minute
                m2 = AS_OFF.hour * 60 + AS_OFF.minute
                if m2 < m1:
                    m2 += 1440
                if 1080 <= m1 % 1440 <= 1439 or 0 <= m1 % 1440 <= 239:
                    penalty = "Night"
                elif 240 <= m1 % 1440 <= 330:
                    penalty = "Morning"
                elif m1 <= 1080 <= m2:
                    penalty = "Afternoon"

            # ---------- Special (use effective_values) ----------
            special = "No"
            if not any(v.upper() in ["OFF", "ADO"] for v in effective_values) and not sick and weekday not in ["Saturday","Sunday"]:
                if (AS_ON and time(1,1) <= AS_ON <= time(3,59)) or (AS_OFF and time(1,1) <= AS_OFF <= time(3,59)):
                    special = "Yes"

            # ---------- Rates (use effective_values) ----------
            ot, prate, sload, srate, drate, lrate, dcount = calculate_row(
                weekday, effective_values, sick, penalty, special, unit
            )

            if any(v.upper() == "ADO" for v in effective_values):
                any_ado = True

            # Display in R On cell: chosen flag ("OFF"/"ADO") if set, else original
            display_rs_on = chosen_flag if chosen_flag else values[0]

            # Store as strings with 2 decimals for display
            rows.append([
                weekday, date_str, display_rs_on, values[1], values[2], values[3], values[4], values[5],
                "Yes" if sick else "No", f"{unit:.2f}", penalty, special, is_holiday,
                f"{ot:.2f}", f"{prate:.2f}", f"{sload:.2f}", f"{srate:.2f}",
                f"{lrate:.2f}", f"{drate:.2f}", f"{dcount:.2f}"
            ])

        # Build output table
        cols = [
            "Weekday","Date","R On","A On","R Off","A Off","Work","Extra","Sick",
            "Unit","Penalty","Special","Holiday",
            "OT Rate","Penalty Rate","Special Ldg","Sick Rate","Loading","Daily Rate","Daily Count"
        ]
        df = pd.DataFrame(rows, columns=cols)

        # Numeric totals: compute from floats (not the formatted strings)
        num_cols = cols[13:]
        totals_float = [pd.to_numeric(df[c], errors="coerce").fillna(0).sum() for c in num_cols]

        # Long fortnight deduction if no ADO anywhere
        if not any_ado:
            deduction = 0.5 * rate_constants["Ordinary Hours"] * 8  # ≈ 199.275
            totals_float[-1] -= deduction
            st.warning(f"Applied long-fortnight deduction: -{deduction:.2f}")

        # Append TOTAL row as 2-decimal strings
        totals_fmt = [f"{t:.2f}" for t in totals_float]
        total_row = ["TOTAL","","","","","","","","","", "", "", ""] + totals_fmt
        df.loc[len(df)] = total_row

        # Highlight TOTAL row
        def highlight_total(row):
            return ['background-color: #d0ffd0' if row.name == len(df)-1 else '' for _ in row]

        st.dataframe(df.style.apply(highlight_total, axis=1), use_container_width=True)
