import json
import pytest

from setup import app as setup_app


@pytest.fixture
def temp_setup_config(tmp_path, monkeypatch):
    config_file = str(tmp_path / 'config.json')
    monkeypatch.setattr(setup_app, 'CONFIG_PATH', config_file)
    return config_file


def test_api_save_preserves_font_size(temp_setup_config):
    # Prepare existing config with font_size
    with open(temp_setup_config, 'w') as f:
        json.dump({'font_size': 44, 'speech_mode': 'offline'}, f)

    client = setup_app.app.test_client()
    payload = {'speech_mode': 'online', 'stt_provider': 'deepgram'}
    res = client.post('/api/save', json=payload)
    assert res.status_code == 200

    with open(temp_setup_config) as f:
        saved = json.load(f)

    assert saved['speech_mode'] == 'online'
    assert saved['stt_provider'] == 'deepgram'
    assert saved['font_size'] == 44


def test_api_save_allows_updating_font_size(temp_setup_config):
    with open(temp_setup_config, 'w') as f:
        json.dump({'font_size': 36}, f)

    client = setup_app.app.test_client()
    res = client.post('/api/save', json={'font_size': 52})
    assert res.status_code == 200

    with open(temp_setup_config) as f:
        saved = json.load(f)

    assert saved['font_size'] == 52
