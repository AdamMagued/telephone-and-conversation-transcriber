import json
import os
import pytest
from PyQt6.QtWidgets import QApplication

import caption_app
from caption_app import (
    CaptionView,
    DEFAULT_FONT_SIZE,
    FONT_PRESETS,
    FONT_SIZE_STEP,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    clamp_font_size,
    get_next_font_size,
    get_prev_font_size,
    load_config,
    save_config,
    save_font_size,
)

# Ensure headless Qt environment
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


@pytest.fixture(scope='session')
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(['-platform', 'offscreen'])
    return app


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    config_file = str(tmp_path / 'config.json')
    monkeypatch.setattr(caption_app, 'CONFIG_PATH', config_file)
    monkeypatch.setattr(caption_app, 'CONFIG', {})
    return config_file


class TestFontSizeBoundaryGuards:
    def test_clamp_within_bounds(self):
        assert clamp_font_size(36) == 36
        assert clamp_font_size(24) == 24
        assert clamp_font_size(48) == 48

    def test_clamp_lower_boundary_guard(self):
        assert clamp_font_size(MIN_FONT_SIZE) == MIN_FONT_SIZE
        assert clamp_font_size(MIN_FONT_SIZE - 1) == MIN_FONT_SIZE
        assert clamp_font_size(0) == MIN_FONT_SIZE
        assert clamp_font_size(-10) == MIN_FONT_SIZE

    def test_clamp_upper_boundary_guard(self):
        assert clamp_font_size(MAX_FONT_SIZE) == MAX_FONT_SIZE
        assert clamp_font_size(MAX_FONT_SIZE + 1) == MAX_FONT_SIZE
        assert clamp_font_size(100) == MAX_FONT_SIZE
        assert clamp_font_size(1000) == MAX_FONT_SIZE

    def test_clamp_string_presets(self):
        assert clamp_font_size('S') == FONT_PRESETS['S']
        assert clamp_font_size('s') == FONT_PRESETS['S']
        assert clamp_font_size('M') == FONT_PRESETS['M']
        assert clamp_font_size('m') == FONT_PRESETS['M']
        assert clamp_font_size('L') == FONT_PRESETS['L']
        assert clamp_font_size('l') == FONT_PRESETS['L']

    def test_clamp_numeric_strings_and_floats(self):
        assert clamp_font_size('40') == 40
        assert clamp_font_size('10') == MIN_FONT_SIZE
        assert clamp_font_size('90') == MAX_FONT_SIZE
        assert clamp_font_size(36.4) == 36
        assert clamp_font_size(36.6) == 37

    def test_clamp_invalid_inputs_fallback_to_default(self):
        assert clamp_font_size(None) == DEFAULT_FONT_SIZE
        assert clamp_font_size('invalid') == DEFAULT_FONT_SIZE
        assert clamp_font_size('') == DEFAULT_FONT_SIZE


class TestIncrementalScaling:
    def test_increment_by_step(self):
        start = DEFAULT_FONT_SIZE
        next_size = get_next_font_size(start)
        assert next_size == start + FONT_SIZE_STEP

    def test_decrement_by_step(self):
        start = DEFAULT_FONT_SIZE
        prev_size = get_prev_font_size(start)
        assert prev_size == start - FONT_SIZE_STEP

    def test_increment_boundary_guard(self):
        size = MAX_FONT_SIZE
        assert get_next_font_size(size) == MAX_FONT_SIZE
        near_max = MAX_FONT_SIZE - (FONT_SIZE_STEP - 1)
        assert get_next_font_size(near_max) == MAX_FONT_SIZE

    def test_decrement_boundary_guard(self):
        size = MIN_FONT_SIZE
        assert get_prev_font_size(size) == MIN_FONT_SIZE
        near_min = MIN_FONT_SIZE + (FONT_SIZE_STEP - 1)
        assert get_prev_font_size(near_min) == MIN_FONT_SIZE

    def test_custom_step(self):
        assert get_next_font_size(30, step=8) == 38
        assert get_prev_font_size(30, step=8) == 22


