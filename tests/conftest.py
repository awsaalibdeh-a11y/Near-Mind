import pytest

from nearmind.api import create_app
from nearmind.config import Settings
from nearmind.llm import FakeModel
from nearmind.world import World
from datetime import datetime


@pytest.fixture()
def settings() -> Settings:
    return Settings(start_time=datetime(2026, 11, 14, 19, 0))


@pytest.fixture()
def world(settings) -> World:
    w = World.sandbox(settings)
    w.reply_script = {}
    return w


@pytest.fixture()
def app(settings):
    app = create_app(settings, model=FakeModel())
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def world_from_app(app):
    return app.extensions["nearmind"].world
