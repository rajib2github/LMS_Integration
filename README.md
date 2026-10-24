# Student Assist LTI 1.3

A reusable Python package and Streamlit demo for launching Student Assist from Moodle or Open edX using LTI 1.3. The package handles OIDC login initiation and validates signed LTI launch tokens. The demo loads the launched Moodle course and its section/module structure through Moodle REST, or shows representative mock course data when Moodle REST settings are absent.

## Architecture

```text
Student opens Student Assist in LMS
  -> LMS OIDC login initiation -> GET or POST /lti/login
  -> platform authorization endpoint
  -> signed id_token form_post -> POST /lti/launch
  -> validate signature, issuer, audience, nonce, version, message type, deployment
  -> one-time code redirects browser to Streamlit
  -> Streamlit exchanges code and reads the signed launch context ID
  -> Moodle REST returns course details and section/activity structure
  -> Streamlit shows a course card, then a General and section-wise course view
  -> section chat invokes AI agent (mock response in this demo)
```

LTI launches are initiated by the LMS. Configure its tool registration with login initiation URL `http://<host>:8000/lti/login`, redirect URI `http://<host>:8000/lti/launch`, and the issuer, client ID, deployment ID, authorization endpoint, and JWKS URL supplied by that registration. Use HTTPS outside local development.

## Build and install the wheel

From the project root with Python 3.10 or later:

```bash
python -m pip install --upgrade build
python -m build --wheel
python -m pip install dist/student_assist_lti-0.1.0-py3-none-any.whl
```

For local demo development, install the project and demo dependencies:

```bash
python -m pip install -e ".[demo]"
```

## Run the demo

In PowerShell, set platform registration values and start the bridge:

```powershell
$env:LTI_ISSUER="https://your-lms.example"
$env:LTI_CLIENT_ID="your-client-id"
$env:LTI_DEPLOYMENT_ID="your-deployment-id"
$env:LTI_AUTHORIZATION_ENDPOINT="https://your-lms.example/oidc/auth"
$env:LTI_JWKS_URI="https://your-lms.example/.well-known/jwks.json"
$env:LTI_REDIRECT_URI="http://localhost:8000/lti/launch"
uvicorn demo.api:app --reload --port 8000
```

Start Streamlit in a second terminal:

```powershell
streamlit run demo/streamlit_app.py
```

Register the public login and launch callback URLs in the LMS and launch Student Assist from a course. Directly opening Streamlit does not authenticate a user. In production, run behind HTTPS and use shared expiring stores such as Redis for OIDC transactions and one-time launch codes. The in-memory stores are for a single-process demo.

To use real Moodle course content, configure a Moodle REST service and set these values before starting Streamlit:

```powershell
$env:MOODLE_BASE_URL="https://moodle.example.edu"
$env:MOODLE_WS_TOKEN="the-token-from-the-restricted-moodle-service"
```

When both are set, the demo calls `core_course_get_courses_by_field` and `core_course_get_contents` using the LTI launch context ID (Moodle's course context ID is normally the course ID). If either setting is missing, the demo uses mock data. The token is sent only from the Streamlit server to Moodle and is not placed in the browser URL or page.

### Moodle REST service setup

An administrator should:

1. Enable web services in **Site administration → Advanced features**.
2. Enable the REST protocol in **Site administration → Server → Web services → Manage protocols**.
3. Create an external service, enable it, and add `core_course_get_courses_by_field` and `core_course_get_contents` as its functions.
4. Create a dedicated, non-administrator Moodle service user; authorize that user for the service and create a token for it.
5. Grant only the capabilities needed to view the intended course content. Confirm the Moodle REST endpoint is reachable by the Student Assist server at `/webservice/rest/server.php`.

Moodle may hide activities according to the service user's permissions. In production, do not use an administrator token: Moodle REST requests run as the token's user, and a broad service account could expose content beyond the learner's access. Enforce learner enrollment and visibility in a trusted backend (or use an appropriate per-learner delegated authorization design) before returning course data. The LTI launch proves the launcher's identity to Student Assist but does not itself authorize Moodle REST calls.

This demo loads the course in the current LTI launch context, not every course the student has enrolled in. LTI does not provide a universal enrolled-course listing API. If Moodle sends an opaque context ID instead of its numeric course ID, add a trusted Moodle-side mapping/custom launch claim and adapt `MoodleCourseProvider.get_course_by_id`; do not trust an arbitrary browser-supplied course ID.

## Package usage

```python
from student_assist_lti import LtiService, PlatformConfig
from student_assist_lti.fastapi import create_lti_app

platform = PlatformConfig(
    issuer="https://lms.example.edu",
    client_id="registered-client-id",
    deployment_id="registered-deployment-id",
    authorization_endpoint="https://lms.example.edu/oidc/auth",
    jwks_uri="https://lms.example.edu/.well-known/jwks.json",
)
service = LtiService(platform, redirect_uri="https://assist.example.com/lti/launch")
app = create_lti_app(service, streamlit_url="https://assist.example.com")
```

`LtiService.begin_login(...)` builds the authorization redirect. `validate_launch(state, id_token)` verifies the launch and returns `LaunchContext`. The FastAPI adapter provides routes and browser handoff; another framework can call the service directly.

## Replace mock data with LMS course APIs

`demo/course_provider.py` defines normalized `Course`, `CourseSection`, and `CourseActivity` records plus `MoodleCourseProvider`. For another LMS, implement `get_course_by_id(context_id)` and map the LMS course structure to those records. Keep API credentials in a secret manager or environment configuration.

LTI 1.3 launch claims do not define a universal API for listing every course a student has enrolled in. Launch context identifies the current course when provided; a complete enrollment list requires an LMS-specific API and appropriate credentials or provisioned service. Moodle and Open edX integrations differ, so this adapter isolates those differences.

## Security and production notes

- The package validates the platform JWT signature against JWKS and checks issuer, audience, nonce, token age, LTI version, resource-link message type, and deployment ID.
- Use HTTPS and a shared transactional store in multi-worker deployments. The sample memory stores are process-local.
- The demo handoff code is opaque, one-time, and short-lived. Add normal application session controls before production use.
- This implementation supports resource-link launches. Add explicit handling for other LTI message types and services only when required by the LMS registration.
