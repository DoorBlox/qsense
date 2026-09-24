import os
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Q-SENSE",
    page_icon="📊",
    layout="wide"
)

# =========================================================
# SETTINGS
# =========================================================

DEMO_DIR = "demo_data"
ANALYTICS_DIR = "analytics"

# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data
def load_data():

    sessions = pd.read_csv(
        os.path.join(DEMO_DIR, "sessions.csv")
    )

    snapshots = pd.read_csv(
        os.path.join(DEMO_DIR, "queue_snapshots.csv"),
        parse_dates=["timestamp"]
    )

    events = pd.read_csv(
        os.path.join(DEMO_DIR, "queue_events.csv"),
        parse_dates=["timestamp"]
    )

    meals = pd.read_csv(
        os.path.join(DEMO_DIR, "meal_log.csv")
    )

    validation = pd.read_csv(
        os.path.join(DEMO_DIR, "manual_validation.csv")
    )

    session_metrics = pd.read_csv(
        os.path.join(
            ANALYTICS_DIR,
            "session_metrics.csv"
        ),
        parse_dates=["peak_time"]
    )

    meal_summary = pd.read_csv(
        os.path.join(
            ANALYTICS_DIR,
            "meal_period_summary.csv"
        )
    )

    menu_summary = pd.read_csv(
        os.path.join(
            ANALYTICS_DIR,
            "menu_summary.csv"
        )
    )

    weekday_summary = pd.read_csv(
        os.path.join(
            ANALYTICS_DIR,
            "weekday_summary.csv"
        )
    )

    validation_summary = pd.read_csv(
        os.path.join(
            ANALYTICS_DIR,
            "validation_summary.csv"
        )
    )

    return (
        sessions,
        snapshots,
        events,
        meals,
        validation,
        session_metrics,
        meal_summary,
        menu_summary,
        weekday_summary,
        validation_summary
    )


(
    sessions,
    snapshots,
    events,
    meals,
    validation,
    session_metrics,
    meal_summary,
    menu_summary,
    weekday_summary,
    validation_summary
) = load_data()

# =========================================================
# TITLE
# =========================================================

st.title("Q-SENSE")

st.caption(
    "Smart Cafeteria Queue Sensing and Evaluation System"
)

st.warning(
    "⚠️ DEMONSTRATION MODE — all displayed values are "
    "synthetic proof-of-concept data, not field measurements."
)

# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.header("Q-SENSE Controls")

meal_options = [
    "All",
    "Breakfast",
    "Lunch",
    "Dinner"
]

selected_meal = st.sidebar.selectbox(
    "Meal period",
    meal_options
)

if selected_meal != "All":

    filtered_sessions = session_metrics[
        session_metrics["meal_period"]
        == selected_meal.lower()
    ].copy()

else:

    filtered_sessions = session_metrics.copy()


filtered_sessions = filtered_sessions.sort_values(
    "date"
)

session_options = (
    filtered_sessions["session_id"]
    .tolist()
)

selected_session = st.sidebar.selectbox(
    "Session",
    session_options,
    index=len(session_options) - 1
)

# =========================================================
# GET SELECTED SESSION
# =========================================================

selected_metrics = session_metrics[
    session_metrics["session_id"]
    == selected_session
].iloc[0]

selected_snapshots = snapshots[
    snapshots["session_id"]
    == selected_session
].sort_values("timestamp")

selected_events = events[
    events["session_id"]
    == selected_session
].sort_values("timestamp")

meal_period = selected_metrics[
    "meal_period"
]

menu_id = selected_metrics.get(
    "menu_id",
    "Unknown"
)

# =========================================================
# SESSION HEADER
# =========================================================

st.subheader(
    f"{selected_metrics['date']} — "
    f"{meal_period.upper()}"
)

menu_name = ""

if pd.notna(menu_id):

    matching_menu = meals[
        meals["menu_id"] == menu_id
    ]

    if not matching_menu.empty:

        m = matching_menu.iloc[0]

        menu_name = (
            f"{m['staple']} + "
            f"{m['animal_protein']}"
        )

        st.write(
            f"**Menu:** {menu_id} — {menu_name}"
        )

# =========================================================
# TOP METRICS
# =========================================================

current_queue = int(
    selected_snapshots.iloc[-1]["queue_count"]
)

peak_queue = int(
    selected_metrics["peak_queue"]
)

avg_wait_min = (
    selected_metrics["mean_wait_seconds"]
    / 60
)

served = int(
    selected_metrics["total_served"]
)

throughput = (
    selected_metrics[
        "mean_throughput_per_min"
    ]
)

burden = (
    selected_metrics[
        "queue_burden_person_min"
    ]
)

col1, col2, col3, col4, col5, col6 = st.columns(6)

col1.metric(
    "Current queue",
    f"{current_queue}"
)

