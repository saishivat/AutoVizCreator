import streamlit as st
import pandas as pd
import io
import plotly.express as px
from openai import OpenAI
import json

# ----------------------------
# Page Configuration
# ----------------------------
st.set_page_config(
    page_title="Auto Data Visualization Generator",
    page_icon="📊",
    layout="wide"
)

# ----------------------------
# API Key and OpenAI Client
# ----------------------------
# Attempt to get the key from Streamlit's secrets management
try:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except (FileNotFoundError, KeyError):
    st.sidebar.warning("OpenAI API key not found. Please enter it below to use the app.", icon="⚠️")
    OPENAI_API_KEY = st.sidebar.text_input("Enter your OpenAI API Key:", type="password")

if not OPENAI_API_KEY:
    st.info("Please provide your OpenAI API key in the sidebar to begin.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
# Initialize Session State
# ----------------------------
# This prevents the app from losing data during user interactions
if "cleaned_df" not in st.session_state:
    st.session_state.cleaned_df = None
if "ai_suggestions" not in st.session_state:
    st.session_state.ai_suggestions = ""
if "suggested_chart" not in st.session_state:
    st.session_state.suggested_chart = "bar" # Default chart type

# ----------------------------
# Sidebar for Data Input
# ----------------------------
st.sidebar.title("Data Input")
st.sidebar.markdown("Paste your messy data and let the AI do the heavy lifting.")

SAMPLE_DATA = """
Monthly Product Sales - 2025
Product A, Jan, $12,500
Product B, Jan, $18,000
Product A, Feb, 14,200 USD
Product B, Feb, $19,500
Product A, Mar, $16,000
Product B, March, $22,100
"""

if st.sidebar.button("Load Sample Data"):
    st.session_state.raw_data = SAMPLE_DATA
else:
    st.session_state.raw_data = st.session_state.get("raw_data", "")

raw_data = st.sidebar.text_area(
    "Paste your data here:",
    value=st.session_state.raw_data,
    height=250,
    key="raw_data_input"
)

if st.sidebar.button("✨ Clean & Visualize Data", type="primary"):
    if not raw_data:
        st.sidebar.warning("Please paste some data first.")
    else:
        with st.spinner("🔄 AI is cleaning and structuring your data..."):
            try:
                # AI call to clean data and suggest a chart type
                prompt = f"""
                You are an expert data cleaning assistant. Your tasks are:
                1.  Clean the provided messy data, creating clear headers and a consistent format.
                2.  Convert the cleaned data into a valid CSV string.
                3.  Suggest the most appropriate chart type from ["bar", "line", "scatter", "pie", "area"].
                4.  Return ONLY a single valid JSON object with the structure:
                {{"csv": "<cleaned_csv_string>", "chart": "<suggested_chart_type>"}}

                User data: ```{raw_data}```
                """
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                
                ai_output = json.loads(response.choices[0].message.content)
                st.session_state.cleaned_df = pd.read_csv(io.StringIO(ai_output["csv"]))
                st.session_state.suggested_chart = ai_output["chart"].lower()
                st.session_state.ai_suggestions = "" # Reset suggestions for new data
            except Exception as e:
                st.error(f"❌ Failed to clean data: {e}")
                st.session_state.cleaned_df = None

# ----------------------------
# Main App UI
# ----------------------------
st.title("📊 AI Data-to-Chart Generator")

if st.session_state.cleaned_df is None:
    st.info("Paste your data in the sidebar and click 'Clean & Visualize Data' to start.")
else:
    df = st.session_state.cleaned_df
    tab1, tab2 = st.tabs(["📈 Visualization & Insights", "⚙️ Data & Configuration"])

    with tab2:
        st.subheader("🧹 Cleaned Data")
        st.dataframe(df, use_container_width=True)
        
        st.subheader("🎨 Chart Controls")
        col_config1, col_config2 = st.columns(2)
        with col_config1:
            chart_options = ["bar", "line", "scatter", "pie", "area"]
            try:
                default_index = chart_options.index(st.session_state.suggested_chart)
            except ValueError:
                default_index = 0
            
            selected_chart = st.radio(
                "Chart Type:", options=chart_options, index=default_index, horizontal=True, key="chart_type"
            )
        
        if len(df.columns) > 1:
            with col_config2:
                 x_axis = st.selectbox("X-Axis", options=df.columns, index=0, key="x_axis")
                 y_axis = st.selectbox("Y-Axis", options=df.columns, index=1, key="y_axis")
            
            chart_title = st.text_input("Chart Title", value=f"{st.session_state.y_axis} by {st.session_state.x_axis}", key="chart_title")
        else:
            st.warning("Data has only one column. Cannot create a 2D chart.")

    with tab1:
        # --- Generate and display chart ---
        if len(df.columns) > 1:
            try:
                if selected_chart == "bar":
                    fig = px.bar(df, x=x_axis, y=y_axis, title=chart_title)
                elif selected_chart == "line":
                    fig = px.line(df, x=x_axis, y=y_axis, title=chart_title)
                elif selected_chart == "scatter":
                    fig = px.scatter(df, x=x_axis, y=y_axis, title=chart_title)
                elif selected_chart == "area":
                    fig = px.area(df, x=x_axis, y=y_axis, title=chart_title)
                elif selected_chart == "pie":
                    fig = px.pie(df, names=x_axis, values=y_axis, title=chart_title)
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"❌ Failed to generate chart: {e}")
        
        st.markdown("---")
        
        # --- AI Suggestions Section ---
        if st.button("💡 Get AI Suggestions"):
            with st.spinner("🧠 AI is analyzing your data for insights..."):
                try:
                    data_string = df.to_string()
                    prompt = f"""
                    You are a helpful business analyst. Based on the following data, provide 2-3 simple, actionable suggestions to improve the outcome (e.g., increase sales, find trends).
                    Format your response as a concise markdown list. Be brief and to the point.

                    Data:
                    ```
                    {data_string}
                    ```
                    """
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.5
                    )
                    st.session_state.ai_suggestions = response.choices[0].message.content
                except Exception as e:
                    st.session_state.ai_suggestions = f"An error occurred: {e}"

        if st.session_state.ai_suggestions:
            st.success("**AI-Powered Suggestions:**")
            st.markdown(st.session_state.ai_suggestions)
