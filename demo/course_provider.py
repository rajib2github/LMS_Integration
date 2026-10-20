"""Course source adapter. Replace MockCourseProvider with an LMS API implementation."""
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Course:
    id: str
    title: str
    description: str
    sections: list[str]


class CourseProvider(Protocol):
    def list_enrolled_courses(self, *, subject: str, issuer: str) -> list[Course]: ...


class MockCourseProvider:
    def list_enrolled_courses(self, *, subject: str, issuer: str) -> list[Course]:
        return [
            Course("BIO101", "Introduction to Biology", "Foundations of living systems.", ["Cell biology", "Genetics", "Evolution"]),
            Course("CS204", "Data Structures", "Core structures and algorithms.", ["Arrays and lists", "Trees", "Graphs"]),
        ]


class LmsApiCourseProvider:
    """Implement LMS-specific enrollment lookup and map results to Course records."""
    def __init__(self, api_base_url: str, access_token: str):
        self.api_base_url, self.access_token = api_base_url.rstrip("/"), access_token

    def list_enrolled_courses(self, *, subject: str, issuer: str) -> list[Course]:
        raise NotImplementedError("LTI launch alone has no universal full-course-list API; implement the LMS enrollment API here.")
