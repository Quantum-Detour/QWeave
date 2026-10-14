"""Tests for CLI summary table formatting."""

import io
from unittest import TestCase
from unittest.mock import patch

from qweave.cli import _format_box_table, _print_final_summary


class CliTableTests(TestCase):
    def test_format_box_table_alignment(self):
        headers = ["Col A", "Col B", "Num"]
        alignments = ["left", "left", "right"]
        rows = [
            ["Short", "A longer value", "42"],
            ["Another row", "Val", "1000"],
        ]
        table_str = _format_box_table(headers, alignments, rows, section_breaks={1})
        lines = table_str.split("\n")

        # Top border, header, header-divider, row 0, section-divider, row 1, bottom border
        self.assertEqual(len(lines), 7)
        self.assertTrue(lines[0].startswith("┌") and lines[0].endswith("┐"))
        self.assertTrue(lines[2].startswith("├") and lines[2].endswith("┤"))
        self.assertTrue(lines[4].startswith("├") and lines[4].endswith("┤"))
        self.assertTrue(lines[6].startswith("└") and lines[6].endswith("┘"))

        # Verify every line has the exact same character width
        line_lengths = {len(line) for line in lines}
        self.assertEqual(len(line_lengths), 1, f"Table lines have inconsistent widths: {line_lengths}")

        # Check right-alignment of numeric column
        row0_cells = [c.strip() for c in lines[3].split("│")[1:-1]]
        self.assertEqual(row0_cells, ["Short", "A longer value", "42"])
        # In row 0, "42" is right-aligned in a column of width 4 ("1000") -> preceded by spaces
        col2_raw = lines[3].split("│")[3]
        self.assertTrue(col2_raw.endswith(" 42 "))

    def test_print_final_summary_renders_cleanly_with_noiseless_and_noisy(self):
        rows = [
            {
                "processor": "five_node_multipath",
                "algorithm": "shortest_path",
                "noiseless_fidelity": 1.0,
                "noisy_fidelity": 0.9751,
                "swaps": 1,
                "native_two_qubit_gates": 4,
                "depth": 8,
                "accepted": 3072,
                "attempted": 3072,
            },
            {
                "processor": "five_node_multipath",
                "algorithm": "qmrp",
                "noiseless_fidelity": 1.0,
                "noisy_fidelity": 0.9711,
                "swaps": 2,
                "native_two_qubit_gates": 9,
                "depth": 11,
                "accepted": 3012,
                "attempted": 3072,
            },
            {
                "processor": "ibm_heavy_hex",
                "algorithm": "shortest_path",
                "noiseless_fidelity": 1.0,
                "noisy_fidelity": 0.7842,
                "swaps": 4,
                "native_two_qubit_gates": 13,
                "depth": 56,
                "accepted": 3072,
                "attempted": 3072,
            },
        ]
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            _print_final_summary(rows, noise="backend")

        output = buffer.getvalue()
        self.assertIn("Final summary (backend noise; ZZ circuit metrics)", output)
        self.assertIn("Noiseless", output)
        self.assertIn("Noisy", output)
        self.assertIn("Five-node", output)
        self.assertIn("1.0000", output)
        self.assertIn("0.9751", output)
        self.assertIn("0.9711", output)
        self.assertIn("IBM", output)
        self.assertIn("0.7842", output)
        # Verify no asterisk highest marker or footnote exists
        self.assertNotIn("0.9751*", output)
        self.assertNotIn("* Highest fidelity within processor family.", output)

    def test_print_final_summary_noise_none_shows_dash(self):
        rows = [
            {
                "processor": "five_node_multipath",
                "algorithm": "shortest_path",
                "noiseless_fidelity": 1.0,
                "noisy_fidelity": None,
                "swaps": 1,
                "native_two_qubit_gates": 4,
                "depth": 8,
                "accepted": 300,
                "attempted": 300,
            },
        ]
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            _print_final_summary(rows, noise="none")

        output = buffer.getvalue()
        self.assertIn("Noiseless", output)
        self.assertIn("Noisy", output)
        self.assertIn("1.0000", output)
        self.assertIn("—", output)

    def test_print_final_summary_empty_and_undefined(self):
        # Empty rows should not print or crash
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            _print_final_summary([], noise="none")
        self.assertEqual(buffer.getvalue(), "")

        # Undefined fidelity
        rows = [{
            "processor": "five_node_multipath",
            "algorithm": "qmrp",
            "noiseless_fidelity": 1.0,
            "noisy_fidelity": None,
            "swaps": 2,
            "native_two_qubit_gates": 9,
            "depth": 11,
            "accepted": 0,
            "attempted": 3072,
        }]
        buffer = io.StringIO()
        with patch("sys.stdout", buffer):
            _print_final_summary(rows, noise="backend")
        output = buffer.getvalue()
        self.assertIn("1.0000", output)
        self.assertIn("undefined", output)
        self.assertIn("0.00%", output)
