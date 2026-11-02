"""Behavior tests for conservative multi-window classification."""
import unittest
from custom_components.smart_heating.window_detail import classify_window_detail


class WindowDetailTests(unittest.TestCase):
    def test_empty_or_unknown_never_claims_closed(self):
        for states in ([], ["unknown"], ["unavailable", "off"], ["mystery", "off"]):
            with self.subTest(states=states):
                self.assertEqual(classify_window_detail(states), "unknown")

    def test_all_closed(self):
        self.assertEqual(classify_window_detail(["off", "closed", "false"]), "closed")

    def test_explicit_open_overrides_tilt_binary_and_unknown(self):
        for states in (["open", "tilted"], ["on", "offen"], ["unknown", "open"]):
            with self.subTest(states=states):
                self.assertEqual(classify_window_detail(states), "open")

    def test_binary_on_is_ambiguous_even_with_tilt(self):
        self.assertEqual(classify_window_detail(["on", "tilted"]), "open_or_tilted")

    def test_explicit_tilt_only_when_no_unknown_or_binary(self):
        self.assertEqual(classify_window_detail(["gekippt", "off"]), "tilted")
        self.assertEqual(classify_window_detail(["gekippt", "unavailable"]), "unknown")

    def test_single_binary_contact(self):
        self.assertEqual(classify_window_detail(["on"]), "open_or_tilted")
        self.assertEqual(classify_window_detail(["off"]), "closed")
