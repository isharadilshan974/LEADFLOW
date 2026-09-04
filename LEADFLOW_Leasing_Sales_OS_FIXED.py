
import streamlit as st
import sqlite3
from datetime import datetime, date, timedelta
import pandas as pd
import math

st.set_page_config(
    page_title="LEADFLOW • Leasing Sales OS",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB = "leadflow_sales.db"

# ============================================================
# DATABASE
# ============================================================
def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        nic TEXT,
        vehicle_type TEXT,
        vehicle TEXT,
        vehicle_value REAL DEFAULT 0,
        down_payment REAL DEFAULT 0,
        required_finance REAL DEFAULT 0,
        source TEXT,
        stage TEXT,
        score INTEGER DEFAULT 0,
        temperature TEXT,
        next_action_date TEXT,
        next_action TEXT,
        notes TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        created_at TEXT NOT NULL,
        activity TEXT,
        note TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

# ============================================================
# HELPERS
# ============================================================
def money(v):
    return f"Rs. {float(v):,.0f}"

def clean_phone(p):
    return str(p).strip()

def calculate_score(vehicle_value, down, finance, source, urgency, stage):
    s = 25
    if vehicle_value > 0:
        s += 10
    if vehicle_value > 0:
        dp = down / vehicle_value
        if dp >= 0.30: s += 20
        elif dp >= 0.20: s += 14
        elif dp >= 0.10: s += 8
    if finance > 0:
        s += 10
    if source in ["Referral", "Existing Customer", "Dealer", "Broker"]:
        s += 10
    if urgency == "Today":
        s += 10
    elif urgency == "This week":
        s += 6
    if stage in ["Quotation", "Negotiation", "Documents"]:
        s += 5
    return min(100, int(s))

def temp(score):
    if score >= 80: return "🔥 HOT"
    if score >= 60: return "🟡 WARM"
    return "🔵 COLD"

def lead_df():
    con = get_conn()
    df = pd.read_sql_query("SELECT * FROM leads ORDER BY id DESC", con)
    con.close()
    return df

def add_lead(values):
    con = get_conn()
    con.execute("""
    INSERT INTO leads
    (created_at,name,phone,nic,vehicle_type,vehicle,vehicle_value,
     down_payment,required_finance,source,stage,score,temperature,
     next_action_date,next_action,notes)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, values)
    con.commit()
    con.close()

def update_lead(lead_id, **kwargs):
    if not kwargs:
        return
    con = get_conn()
    sets = ", ".join([f"{k}=?" for k in kwargs])
    vals = list(kwargs.values()) + [lead_id]
    con.execute(f"UPDATE leads SET {sets} WHERE id=?", vals)
    con.commit()
    con.close()

def add_activity(lead_id, activity, note):
    con = get_conn()
    con.execute(
        "INSERT INTO activities(lead_id,created_at,activity,note) VALUES(?,?,?,?)",
        (lead_id, datetime.now().isoformat(timespec="seconds"), activity, note)
    )
    con.commit()
    con.close()

def get_activities(lead_id):
    con = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM activities WHERE lead_id=? ORDER BY id DESC",
        con, params=(lead_id,)
    )
    con.close()
    return df

def emi(principal, rate, years):
    n = int(years * 12)
    if principal <= 0 or n <= 0:
        return 0.0
    r = rate / 100 / 12
    if r == 0:
        return principal / n
    return principal * r * (1+r)**n / ((1+r)**n - 1)

# ============================================================
# STYLE
# ============================================================
st.markdown("""
<style>
.stApp { background:#f4f7fb; }
.block-container { max-width:1280px; padding-top:1rem; padding-bottom:4rem; }
.hero {
    background:linear-gradient(135deg,#0f172a 0%,#172554 55%,#1e3a8a 100%);
    color:#fff; border-radius:24px; padding:26px 28px; margin-bottom:18px;
    box-shadow:0 12px 35px rgba(15,23,42,.18);
}
.hero h1 { margin:0; font-size:32px; font-weight:850; }
.hero p { margin:6px 0 0; color:#cbd5e1; }
.kpi {
    background:#fff; border:1px solid #e5eaf0; border-radius:18px;
    padding:18px; min-height:112px; box-shadow:0 5px 18px rgba(15,23,42,.05);
}
.kpi .label {font-size:12px;color:#64748b;font-weight:700;letter-spacing:.4px;}
.kpi .value {font-size:28px;font-weight:850;color:#0f172a;margin-top:5px;}
.kpi .sub {font-size:12px;color:#94a3b8;margin-top:3px;}
.panel {
    background:#fff; border:1px solid #e5eaf0; border-radius:20px;
    padding:20px; margin-top:16px; box-shadow:0 5px 18px rgba(15,23,42,.04);
}
.badge {display:inline-block;padding:5px 10px;border-radius:999px;background:#eef2ff;font-size:12px;font-weight:700;}
.action {
    background:#fff;border:1px solid #e5eaf0;border-radius:16px;padding:15px;
    margin:8px 0;
}
.small {font-size:12px;color:#64748b;}
.big {font-size:25px;font-weight:850;}
div[data-testid="stMetric"] {background:#fff;border:1px solid #e5eaf0;padding:12px;border-radius:15px;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>🚀 LEADFLOW</h1>
<p>Leasing Sales OS • Find leads • Qualify • Follow-up • Quote • Close</p>
</div>
""", unsafe_allow_html=True)

# ============================================================
# NAVIGATION
# ============================================================
menu = st.radio(
    "Main navigation",
    ["🏠 Command Center","➕ New Lead","🧠 Lead Intelligence","📋 Pipeline",
     "👥 Customers","🧮 Smart Finance","📞 Follow-ups","✍️ Message Lab","📊 Analytics"],
    horizontal=True,
    label_visibility="collapsed"
)

df = lead_df()
today = date.today().isoformat()

# ============================================================
# COMMAND CENTER
# ============================================================
if menu == "🏠 Command Center":
    total = len(df)
    today_leads = len(df[df["created_at"].str[:10] == today]) if total else 0
    hot = len(df[df["temperature"].str.contains("HOT", na=False)]) if total else 0
    due = len(df[(df["next_action_date"].notna()) & (df["next_action_date"] <= today)]) if total else 0
    won = len(df[df["stage"] == "Disbursed"]) if total else 0

    cols = st.columns(5)
    data = [
        ("TODAY'S LEADS", today_leads, "Target: 10"),
        ("HOT LEADS", hot, "Call first"),
        ("FOLLOW-UPS DUE", due, "Action required"),
        ("QUOTATIONS", len(df[df["stage"]=="Quotation"]) if total else 0, "Active"),
        ("DISBURSED", won, "Closed deals"),
    ]
    for c,(lab,val,sub) in zip(cols,data):
        c.markdown(f'<div class="kpi"><div class="label">{lab}</div><div class="value">{val}</div><div class="sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel"><h3>🎯 Daily 10 Lead Mission</h3>', unsafe_allow_html=True)
    st.progress(min(1, today_leads/10))
    if today_leads >= 10:
        st.success("🎉 Daily target reached. Now focus on qualification and conversion.")
    else:
        st.write(f"**{today_leads}/10** new leads captured • **{10-today_leads}** remaining.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='panel'><h3>⚡ Today's Priority Queue</h3>", unsafe_allow_html=True)
    if total:
        priority = df.copy()
        priority["due_rank"] = priority["next_action_date"].fillna("9999-12-31")
        priority = priority.sort_values(["score","due_rank"], ascending=[False,True]).head(8)
        for _,r in priority.iterrows():
            st.markdown(
                f'<div class="action"><b>{r["temperature"]} {r["name"]}</b> • {r["phone"]} '
                f'<span class="badge">Score {int(r["score"])}</span><br>'
                f'<span class="small">{r["vehicle"] or "Vehicle not specified"} • {r["stage"]} • '
                f'Next: {r["next_action"] or "Contact customer"} ({r["next_action_date"] or "—"})</span></div>',
                unsafe_allow_html=True
            )
    else:
        st.info("No leads yet. Start with **➕ New Lead**.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel"><h3>💡 Sales Coach</h3>', unsafe_allow_html=True)
    if not total:
        st.write("Start capturing leads. Once you have data, this section will highlight your strongest sources and follow-up gaps.")
    else:
        source = df["source"].value_counts()
        st.write(f"**Best lead source so far:** {source.index[0]} ({source.iloc[0]} leads)")
        if due:
            st.warning(f"⚠️ {due} customer(s) need follow-up today or are overdue.")
        if hot:
            st.success(f"🔥 {hot} HOT lead(s) deserve priority calls.")
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================================
# NEW LEAD
# ============================================================
elif menu == "➕ New Lead":
    st.header("➕ Capture New Inquiry")
    st.caption("One record becomes the customer's sales timeline from first inquiry to disbursement.")

    with st.form("new_lead", clear_on_submit=True):
        a,b,c = st.columns(3)
        with a:
            name = st.text_input("Customer Name *")
            phone = st.text_input("Phone Number *")
            nic = st.text_input("NIC")
        with b:
            vehicle_type = st.selectbox("Vehicle Type", ["Car","Three Wheeler","Motorcycle","Other"])
            vehicle = st.text_input("Vehicle / Model")
            vehicle_value = st.number_input("Vehicle Value (Rs.)", min_value=0.0, step=10000.0)
        with c:
            down = st.number_input("Down Payment (Rs.)", min_value=0.0, step=10000.0)
            source = st.selectbox("Lead Source", ["Facebook","WhatsApp","TikTok","LinkedIn","Referral","Existing Customer","Dealer","Broker","Other"])
            urgency = st.selectbox("Purchase Timing", ["Today","This week","This month","Just asking"])
        action_date = st.date_input("Next Action Date", date.today()+timedelta(days=1))
        action = st.selectbox("Next Action", ["Call customer","Send quotation","Request documents","WhatsApp follow-up","Arrange meeting","Check approval"])
        notes = st.text_area("Notes")
        submit = st.form_submit_button("🚀 SAVE & SCORE LEAD", type="primary", use_container_width=True)

    if submit:
        if not name.strip() or not phone.strip():
            st.error("Customer name and phone number are required.")
        else:
            finance = max(0, vehicle_value - down)
            sc = calculate_score(vehicle_value, down, finance, source, urgency, "New")
            add_lead((
                datetime.now().isoformat(timespec="seconds"), name.strip(), clean_phone(phone),
                nic.strip(), vehicle_type, vehicle, vehicle_value, down, finance,
                source, "New", sc, temp(sc), action_date.isoformat(), action, notes
            ))
            st.success(f"Lead saved successfully — {temp(sc)} • Score {sc}/100")
            st.balloons()

# ============================================================
# LEAD INTELLIGENCE
# ============================================================
elif menu == "🧠 Lead Intelligence":
    st.header("🧠 Lead Intelligence")
    if df.empty:
        st.info("Add leads first.")
    else:
        selected = st.selectbox(
            "Select customer",
            df["id"].tolist(),
            format_func=lambda x: f"#{x} • {df.loc[df.id==x,'name'].iloc[0]} • {df.loc[df.id==x,'phone'].iloc[0]}"
        )
        r = df[df.id == selected].iloc[0]
        score_val = int(r["score"])
        st.markdown(f"### {r['temperature']} {r['name']} — **{score_val}/100**")
        a,b,c,d = st.columns(4)
        a.metric("Stage", r["stage"])
        b.metric("Finance", money(r["required_finance"]))
        c.metric("Source", r["source"])
        d.metric("Next Action", r["next_action_date"] or "—")

        st.markdown('<div class="panel"><h3>🎯 Recommended Strategy</h3>', unsafe_allow_html=True)
        if score_val >= 80:
            st.success("HOT lead: call first, confirm exact requirement, then move directly toward quotation/documents.")
        elif score_val >= 60:
            st.warning("WARM lead: clarify vehicle, finance amount and purchase timing, then schedule a specific follow-up.")
        else:
            st.info("COLD lead: nurture, provide useful information and set a future follow-up instead of pushing for an immediate close.")
        st.markdown('</div>', unsafe_allow_html=True)

        note = st.text_area("Add activity note")
        ac1,ac2,ac3 = st.columns(3)
        with ac1:
            if st.button("📞 Logged Call", use_container_width=True):
                add_activity(int(selected),"Call",note)
                st.success("Call logged.")
        with ac2:
            if st.button("💬 WhatsApp Sent", use_container_width=True):
                add_activity(int(selected),"WhatsApp",note)
                st.success("WhatsApp activity logged.")
        with ac3:
            if st.button("🧾 Quotation Sent", use_container_width=True):
                update_lead(int(selected),stage="Quotation",next_action="Quotation follow-up")
                add_activity(int(selected),"Quotation",note)
                st.success("Quotation stage updated.")

        acts = get_activities(int(selected))
        if not acts.empty:
            st.markdown("### 🕒 Customer Timeline")
            st.dataframe(acts[["created_at","activity","note"]], use_container_width=True, hide_index=True)

# ============================================================
# PIPELINE
# ============================================================
elif menu == "📋 Pipeline":
    st.header("📋 Sales Pipeline")
    stages = ["New","Contacted","Quotation","Negotiation","Documents","Approved","Disbursed","Lost"]
    if df.empty:
        st.info("No leads in pipeline.")
    else:
        counts = df["stage"].value_counts()
        cols = st.columns(len(stages))
        for c,s in zip(cols,stages):
            c.metric(s, int(counts.get(s,0)))
        stage = st.selectbox("View stage", stages)
        view = df[df["stage"] == stage]
        if view.empty:
            st.info("No customers at this stage.")
        else:
            st.dataframe(view[["id","name","phone","vehicle","required_finance","temperature","score","next_action_date","next_action"]],
                         use_container_width=True, hide_index=True)

# ============================================================
# CUSTOMERS
# ============================================================
elif menu == "👥 Customers":
    st.header("👥 Customer 360")
    if df.empty:
        st.info("No customers saved yet.")
    else:
        q = st.text_input("🔎 Search name, phone, NIC or vehicle")
        view = df.copy()
        if q:
            mask = False
            for col in ["name","phone","nic","vehicle"]:
                mask = mask | view[col].fillna("").astype(str).str.contains(q,case=False,na=False)
            view = view[mask]
        st.dataframe(view[["id","name","phone","nic","vehicle_type","vehicle","vehicle_value","down_payment",
                           "required_finance","source","stage","temperature","score","next_action_date"]],
                     use_container_width=True, hide_index=True)
        st.download_button("📥 Export Customer Database", view.to_csv(index=False).encode("utf-8"),
                           "leadflow_customers.csv", "text/csv")

# ============================================================
# SMART FINANCE
# ============================================================
elif menu == "🧮 Smart Finance":
    st.header("🧮 Smart Finance Simulator")
    st.caption("Planning estimate only — confirm official company terms before a binding quotation.")
    a,b,c = st.columns(3)
    with a:
        vehicle_type = st.selectbox("Vehicle Type",["Car","Three Wheeler","Motorcycle"])
        value = st.number_input("Vehicle Value", min_value=0.0, value=2500000.0, step=10000.0)
        down = st.number_input("Down Payment", min_value=0.0, value=750000.0, step=10000.0)
    with b:
        max_fin = st.slider("Maximum Finance %",0,100,70)
        lease_share = st.slider("Lease Share of Finance %",0,100,50)
        years = st.selectbox("Period (Years)",[2,3,4,5],index=2)
    with c:
        lease_rate = st.number_input("Lease Rate % p.a.",min_value=0.0,value=24.0,step=.25)
        loan_rate = st.number_input("Loan Rate % p.a.",min_value=0.0,value=26.0,step=.25)
        charges = st.number_input("Insurance / Other Charges",min_value=0.0,step=1000.0)

    finance = max(0,value-down)
    maximum = value*max_fin/100
    if finance > maximum:
        st.error(f"Required finance {money(finance)} exceeds the selected maximum {money(maximum)}.")
    else:
        lease = finance*lease_share/100
        loan = finance-lease
        lease_emi = emi(lease+charges,lease_rate,years)
        loan_emi = emi(loan,loan_rate,max(1,years-1))
        cols=st.columns(4)
        for col,label,val in zip(cols,["Finance","Lease Portion","Loan Portion","Total Monthly"],
                                 [finance,lease,loan,lease_emi+loan_emi]):
            col.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{money(val)}</div></div>',unsafe_allow_html=True)
        st.markdown('<div class="panel"><h3>💡 Customer Option Comparison</h3>',unsafe_allow_html=True)
        rows=[]
        for y in [3,4,5]:
            rows.append({
                "Plan":f"{y} Years",
                "Lease EMI":money(emi(lease+charges,lease_rate,y)),
                "Loan EMI":money(emi(loan,loan_rate,max(1,y-1))),
                "Combined":money(emi(lease+charges,lease_rate,y)+emi(loan,loan_rate,max(1,y-1)))
            })
        st.table(pd.DataFrame(rows))
        st.markdown('</div>',unsafe_allow_html=True)

# ============================================================
# FOLLOW UPS
# ============================================================
elif menu == "📞 Follow-ups":
    st.header("📞 Follow-up Control Room")
    if df.empty:
        st.info("No leads yet.")
    else:
        due = df[(df["next_action_date"].notna()) & (df["next_action_date"] <= today)].copy()
        upcoming = df[(df["next_action_date"].notna()) & (df["next_action_date"] > today)].copy()
        a,b = st.columns(2)
        a.metric("🔥 Due / Overdue",len(due))
        b.metric("📅 Upcoming",len(upcoming))
        if not due.empty:
            st.subheader("🔥 Action Now")
            st.dataframe(due[["id","name","phone","temperature","score","stage","next_action_date","next_action"]],
                         use_container_width=True,hide_index=True)
        else:
            st.success("No overdue follow-ups 🎉")
        if not upcoming.empty:
            st.subheader("📅 Upcoming")
            st.dataframe(upcoming[["id","name","phone","temperature","next_action_date","next_action"]],
                         use_container_width=True,hide_index=True)

# ============================================================
# MESSAGE LAB
# ============================================================
elif menu == "✍️ Message Lab":
    st.header("✍️ Sales Message Lab")
    a,b=st.columns(2)
    with a:
        name=st.text_input("Customer Name","Customer")
        vehicle=st.text_input("Vehicle","vehicle")
        stage=st.selectbox("Purpose",["First Contact","Quotation Follow-up","No Response","Document Request","Appointment","Referral"])
    with b:
        rental=st.number_input("Monthly Rental (optional)",0.0,step=1000.0)
        officer=st.text_input("Sales Officer","Sales Officer")
        tone=st.selectbox("Tone",["Professional","Friendly","Short"])
    messages={
    "First Contact":f"Hi {name}, 👋 ඔබගේ {vehicle} finance inquiry එක සම්බන්ධයෙන් contact වුණේ. ඔබගේ requirement එක share කළොත් suitable payment option එකක් check කරලා දෙන්නම්. — {officer}",
    "Quotation Follow-up":f"Hi {name}, ඔබට ලබාදුන් {vehicle} quotation එක ගැන any questions තියෙනවා නම් මට කියන්න. Estimated monthly rental: {money(rental)}. ඔබට පහසු option එකක් discuss කරමු. — {officer}",
    "No Response":f"Hi {name}, 👋 just following up regarding your {vehicle} finance inquiry. තවම requirement එක තියෙනවා නම් reply එකක් දෙන්න. Suitable option එකක් බලලා දෙන්නම්. — {officer}",
    "Document Request":f"Hi {name}, ඔබගේ {vehicle} finance application එක process කරන්න pending documents ලබාදෙන්න පුළුවන්ද? අවශ්‍ය details මම guide කරන්නම්. — {officer}",
    "Appointment":f"Hi {name}, ඔබට පහසු වෙලාවක් confirm කළොත් {vehicle} finance options ගැන short discussion එකක් arrange කරගන්න පුළුවන්. — {officer}",
    "Referral":f"Hi {name}, 🙏 ඔබ දන්නා vehicle finance අවශ්‍යතාවයක් තියෙන කෙනෙක් ඉන්නවා නම් මාව introduce කරලා දෙන්න. මම ඔවුන්ට suitable option එකක් check කරලා දෙන්නම්. — {officer}"
    }
    st.text_area("Ready-to-send message",messages[stage],height=220)
    st.info("AI upgrade point: connect an LLM API later to personalize messages from customer history, vehicle, stage and objections.")

# ============================================================
# ANALYTICS
# ============================================================
elif menu == "📊 Analytics":
    st.header("📊 Sales Intelligence")
    if df.empty:
        st.info("Analytics will appear after you add leads.")
    else:
        a,b,c,d=st.columns(4)
        a.metric("Total Leads",len(df))
        b.metric("Hot Leads",len(df[df.temperature.str.contains("HOT",na=False)]))
        b2=df["stage"].isin(["Approved","Disbursed"]).sum()
        c.metric("Advanced Deals",int(b2))
        conversion=(b2/len(df)*100) if len(df) else 0
        d.metric("Advanced %",f"{conversion:.1f}%")
        st.markdown('<div class="panel"><h3>📌 Lead Sources</h3>',unsafe_allow_html=True)
        st.bar_chart(df["source"].value_counts())
        st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('<div class="panel"><h3>📈 Pipeline Distribution</h3>',unsafe_allow_html=True)
        st.bar_chart(df["stage"].value_counts())
        st.markdown('</div>',unsafe_allow_html=True)

st.markdown("---")
st.caption("LEADFLOW • Leasing Sales OS • Local database • Planning estimates only. Verify official finance terms before customer commitment.")
