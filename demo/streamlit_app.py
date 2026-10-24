import os
import requests
import streamlit as st
import bleach
import traceback

try:  # `streamlit run demo/streamlit_app.py`
    from course_provider import MoodleApiError, MoodleCourseProvider, MockCourseProvider
except ModuleNotFoundError:  # `python -m streamlit run demo.streamlit_app`
    from demo.course_provider import MoodleApiError, MoodleCourseProvider, MockCourseProvider


def render_moodle_html(value: str) -> None:
    """Render Moodle description HTML after removing scripts and unsafe attributes."""
    if value:
        clean = bleach.clean(
            value,
            tags={"p", "br", "div", "span", "strong", "b", "em", "i", "u", "ul", "ol", "li", "a", "h1", "h2", "h3", "h4", "blockquote", "code", "pre", "table", "thead", "tbody", "tr", "th", "td"},
            attributes={"a": ["href", "title"], "th": ["colspan", "rowspan"], "td": ["colspan", "rowspan"]},
            protocols={"http", "https", "mailto"}, strip=True,
        )
        st.html(clean)

st.set_page_config(page_title="Student Assist", page_icon="🎓", layout="wide")
st.title("🎓 Student Assist")
st.caption("LTI 1.3 course launch and Moodle course content preview")
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

base_url = os.getenv("MOODLE_BASE_URL")
ws_token = os.getenv("MOODLE_WS_TOKEN")
if bool(base_url) != bool(ws_token):
    st.error("Configure both MOODLE_BASE_URL and MOODLE_WS_TOKEN, or unset both to use mock course data.")
    st.stop()

using_moodle = bool(base_url and ws_token)
provider = MoodleCourseProvider(base_url, ws_token) if using_moodle else MockCourseProvider()
context_id = launch.get("context_id")
if not context_id:
    st.warning("This LTI launch did not include a course context ID, so course details cannot be loaded.")
    st.stop()

cache_key = f"course:{launch.get('issuer')}:{context_id}:{'moodle' if using_moodle else 'mock'}"
try:
    if cache_key not in st.session_state:
        st.session_state[cache_key] = provider.get_course_by_id(context_id)
    course = st.session_state[cache_key]
except MoodleApiError as exc:
    st.error(str(exc))
    with st.expander("Full Moodle API error trace", expanded=True):
        st.code(traceback.format_exc(), language="text")
        if exc.diagnostic:
            st.caption("Moodle response / request diagnostic (service token redacted)")
            st.code(exc.diagnostic, language="json" if exc.diagnostic.lstrip().startswith("{") else "text")
    st.info("Check the Moodle external service functions, token permissions, course ID mapping, and REST endpoint configuration.")
    st.stop()

st.subheader("Course")
with st.container(border=True):
    st.subheader(course.title)
    if course.shortname:
        st.caption(f"{course.shortname} · Course ID {course.id}")
    render_moodle_html(course.description)
    st.caption(f"{len(course.sections)} sections")
    if st.button("Open course", key=f"open-{course.id}", type="primary"):
        st.session_state.open_course_id = course.id

if st.session_state.get("open_course_id") == course.id:
    st.divider()
    st.header(course.title)
    render_moodle_html(course.description)
    for section in course.sections:
        with st.expander(section.title, expanded=section.is_general):
            render_moodle_html(section.summary)
            if not section.activities:
                st.caption("No visible activities in this section.")
            for activity in section.activities:
                with st.container(border=True):
                    st.write(f"**{activity.name}** · {activity.module_type.replace('_', ' ').title()}")
                    render_moodle_html(activity.description)
                    if activity.files:
                        st.caption("Files: " + ", ".join(activity.files))
                    if activity.url and activity.url.startswith(("https://", "http://")):
                        st.link_button("Open in Moodle", activity.url)

    section_names = [section.title for section in course.sections] or ["Course"]
    section_name = st.selectbox("Ask about section", section_names, key=f"chat-section-{course.id}")
    prompt = st.chat_input(f"Ask about {section_name}")
    if prompt:
        st.chat_message("user").write(prompt)
        st.chat_message("assistant").write(
            f"Mock response for **{course.title} / {section_name}**: connect your agent's retrieval and generation service here."
        )
