import os
import requests
import streamlit as st

try:  # `streamlit run demo/streamlit_app.py`
    from course_provider import MockCourseProvider
except ModuleNotFoundError:  # `python -m streamlit run demo.streamlit_app`
    from demo.course_provider import MockCourseProvider

st.set_page_config(page_title="Student Assist", page_icon="🎓", layout="wide")
st.title("🎓 Student Assist")
st.caption("LTI 1.3 launch demo with mock enrolled courses")
api_url = os.environ.get("LTI_BRIDGE_URL", "http://localhost:8000")

if "launch_code" in st.query_params:
    code = st.query_params["launch_code"]
    try:
        response = requests.post(f"{api_url}/lti/exchange", json={"code": code}, timeout=10)
        response.raise_for_status()
        st.session_state.launch = response.json()
    except requests.RequestException as exc:
        st.error(f"Could not complete LTI launch: {exc}")
    st.query_params.clear()

launch = st.session_state.get("launch")
if not launch:
    st.info("Start Student Assist from its registered LTI link in your LMS. The LMS performs the secure login launch.")
    st.code("Login initiation: http://localhost:8000/lti/login\nLaunch callback: http://localhost:8000/lti/launch")
    st.stop()

st.success("Authenticated through LTI 1.3")
st.subheader("User details")
left, right = st.columns(2)
with left:
    st.write("**Name:**", launch.get("name") or "Not provided by Moodle")
    st.write("**Email:**", launch.get("email") or "Not provided by Moodle")
    st.write("**Moodle subject ID:**", launch.get("subject") or "Not provided")
with right:
    st.write("**LTI roles:**", ", ".join(launch.get("roles") or []) or "Not provided")
    st.write("**Course context:**", launch.get("context_title") or "Not provided by Moodle")
    st.write("**Course context ID:**", launch.get("context_id") or "Not provided")

st.subheader("Courses")
courses = MockCourseProvider().list_enrolled_courses(subject=launch["subject"], issuer=launch["issuer"])
if not courses:
    st.warning("No enrolled courses were returned.")
else:
    course = st.selectbox("Course", courses, format_func=lambda item: item.title)
    st.write(course.description)
    section = st.selectbox("Section", course.sections, key=f"section-{course.id}")
    prompt = st.chat_input(f"Ask about {section}")
    if prompt:
        st.chat_message("user").write(prompt)
        st.chat_message("assistant").write(f"Mock response for **{course.title} / {section}**: connect your agent's retrieval and generation service here.")
