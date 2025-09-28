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
st.title("📊 Timesheet Calculator (14-day Fortnight • Row Layout)")

start_date = st.date_input("Select Start Date")

if start_date:
    st.caption("Enter times as HH:MM or HHMM. Worked blank→8h. Toggles: Sick acts like OFF; ADO overrides OFF/Sick.")
    rows = []
    any_ado = False

    # short labels for mobile
    header = st.columns([1.6, 1, 1, 1, 1, 1, 1, 0.8, 0.7, 0.8])  # Weekday/Date, R On, A On, R Off, A Off, Work, Extra, Sick, Off, ADO
    header[0].markdown("**Day**")
    header[1].markdown("**R On**")
    header[2].markdown("**A On**")
    header[3].markdown("**R Off**")
    header[4].markdown("**A Off**")
    header[5].markdown("**Work**")
    header[6].markdown("**Extra**")
    header[7].markdown("**Sick**")
    header[8].markdown("**Off**")
    header[9].markdown("**ADO**")

    # Collect inputs row-by-row
    inputs = []
    for i in range(14):
        date = start_date + timedelta(days=i)
        weekday = date.strftime("%A")
        date_str = date.strftime("%Y-%m-%d")

        cols = st.columns([1.6, 1, 1, 1, 1, 1, 1, 0.8, 0.7, 0.8])
        cols[0].markdown(f"**{weekday}**<br><span style='font-size:0.9em;color:#888'>{date_str}</span>", unsafe_allow_html=True)
        r_on  = cols[1].text_input("R On",  key=f"r_on_{i}",  label_visibility="collapsed")
        a_on  = cols[2].text_input("A On",  key=f"a_on_{i}",  label_visibility="collapsed")
        r_off = cols[3].text_input("R Off", key=f"r_off_{i}", label_visibility="collapsed")
        a_off = cols[4].text_input("A Off", key=f"a_off_{i}", label_visibility="collapsed")
        work  = cols[5].text_input("Work",  key=f"work_{i}",  label_visibility="collapsed")
        extra = cols[6].text_input("Extra", key=f"ext_{i}",   label_visibility="collapsed")
        sick  = cols[7].checkbox("Sick", key=f"sick_{i}", label_visibility="collapsed")
        off_t = cols[8].checkbox("Off",  key=f"off_{i}",  label_visibility="collapsed")
        ado_t = cols[9].checkbox("ADO",  key=f"ado_{i}",  label_visibility="collapsed")

        inputs.append({
            "weekday": weekday, "date": date, "date_str": date_str,
            "r_on": r_on, "a_on": a_on, "r_off": r_off, "a_off": a_off,
            "work": work, "extra": extra, "sick": sick, "off": off_t, "ado": ado_t
        })

    if st.button("Calculate"):
        for row in inputs:
            weekday = row["weekday"]
            date = row["date"]
            date_str = row["date_str"]

            values = [
                (row["r_on"] or "").strip(),
                (row["a_on"] or "").strip(),
                (row["r_off"] or "").strip(),
                (row["a_off"] or "").strip(),
                (row["work"] or "").strip(),
                (row["extra"] or "").strip(),
            ]
            sick = bool(row["sick"])
            off_toggle = bool(row["off"])
            ado_toggle = bool(row["ado"])

            # precedence: ADO > Sick/Off > none
            effective_values = values.copy()
            chosen_flag = None
            if ado_toggle:
                effective_values[0] = "ADO"; chosen_flag = "ADO"
            elif sick or off_toggle:
                effective_values[0] = "OFF"; chosen_flag = "OFF"

            # Holiday flag
            is_holiday = "Yes" if date_str in NSW_PUBLIC_HOLIDAYS else "No"

            # ---- Unit (original logic) ----
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

            unit = round(unit, 2)

            # ---- Penalty (use effective values) ----
            penalty = "No"
            AS_ON  = parse_time(effective_values[1])
            AS_OFF = parse_time(effective_values[3])
            if not any(v.upper() in ["OFF","ADO"] for v in effective_values) and not sick and AS_ON and AS_OFF and weekday not in ["Saturday","Sunday"]:
                m1 = AS_ON.hour * 60 + AS_ON.minute
                m2 = AS_OFF.hour * 60 + AS_OFF.minute
                if m2 < m1: m2 += 1440
                if 1080 <= m1 % 1440 <= 1439 or 0 <= m1 % 1440 <= 239:
                    penalty = "Night"
                elif 240 <= m1 % 1440 <= 330:
                    penalty = "Morning"
                elif m1 <= 1080 <= m2:
                    penalty = "Afternoon"

            # ---- Special (use effective values) ----
            special = "No"
            if not any(v.upper() in ["OFF","ADO"] for v in effective_values) and not sick and weekday not in ["Saturday","Sunday"]:
                if (AS_ON and time(1,1) <= AS_ON <= time(3,59)) or (AS_OFF and time(1,1) <= AS_OFF <= time(3,59)):
                    special = "Yes"

            # ---- Rates ----
            ot, prate, sload, srate, drate, lrate, dcount = calculate_row(
                weekday, effective_values, sick, penalty, special, unit
            )
            if any(v.upper()=="ADO" for v in effective_values):
                any_ado = True

            display_rs_on = chosen_flag if chosen_flag else values[0]

            rows.append([
                weekday, date_str, display_rs_on, values[1], values[2], values[3], values[4], values[5],
                "Yes" if sick else "No", f"{unit:.2f}", penalty, special, is_holiday,
                f"{ot:.2f}", f"{prate:.2f}", f"{sload:.2f}", f"{srate:.2f}",
                f"{lrate:.2f}", f"{drate:.2f}", f"{dcount:.2f}"
            ])

        # Output table
        cols = [
            "Weekday","Date","R On","A On","R Off","A Off","Work","Extra","Sick",
            "Unit","Penalty","Special","Holiday",
            "OT Rate","Penalty Rate","Special Ldg","Sick Rate","Loading","Daily Rate","Daily Count"
        ]
        df = pd.DataFrame(rows, columns=cols)

        # Totals from floats
        num_cols = cols[13:]
        totals_float = [pd.to_numeric(df[c], errors="coerce").fillna(0).sum() for c in num_cols]

        # Long-fortnight deduction if no ADO anywhere
        if not any_ado:
            deduction = 0.5 * rate_constants["Ordinary Hours"] * 8  # ≈ 199.275
            totals_float[-1] -= deduction
            st.warning(f"Applied long-fortnight deduction: -{deduction:.2f}")

        totals_fmt = [f"{t:.2f}" for t in totals_float]
        df.loc[len(df)] = ["TOTAL","","","","","","","","","", "", "", ""] + totals_fmt

        def highlight_total(row):
            return ['background-color: #d0ffd0' if row.name == len(df)-1 else '' for _ in row]

        st.dataframe(df.style.apply(highlight_total, axis=1), use_container_width=True)
