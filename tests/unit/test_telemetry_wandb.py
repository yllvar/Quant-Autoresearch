import pytest
import os
from unittest.mock import MagicMock, patch
from utils.telemetry import TelemetryProvider

@pytest.fixture
def mock_wandb():
    with patch("utils.telemetry.wandb") as mock:
        yield mock

def test_telemetry_disabled_with_no_key(mock_wandb):
    with patch.dict(os.environ, {}, clear=True):
        provider = TelemetryProvider()
        assert provider.api_key is None
        assert provider.enabled is False

def test_telemetry_initialization_success(mock_wandb):
    with patch.dict(os.environ, {"WANDB_API_KEY": "test_key"}):
        provider = TelemetryProvider()
        assert provider.api_key == "test_key"
        assert provider.enabled is True
        mock_wandb.login.assert_called_with(key="test_key")

def test_start_run(mock_wandb):
    with patch.dict(os.environ, {"WANDB_API_KEY": "test_key"}):
        provider = TelemetryProvider(project="test_proj")
        provider.start_run("test_run", {"lr": 0.01})
        mock_wandb.init.assert_called_with(
            project="test_proj",
            entity=None,
            name="test_run",
            config={"lr": 0.01}
        )

def test_log_metrics(mock_wandb):
    with patch.dict(os.environ, {"WANDB_API_KEY": "test_key"}):
        provider = TelemetryProvider()
        provider.log_metrics({"loss": 0.5}, step=1)
        mock_wandb.log.assert_called_with({"loss": 0.5}, step=1)

def test_finish(mock_wandb):
    with patch.dict(os.environ, {"WANDB_API_KEY": "test_key"}):
        provider = TelemetryProvider()
        provider.finish()
        mock_wandb.finish.assert_called_once()
