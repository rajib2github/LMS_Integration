"""Normalized course models and Moodle REST API adapter for the demo."""
from dataclasses import dataclass, field
import json

import requests


@dataclass
class CourseActivity:
    name: str
    module_type: str = "activity"
    description: str = ""
    url: str = ""
    files: list[str] = field(default_factory=list)


@dataclass
class CourseSection:
    id: str
    number: int
    title: str
    summary: str = ""
    activities: list[CourseActivity] = field(default_factory=list)
    is_general: bool = False


@dataclass
class Course:
    id: str
    title: str
    shortname: str = ""
    description: str = ""
    sections: list[CourseSection] = field(default_factory=list)


class MoodleApiError(RuntimeError):
    """Moodle rejected a REST request or returned an unexpected response."""

    def __init__(self, message: str, diagnostic: str = ""):
        super().__init__(message)
        self.diagnostic = diagnostic


class MoodleCourseProvider:
    """Fetch a launched Moodle course and its visible section/module structure."""

    def __init__(self, base_url: str, token: str, timeout: float = 15):
        self.endpoint = f"{base_url.rstrip('/')}/webservice/rest/server.php"
        self.token = token
        self.timeout = timeout

    def _call(self, function: str, **params):
        data = {
            "wstoken": self.token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
            **params,
        }
        try:
            response = requests.post(self.endpoint, data=data, timeout=self.timeout)
        except requests.RequestException as exc:
            diagnostic = self._redact(f"{type(exc).__name__}: {exc}")
            raise MoodleApiError(f"Moodle API request failed ({function}): {exc}", diagnostic) from exc

        if not response.ok:
            body = response.text or "<empty response body>"
            diagnostic = self._redact(f"HTTP {response.status_code} {response.reason}\n\n{body}")
            raise MoodleApiError(f"Moodle API request failed ({function}): HTTP {response.status_code}", diagnostic)
        try:
            result = response.json()
        except ValueError as exc:
            diagnostic = self._redact(f"Response was not valid JSON. HTTP {response.status_code}\n\n{response.text}")
            raise MoodleApiError(f"Moodle API returned invalid JSON ({function}).", diagnostic) from exc
        if isinstance(result, dict) and (result.get("exception") or result.get("errorcode")):
            message = result.get("message") or result.get("errorcode") or "Unknown Moodle API error"
            diagnostic = self._redact(json.dumps(result, ensure_ascii=False, indent=2))
            raise MoodleApiError(f"Moodle API rejected {function}: {message}", diagnostic)
        return result

    def _redact(self, value: str) -> str:
        """Avoid displaying the configured bearer token if Moodle echoes request data."""
        return value.replace(self.token, "[REDACTED MOODLE TOKEN]") if self.token else value

    def get_course_by_id(self, context_id: str) -> Course:
        try:
            course_id = int(context_id)
            if course_id < 1:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise MoodleApiError(
                "The LTI context ID is not a numeric Moodle course ID. Configure a Moodle-side mapping or pass the Moodle course ID as a validated custom LTI claim."
            ) from exc

        result = self._call("core_course_get_courses_by_field", field="id", value=str(course_id))
        courses = result.get("courses", []) if isinstance(result, dict) else []
        if not courses:
            raise MoodleApiError(f"Moodle returned no course for course ID {course_id}.")
        raw_course = courses[0]
        raw_sections = self._call("core_course_get_contents", courseid=course_id)
        sections = []
        if isinstance(raw_sections, list):
            for raw in raw_sections:
                if raw.get("uservisible") is False or raw.get("visible") == 0:
                    continue
                number = int(raw.get("section", 0) or 0)
                activities = []
                for module in raw.get("modules", []):
                    if module.get("uservisible") is False or module.get("visible") == 0:
                        continue
                    activities.append(CourseActivity(
                        name=module.get("name") or "Untitled activity",
                        module_type=module.get("modname") or "activity",
                        description=module.get("description") or "",
                        url=module.get("url") or "",
                        files=[item.get("filename", "") for item in module.get("contents", []) if item.get("filename")],
                    ))
                sections.append(CourseSection(
                    id=str(raw.get("id", number)), number=number,
                    title=raw.get("name") or ("General" if number == 0 else f"Section {number}"),
                    summary=raw.get("summary") or "", activities=activities, is_general=(number == 0),
                ))
        return Course(
            id=str(course_id), title=raw_course.get("fullname") or raw_course.get("shortname") or f"Course {course_id}",
            shortname=raw_course.get("shortname") or "", description=raw_course.get("summary") or "", sections=sections,
        )


class MockCourseProvider:
    """A representative course tree used when Moodle REST credentials are absent."""
    def get_course_by_id(self, context_id: str) -> Course:
        return Course(
            id=str(context_id or "demo-course"), title="Introduction to Biology", shortname="BIO101",
            description="<p>Foundations of living systems, from cells to ecosystems.</p>",
            sections=[
                CourseSection("general", 0, "General", "<p>Welcome. Start with the course guide.</p>", [
                    CourseActivity("Course guide", "page", "<p>How to use this course.</p>")
                ], True),
                CourseSection("cells", 1, "Cell biology", "<p>Study cell structure and function.</p>", [
                    CourseActivity("Cell structure reading", "resource", "<p>Read the introductory material.</p>", files=["cell_structure.pdf"]),
                    CourseActivity("Cell biology discussion", "forum", "<p>Share one question from the reading.</p>"),
                ]),
                CourseSection("genetics", 2, "Genetics", "<p>Explore inheritance and gene expression.</p>", [
                    CourseActivity("Genetics quiz", "quiz", "<p>Check your understanding.</p>")
                ]),
            ],
        )
