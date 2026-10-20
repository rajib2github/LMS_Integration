import os
from student_assist_lti import LtiService, PlatformConfig
from student_assist_lti.fastapi import create_lti_app

platform = PlatformConfig(
    issuer=os.environ.get("LTI_ISSUER", "https://lms.example.edu"),
    client_id=os.environ.get("LTI_CLIENT_ID", "student-assist-client"),
    deployment_id=os.environ.get("LTI_DEPLOYMENT_ID", "deployment-1"),
    authorization_endpoint=os.environ.get("LTI_AUTHORIZATION_ENDPOINT", "https://lms.example.edu/oidc/auth"),
    jwks_uri=os.environ.get("LTI_JWKS_URI", "https://lms.example.edu/.well-known/jwks.json"),
    token_endpoint=os.environ.get("LTI_TOKEN_ENDPOINT"),
)
service = LtiService(platform, os.environ.get("LTI_REDIRECT_URI", "http://localhost:8000/lti/launch"))
app = create_lti_app(service, streamlit_url=os.environ.get("STREAMLIT_URL", "http://localhost:8501"))
