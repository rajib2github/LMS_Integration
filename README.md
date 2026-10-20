# Student Assist LTI 1.3

A reusable Python package and Streamlit demo for launching Student Assist from Moodle or Open edX using LTI 1.3. The package handles OIDC login initiation and validates signed LTI launch tokens. The demo displays mock courses and section chat panels.

## Architecture

```text
Student opens Student Assist in LMS
  -> LMS OIDC login initiation -> GET or POST /lti/login
  -> platform authorization endpoint
  -> signed id_token form_post -> POST /lti/launch
  -> validate signature, issuer, audience, nonce, version, message type, deployment
  -> one-time code redirects browser to Streamlit
  -> Streamlit exchanges code and lists courses through CourseProvider
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

The UI calls `CourseProvider.list_enrolled_courses(subject, issuer)`. Implement that method in `demo/course_provider.py` with your LMS API, map the response to normalized `Course` objects, and replace `MockCourseProvider` in `demo/streamlit_app.py` with your implementation. Keep API credentials in a secret manager or environment configuration.

LTI 1.3 launch claims do not define a universal API for listing every course a student has enrolled in. Launch context identifies the current course when provided; a complete enrollment list requires an LMS-specific API and appropriate credentials or provisioned service. Moodle and Open edX integrations differ, so this adapter isolates those differences.

## Security and production notes

- The package validates the platform JWT signature against JWKS and checks issuer, audience, nonce, token age, LTI version, resource-link message type, and deployment ID.
- Use HTTPS and a shared transactional store in multi-worker deployments. The sample memory stores are process-local.
- The demo handoff code is opaque, one-time, and short-lived. Add normal application session controls before production use.
- This implementation supports resource-link launches. Add explicit handling for other LTI message types and services only when required by the LMS registration.