col2.metric(
    "Peak queue",
    f"{peak_queue}"
)

col3.metric(
    "Avg wait",
    f"{avg_wait_min:.1f} min"
)

col4.metric(
    "Served",
    f"{served}"
)

col5.metric(
    "Avg throughput",
    f"{throughput:.1f}/min"
)

col6.metric(
    "Queue burden",
    f"{burden:.0f} person-min"
)

st.divider()

# =========================================================
# TABS
# =========================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "Session",
        "Meal Patterns",
        "Menu Analytics",
        "Week Patterns",
        "Validation"
    ]
)

# =========================================================
# TAB 1 — SESSION
# =========================================================

with tab1:

    st.subheader(
        "Queue Throughout the Meal"
    )

    plot_data = selected_snapshots.copy()

    plot_data["time"] = (
        plot_data["timestamp"]
        .dt.strftime("%H:%M")
    )

    fig = px.line(
        plot_data,
        x="timestamp",
        y="queue_count",
        markers=False,
        labels={
            "timestamp": "Time",
            "queue_count": "Students in queue"
        }
    )

    fig.update_layout(
        height=420,
        xaxis_title="Time",
        yaxis_title="Queue length",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ---------------------------------------------
    # More statistics
    # ---------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Mean queue",
        f"{selected_metrics['mean_queue']:.1f}"
    )

    c2.metric(
        "Median queue",
        f"{selected_metrics['median_queue']:.1f}"
    )

    c3.metric(
        "95th percentile",
        f"{selected_metrics['p95_queue']:.1f}"
    )

    c4.metric(
        "Abandonment",
        f"{selected_metrics['abandonment_rate_pct']:.1f}%"
    )

    # ---------------------------------------------
    # Peak time
    # ---------------------------------------------

    peak_time = pd.to_datetime(
        selected_metrics["peak_time"]
    )

    st.info(
        f"Peak queue occurred at "
        f"**{peak_time.strftime('%H:%M:%S')}**, "
        f"with **{peak_queue} students**."
    )

    # ---------------------------------------------
    # Events
    # ---------------------------------------------

    st.subheader(
        "Queue Events"
    )

    event_display = (
        selected_events[
            [
                "timestamp",
                "track_id",
                "event",
                "wait_seconds",
                "queue_count"
            ]
        ]
        .tail(30)
        .copy()
    )

    event_display[
        "timestamp"
    ] = event_display[
        "timestamp"
    ].dt.strftime(
        "%H:%M:%S"
    )

    st.dataframe(
        event_display,
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# TAB 2 — MEAL PATTERNS
# =========================================================

with tab2:

    st.subheader(
        "Breakfast vs Lunch vs Dinner"
    )

    order = [
        "breakfast",
        "lunch",
        "dinner"
    ]

    meal_chart = (
        meal_summary
        .set_index("meal_period")
        .reindex(order)
        .reset_index()
    )

    fig = px.bar(
        meal_chart,
        x="meal_period",
        y="mean_peak_queue",
        labels={
            "meal_period": "Meal period",
            "mean_peak_queue":
                "Average peak queue"
        }
    )

    fig.update_layout(
        height=400
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ---------------------------------------------
    # Waiting time
    # ---------------------------------------------

    fig_wait = px.bar(
        meal_chart,
        x="meal_period",
        y=(
            meal_chart[
                "mean_wait_seconds"
            ] / 60
        ),
        labels={
            "meal_period":
                "Meal period",
            "y":
                "Average waiting time (min)"
        }
    )

    fig_wait.update_layout(
        height=400,
        yaxis_title=
            "Average waiting time (min)"
    )

    st.plotly_chart(
        fig_wait,
        use_container_width=True
    )

    st.dataframe(
        meal_summary,
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# TAB 3 — MENU ANALYTICS
# =========================================================

with tab3:

    st.subheader(
        "Repeated Menu Demand"
    )

    menu_ranked = (
        menu_summary
        .sort_values(
            "mean_peak_uplift_pct",
            ascending=False
        )
        .copy()
    )

    menu_ranked[
        "menu_label"
    ] = (
        menu_ranked["menu_id"]
        + " | "
        + menu_ranked["staple"].fillna("")
        + " + "
        + menu_ranked[
            "animal_protein"
        ].fillna("")
    )

    fig_menu = px.bar(
        menu_ranked,
        x="menu_label",
        y="mean_peak_uplift_pct",
        labels={
            "menu_label": "Menu",
            "mean_peak_uplift_pct":
                "Peak demand vs meal baseline (%)"
        }
    )

    fig_menu.add_hline(
        y=0,
        line_dash="dash"
    )

    fig_menu.update_layout(
        height=480,
        xaxis_tickangle=-35
    )

    st.plotly_chart(
        fig_menu,
        use_container_width=True
    )

    st.caption(
        "Positive values indicate a higher average "
        "peak queue than the baseline for that meal period."
    )

    # ---------------------------------------------
    # Menu selector
    # ---------------------------------------------

    menu_choice = st.selectbox(
        "Inspect a menu",
        menu_ranked["menu_id"].tolist()
    )

    m = menu_summary[
        menu_summary["menu_id"]
        == menu_choice
    ].iloc[0]

    st.subheader(
        f"{menu_choice}"
    )

    st.write(
        f"**{m['staple']} + "
        f"{m['animal_protein']}**"
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "Occurrences",
        int(m["occurrences"])
    )

    b.metric(
        "Avg peak",
        f"{m['mean_peak_queue']:.1f}"
    )

    c.metric(
        "Demand uplift",
        f"{m['mean_peak_uplift_pct']:+.1f}%"
    )

    d.metric(
        "Avg wait",
        f"{m['mean_wait_seconds']/60:.1f} min"
    )

    st.dataframe(
        menu_ranked[
            [
                "menu_id",
                "meal_period",
                "staple",
                "animal_protein",
                "occurrences",
                "mean_peak_queue",
                "mean_peak_uplift_pct",
                "mean_wait_seconds",
                "mean_served"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

# =========================================================
# TAB 4 — WEEK PATTERNS
# =========================================================

with tab4:

    st.subheader(
        "Queue Demand by Weekday"
    )

    fig_weekday = px.bar(
        weekday_summary,
        x="weekday",
        y="mean_peak_queue",
        labels={
            "weekday":
                "Weekday",
            "mean_peak_queue":
                "Average peak queue"
        }
    )

    fig_weekday.update_layout(
        height=420
    )

    st.plotly_chart(
        fig_weekday,
        use_container_width=True
    )

    # ---------------------------------------------
    # Weekday × meal heatmap
    # ---------------------------------------------

    st.subheader(
        "Weekday × Meal Heatmap"
    )

    heat_data = (
        session_metrics
        .pivot_table(
            index="weekday",
            columns="meal_period",
            values="peak_queue",
            aggfunc="mean"
        )
    )

    weekday_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    heat_data = heat_data.reindex(
        weekday_order
    )

    heat_data = heat_data[
        [
            c
            for c in [
                "breakfast",
                "lunch",
                "dinner"
            ]
            if c in heat_data.columns
        ]
    ]

    heatmap = go.Figure(
        data=go.Heatmap(
            z=heat_data.values,
            x=[
                x.capitalize()
                for x in heat_data.columns
            ],
            y=heat_data.index,
            text=heat_data.round(1).values,
            texttemplate="%{text}",
            hovertemplate=(
                "%{y}<br>"
                "%{x}<br>"
                "Avg peak: %{z:.1f}"
                "<extra></extra>"
            )
        )
    )

    heatmap.update_layout(
        height=480,
        xaxis_title="Meal",
        yaxis_title="Weekday"
    )

    st.plotly_chart(
        heatmap,
        use_container_width=True
    )

# =========================================================
# TAB 5 — VALIDATION
# =========================================================

with tab5:

    st.subheader(
        "Q-SENSE Instrument Validation"
    )

    st.warning(
        "These validation results are currently "
        "synthetic and demonstrate the proposed "
        "validation workflow only."
    )

    v = validation_summary.iloc[0]

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "MAE",
        f"{v['MAE_people']:.3f}"
    )

    c2.metric(
        "RMSE",
        f"{v['RMSE_people']:.3f}"
    )

    c3.metric(
        "Within ±1",
        f"{v['within_1_pct']:.1f}%"
    )

    c4.metric(
        "Mean bias",
        f"{v['mean_bias_people']:+.3f}"
    )

    # ---------------------------------------------
    # Actual vs detected
    # ---------------------------------------------

    fig_validation = px.scatter(
        validation,
        x="actual_count",
        y="detected_count",
        labels={
            "actual_count":
                "Manual count",
            "detected_count":
                "Q-SENSE count"
        }
    )

    max_value = max(
        validation["actual_count"].max(),
        validation["detected_count"].max()
    )

    fig_validation.add_trace(
        go.Scatter(
            x=[0, max_value],
            y=[0, max_value],
            mode="lines",
            name="Perfect agreement",
            line=dict(
                dash="dash"
            )
        )
    )

    fig_validation.update_layout(
        height=500
    )

    st.plotly_chart(
        fig_validation,
        use_container_width=True
    )

    st.write(
        f"""
        **Validation observations:** {int(v['observations'])}

        - Exactly correct: **{v['exact_pct']:.1f}%**
        - Within ±1 student: **{v['within_1_pct']:.1f}%**
        - Within ±2 students: **{v['within_2_pct']:.1f}%**
        """
    )

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Q-SENSE Proof of Concept | "
    "Computer Vision + Multi-Object Tracking | "
    "Synthetic demonstration dataset"
)