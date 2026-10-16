"""Banking Customer Segmentation - Streamlit dashboard.

Run locally:  streamlit run app.py
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.preprocessing import MinMaxScaler, StandardScaler

DATA_PATH = Path(__file__).parent / "data" / "High_Value_Customer_Identification_Final.xlsx"

SCORE_WEIGHTS = {
    "financial_strength_score": 0.25,
    "transaction_behaviour_score": 0.15,
    "spending_behaviour_score": 0.15,
    "credit_profile_score": 0.15,
    "customer_engagement_score": 0.10,
    "relationship_value_score": 0.10,
    "future_potential_score": 0.10,
}

CLUSTER_FEATURES = [
    "age", "annual_income", "avg_balance", "monthly_transactions", "monthly_spend",
    "credit_score", "loan_amount", "investment_value", "products_used",
    "mobile_app_logins", "years_with_bank", "complaints",
]

SEGMENT_ORDER = ["Standard", "Silver", "Gold", "Premium"]


@st.cache_data
def load_data(path):
    return pd.read_excel(path, sheet_name="Customer_360")


@st.cache_data
def run_pipeline(df, n_clusters):
    df = df.copy()

    # 1. Customer Value Score (Min-Max scale each component to 0-100, then weight)
    scaled = pd.DataFrame(
        MinMaxScaler().fit_transform(df[list(SCORE_WEIGHTS)]) * 100,
        columns=list(SCORE_WEIGHTS), index=df.index,
    )
    df["value_score"] = sum(scaled[c] * w for c, w in SCORE_WEIGHTS.items())
    df["potential_score"] = scaled["future_potential_score"]

    # 2. K-Means on standardised features
    X = StandardScaler().fit_transform(df[CLUSTER_FEATURES])
    df["cluster"] = KMeans(n_clusters=n_clusters, random_state=42, n_init=10).fit_predict(X)

    # Name clusters by average income (lowest -> Standard ... highest -> Premium)
    order = df.groupby("cluster")["annual_income"].mean().sort_values().index
    names = SEGMENT_ORDER if n_clusters == 4 else [f"Group {i + 1}" for i in range(n_clusters)]
    df["kmeans_segment"] = df["cluster"].map(dict(zip(order, names)))

    # 3. Value vs potential quadrants (median split)
    hv = df["value_score"] >= df["value_score"].median()
    hp = df["potential_score"] >= df["potential_score"].median()
    df["opportunity"] = "Low Value - Low Potential"
    df.loc[hv & hp, "opportunity"] = "High Value - High Potential"
    df.loc[hv & ~hp, "opportunity"] = "High Value - Low Potential"
    df.loc[~hv & hp, "opportunity"] = "Low Value - High Potential"

    # 4. Priority inside the Low Value - High Potential group
    mask = df["opportunity"] == "Low Value - High Potential"
    q50, q75 = df.loc[mask, "potential_score"].quantile([0.5, 0.75])
    df["priority"] = "Not Targeted"
    df.loc[mask & (df["potential_score"] >= q75), "priority"] = "High"
    df.loc[mask & (df["potential_score"] >= q50) & (df["potential_score"] < q75), "priority"] = "Medium"
    df.loc[mask & (df["potential_score"] < q50), "priority"] = "Low"
    return df


st.set_page_config(page_title="Banking Customer Segmentation", layout="wide")
st.title("Banking Customer Segmentation")
st.caption("Customer Value Score + K-Means segmentation on 10,000 bank customers")

uploaded = st.sidebar.file_uploader("Upload your own Customer_360 workbook (optional)", type="xlsx")
n_clusters = st.sidebar.slider("Number of K-Means clusters", 2, 8, 4)

try:
    raw = load_data(uploaded if uploaded else DATA_PATH)
except Exception as exc:  # file missing or wrong format
    st.error(f"Could not read the data file: {exc}")
    st.stop()

df = run_pipeline(raw, n_clusters)

# KPI row
spend_share = (
    df.groupby("kmeans_segment")["monthly_spend"].sum() / df["monthly_spend"].sum() * 100
)
top_seg = df.groupby("kmeans_segment")["annual_income"].mean().idxmax()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers", f"{len(df):,}")
c2.metric("Clusters", n_clusters)
c3.metric(f"{top_seg} share of spend", f"{spend_share[top_seg]:.1f}%")
c4.metric("Low value, high potential", f"{(df['opportunity'] == 'Low Value - High Potential').sum():,}")

tab1, tab2, tab3, tab4 = st.tabs(["Segments", "Value vs Potential", "Target list", "Customer lookup"])

with tab1:
    left, right = st.columns(2)
    counts = df["kmeans_segment"].value_counts().reset_index()
    counts.columns = ["segment", "customers"]
    left.plotly_chart(px.bar(counts, x="segment", y="customers", title="Customers per segment"),
                      width="stretch")
    right.plotly_chart(
        px.bar(spend_share.reset_index(name="spend_share_%"), x="kmeans_segment", y="spend_share_%",
               title="Share of total monthly spend (%)"),
        width="stretch",
    )
    st.subheader("Segment profile (averages)")
    st.dataframe(df.groupby("kmeans_segment")[CLUSTER_FEATURES].mean().round(1),
                 width="stretch")

with tab2:
    st.plotly_chart(
        px.scatter(df, x="value_score", y="potential_score", color="opportunity", opacity=0.5,
                   title="Current value vs future potential",
                   labels={"value_score": "Customer Value Score", "potential_score": "Future Potential"}),
        width="stretch",
    )
    st.dataframe(df["opportunity"].value_counts().rename("customers"), width="stretch")

with tab3:
    pick = st.multiselect("Priority", ["High", "Medium", "Low"], default=["High"])
    targets = df[df["priority"].isin(pick)].sort_values("potential_score", ascending=False)
    st.write(f"{len(targets):,} customers")
    cols = ["customer_id", "kmeans_segment", "priority", "potential_score", "value_score",
            "annual_income", "avg_balance", "monthly_spend", "investment_value", "products_used"]
    st.dataframe(targets[cols].round(1), width="stretch", hide_index=True)
    st.download_button("Download target list (CSV)", targets[cols].to_csv(index=False),
                       "target_customers.csv", "text/csv")

with tab4:
    cid = st.selectbox("Customer ID", df["customer_id"])
    row = df[df["customer_id"] == cid].iloc[0]
    a, b, c = st.columns(3)
    a.metric("Segment", row["kmeans_segment"])
    b.metric("Value score", f"{row['value_score']:.1f}")
    c.metric("Potential score", f"{row['potential_score']:.1f}")
    st.write(f"Opportunity group: **{row['opportunity']}** | Priority: **{row['priority']}**")
    st.dataframe(row[CLUSTER_FEATURES].to_frame("value"), width="stretch")
