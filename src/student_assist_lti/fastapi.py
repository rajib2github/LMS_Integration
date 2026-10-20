"""FastAPI adapter for LTI login, launch callback, and demo one-time code exchange."""
from urllib.parse import urlencode
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from .service import LtiError, LtiService
from .store import MemoryLaunchStore


def create_lti_app(service: LtiService, *, streamlit_url: str,
                   launch_store: MemoryLaunchStore | None = None) -> FastAPI:
    app = FastAPI(title="Student Assist LTI bridge")
    launches = launch_store or MemoryLaunchStore()

    @app.api_route("/lti/login", methods=["GET", "POST"])
    async def login(request: Request):
        # Platforms may send OIDC login-initiation parameters in either the
        # query string or an application/x-www-form-urlencoded POST body.
        params = dict(request.query_params)
        if request.method == "POST":
            try:
                form = await request.form()
            except Exception as exc:
                raise HTTPException(400, "Unable to read login initiation form") from exc
            params.update({key: str(value) for key, value in form.items()})
        try:
            url = service.begin_login(login_hint=params.get("login_hint", ""),
                lti_message_hint=params.get("lti_message_hint", ""),
                iss=params.get("iss"),
                target_link_uri=params.get("target_link_uri"), client_id=params.get("client_id"))
        except LtiError as exc:
            raise HTTPException(400, str(exc)) from exc
        return RedirectResponse(url, status_code=302)

    @app.post("/lti/launch")
    async def launch(state: str = Form(...), id_token: str = Form(...)):
        try:
            ctx = service.validate_launch(state=state, id_token=id_token)
        except LtiError as exc:
            raise HTTPException(401, str(exc)) from exc
        code = launches.create({"issuer": ctx.issuer, "client_id": ctx.client_id,
            "deployment_id": ctx.deployment_id, "subject": ctx.subject,
            "name": ctx.name, "email": ctx.email, "roles": list(ctx.roles),
            "context_id": ctx.context_id, "context_title": ctx.context_title,
            "resource_link_id": ctx.resource_link_id})
        return RedirectResponse(f"{streamlit_url}?{urlencode({'launch_code': code})}", status_code=303)

    @app.post("/lti/exchange")
    async def exchange(payload: dict):
        code = payload.get("code")
        result = launches.consume(code) if isinstance(code, str) else None
        if not result:
            raise HTTPException(401, "Invalid or expired launch code")
        return result

    return app
