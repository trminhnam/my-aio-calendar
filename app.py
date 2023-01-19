import os
import json
import streamlit as st
import pandas as pd

from gsheetsdb import connect
from datetime import datetime, date

DATE_AND_TIME = 'THỜI_GIAN'
DATE = 'NGÀY'
WEEKDAY = 'THỨ'

# Perform SQL query on the Google Sheet.
# Uses st.cache to only rerun when the query changes or after 10 min.
@st.cache(ttl=600)
def run_query(query):
    conn = connect()
    rows = conn.execute(query, headers=1)
    rows = rows.fetchall()
    return rows

# @st.cache(persist=False,allow_output_mutation=True,show_spinner=True,suppress_st_warning=True)
def load_learned_lectures():
    with open(os.path.join('data', 'learned.json'), 'r') as f:
        learned_lectures = json.load(f)
    return dict(learned_lectures)

def blur_learned_lessons(s):
    """Blur learned lessons with gray color
    Ref: https://discuss.streamlit.io/t/change-background-color-based-on-value/2614

    Args:
        s (_type_): _description_

    Returns:
        _type_: _description_
    """
    return ['background-color: lightgray']*len(s) if learned_lectures.get(s['CÔNG_VIỆC'], False) else ['background-color: white']*len(s)

def display_previous_lectures():
    learned_lectures = load_learned_lectures()
    data = df[
        (df[DATE] < date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day))
        & (df[DATE] > date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day) 
           - pd.Timedelta(days=max_elements))
    ].copy()
    data['LEARNED'] = data['CÔNG_VIỆC'].apply(lambda x: "✅" if learned_lectures.get(x, False) else "❌")

    hide_learned_lectures = st.checkbox('Hide learned lectures')
    if hide_learned_lectures:
        data = data[data['LEARNED'] == '❌']

    st.dataframe(
        data.loc[:, ['NGÀY', 'THỨ', 'CÔNG_VIỆC', 'LEARNED', 'LINK', 'ĐẢM_NHẬN']]
        .style.apply(blur_learned_lessons, axis=1))


st.set_page_config(
    page_title="AIO 2022 Schedule",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="auto",
)

st.title("AIO 2022 Schedule")
st.info('✨ This is a custom Streamlit app that uses Google Sheets as a database. ✨')

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if check_password():
    # load data and preprocessing dataframe
    with st.spinner(f"Loading Google Sheet ... 💫"): 
        sheet_url = st.secrets["private_gsheets_url"]
        rows = run_query(f'SELECT * FROM "{sheet_url}"')
        df = pd.DataFrame(rows,)
        # df.set_index('CÔNG_VIỆC', inplace=True)
        df.drop(columns=['THÁNG', 'TUẦN',], inplace=True)
        df.style.hide_index()
        df[DATE_AND_TIME] = pd.to_datetime(df[DATE_AND_TIME], format=r'%d/%m/%Y %H:%M:%S')
        df[DATE] = pd.to_datetime(df[DATE_AND_TIME], format=r'%d/%m/%Y').dt.date


    next_lectures, previous_lectures = st.tabs(['Next Lectures', 'Previous Lectures'])
    learned_lectures = load_learned_lectures()

    with next_lectures:
        max_elements = st.slider('Max number of days forward', min_value=7, max_value=100, value=14, step=1)
        data = df[(df[DATE] >= date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day))
            & (df[DATE] < date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day) 
                + pd.Timedelta(days=max_elements))
            ].drop(columns=['THỜI_HẠN', "HOÀN_THÀNH", "THỜI_GIAN"]).sort_values(by=DATE)
        st.dataframe(data.loc[:, ['NGÀY', 'THỨ', 'CÔNG_VIỆC', 'LINK', 'ĐẢM_NHẬN']])

    with previous_lectures:
        max_elements = st.slider('Max number of days backward', min_value=7, max_value=100, value=14, step=1)
        data = df[
            (df[DATE] < date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day))
            & (df[DATE] > date(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day) 
            - pd.Timedelta(days=max_elements))
        ].copy()
        data['LEARNED'] = data['CÔNG_VIỆC'].apply(lambda x: "✅" if learned_lectures.get(x, False) else "❌")
        
        selection_list = [item for item in data['CÔNG_VIỆC'].unique()]
        marked_learned = st.selectbox('Select a lecture to take action', selection_list)
        radio = st.radio('Select an action', ['Mark as learned', 'Mark as not learned'])
        action = st.button('Take action')

        if action:
            if radio == 'Mark as learned':
                learned_lectures[marked_learned] = True
                with open(os.path.join('data', 'learned.json'), 'w') as f:
                    json.dump(learned_lectures, f, indent=4)
                display_previous_lectures()
            else:
                learned_lectures[marked_learned] = False
                with open(os.path.join('data', 'learned.json'), 'w') as f:
                    json.dump(learned_lectures, f, indent=4)
                display_previous_lectures()
        else:
            display_previous_lectures()