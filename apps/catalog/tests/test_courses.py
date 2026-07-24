import pytest

from apps.accounts.models import Role, User
from apps.catalog.models import Course, Module

pytestmark = pytest.mark.django_db


@pytest.fixture
def instructor_user():
    return User.objects.create_user(email="i@test.com", password="supersecret123",
                                    role=Role.INSTRUCTOR, email_verified=True)


@pytest.fixture
def other_instructor():
    return User.objects.create_user(email="i2@test.com", password="supersecret123",
                                    role=Role.INSTRUCTOR, email_verified=True)


def test_draft_course_hidden_from_public_list(instructor_user):
    Course.objects.create(title="Draft one", instructor=instructor_user)
    from django.test import Client
    r = Client().get("/api/v1/catalog/courses")
    assert r.json() == []


def test_publish_requires_at_least_one_module(instructor_user, client):
    course = Course.objects.create(title="No modules", instructor=instructor_user)
    client.force_login(instructor_user)  # adjust to your auth helper for JWT in tests
    # ... call publish endpoint, assert 400


def test_instructor_cannot_edit_others_course(instructor_user, other_instructor):
    course = Course.objects.create(title="Mine", instructor=instructor_user)
    from apps.catalog.permissions import check_course_owner
    from ninja.errors import HttpError
    with pytest.raises(HttpError):
        check_course_owner(other_instructor, course)


def test_recommended_filters_by_role(instructor_user):
    Course.objects.create(title="For HMO staff", instructor=instructor_user,
                          status=Course.Status.PUBLISHED, target_roles=["hmo_staff"])
    Course.objects.create(title="For grads", instructor=instructor_user,
                          status=Course.Status.PUBLISHED, target_roles=["student_graduate"])
    # assert a user with current_role="hmo_staff" only sees the first