class TestFontSizePersistence:
    def test_save_config_creates_file_and_updates_dict(self, temp_config):
        success = save_config({'font_size': 44, 'custom_key': 'value'})
        assert success is True
        assert os.path.exists(temp_config)

        with open(temp_config) as f:
            data = json.load(f)
        assert data['font_size'] == 44
        assert data['custom_key'] == 'value'
        assert caption_app.CONFIG['font_size'] == 44

    def test_save_config_preserves_existing_keys(self, temp_config):
        save_config({'speech_mode': 'online', 'stt_provider': 'deepgram'})
        save_font_size(48)

        loaded = load_config()
        assert loaded['speech_mode'] == 'online'
        assert loaded['stt_provider'] == 'deepgram'
        assert loaded['font_size'] == 48

    def test_save_font_size_clamps_before_saving(self, temp_config):
        save_font_size(200)
        loaded = load_config()
        assert loaded['font_size'] == MAX_FONT_SIZE

        save_font_size(5)
        loaded = load_config()
        assert loaded['font_size'] == MIN_FONT_SIZE


class TestCaptionViewIncrementalTextSize:
    def test_initialization_with_default(self, qapp, temp_config):
        view = CaptionView()
        assert view.font_size == DEFAULT_FONT_SIZE
        assert view.current_size == DEFAULT_FONT_SIZE
        assert view.text.font().pointSize() == DEFAULT_FONT_SIZE

    def test_initialization_with_saved_config(
        self, qapp, temp_config, monkeypatch
    ):
        monkeypatch.setattr(caption_app, 'CONFIG', {'font_size': 44})
        view = CaptionView()
        assert view.font_size == 44
        assert view.text.font().pointSize() == 44

    def test_size_buttons_present(self, qapp, temp_config):
        view = CaptionView()
        assert '-' in view.size_buttons
        assert '+' in view.size_buttons
        assert '0' in view.size_buttons

    def test_increase_font_size(self, qapp, temp_config):
        view = CaptionView()
        initial = view.font_size
        view.increase_font_size()
        expected = initial + FONT_SIZE_STEP
        assert view.font_size == expected
        assert view.text.font().pointSize() == expected
        assert view.text.document().defaultFont().pointSize() == expected
        assert load_config().get('font_size') == expected

    def test_decrease_font_size(self, qapp, temp_config):
        view = CaptionView()
        initial = view.font_size
        view.decrease_font_size()
        expected = initial - FONT_SIZE_STEP
        assert view.font_size == expected
        assert view.text.font().pointSize() == expected
        assert view.text.document().defaultFont().pointSize() == expected
        assert load_config().get('font_size') == expected

    def test_reset_font_size(self, qapp, temp_config):
        view = CaptionView()
        view.increase_font_size()
        view.increase_font_size()
        assert view.font_size != DEFAULT_FONT_SIZE
        view.reset_font_size()
        assert view.font_size == DEFAULT_FONT_SIZE
        assert load_config().get('font_size') == DEFAULT_FONT_SIZE

    def test_upper_boundary_guard_in_view(self, qapp, temp_config):
        view = CaptionView()
        view.set_font_size(MAX_FONT_SIZE)
        view.increase_font_size()
        assert view.font_size == MAX_FONT_SIZE
        assert '#181818' in view.size_buttons['+'].styleSheet()

    def test_lower_boundary_guard_in_view(self, qapp, temp_config):
        view = CaptionView()
        view.set_font_size(MIN_FONT_SIZE)
        view.decrease_font_size()
        assert view.font_size == MIN_FONT_SIZE
        assert '#181818' in view.size_buttons['-'].styleSheet()

    def test_backwards_compatibility_set_size(self, qapp, temp_config):
        view = CaptionView()
        view.set_size('S')
        assert view.font_size == FONT_PRESETS['S']
        view.set_size('L')
        assert view.font_size == FONT_PRESETS['L']
        view.set_size('M')
        assert view.font_size == FONT_PRESETS['M']
        view.set_size(52)
        assert view.font_size == 52

    def test_button_mouse_press_events(self, qapp, temp_config):
        view = CaptionView()
        initial = view.font_size
        view.size_buttons['+'].mousePressEvent(None)
        assert view.font_size == initial + FONT_SIZE_STEP
        view.size_buttons['-'].mousePressEvent(None)
        assert view.font_size == initial
        view.set_font_size(48)
        view.size_buttons['0'].mousePressEvent(None)
        assert view.font_size == DEFAULT_FONT_SIZE
