"""Tests for dynamic visual report generation and CLI report options."""

import io
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch

from qweave.report import (
    generate_html_report,
    build_processor_figure,
    build_fidelity_comparison_figure,
    build_overhead_comparison_figure,
)
from qweave.cli import main as cli_main


class VisualReportTests(TestCase):
    def test_generate_html_report_dynamic_values(self):
        """Verify the report renders dynamic execution values without hardcoding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_report.html"
            sample_rows = [
                {
                    "processor": "five_node_multipath",
                    "algorithm": "shortest_path",
                    "num_qubits": 5,
                    "output_ports": (0, 4),
                    "active_qubits": 3,
                    "noiseless_fidelity": 1.0,
                    "noisy_fidelity": 0.8888,
                    "fidelity": 0.8888,
                    "fidelity_interval": (0.8500, 0.9200),
                    "swaps": 1,
                    "native_two_qubit_gates": 42,
                    "depth": 137,
                    "accepted": 2900,
                    "attempted": 3000,
                    "unconditional_fidelity": 0.8200,
                },
                {
                    "processor": "five_node_multipath",
                    "algorithm": "qmrp",
                    "num_qubits": 5,
                    "output_ports": (0, 4),
                    "active_qubits": 5,
                    "noiseless_fidelity": 1.0,
                    "noisy_fidelity": 0.9123,
                    "fidelity": 0.9123,
                    "fidelity_interval": (0.8700, 0.9500),
                    "swaps": 2,
                    "native_two_qubit_gates": 84,
                    "depth": 250,
                    "accepted": 2700,
                    "attempted": 3000,
                    "unconditional_fidelity": 0.8400,
                },
            ]

            generate_html_report(sample_rows, out_file, metadata={"noise": "backend", "shots": 1000})
            self.assertTrue(out_file.is_file())
            content = out_file.read_text()

            # Dynamic values must be present in the generated HTML
            self.assertIn("0.8888", content)
            self.assertIn("0.9123", content)
            self.assertIn("42", content)
            self.assertIn("137", content)
            self.assertIn("84", content)
            self.assertIn("250", content)
            self.assertIn("3 / 5", content)
            self.assertIn("5 / 5", content)
            self.assertIn("90.00%", content)  # 2700/3000
            self.assertIn("96.67%", content)  # 2900/3000

    def test_build_figures_single_processor(self):
        """Figures should build without error for a single processor."""
        rows = [
            {
                "processor": "five_node_multipath",
                "algorithm": "shortest_path",
                "num_qubits": 5,
                "noisy_fidelity": 0.95,
                "fidelity": 0.95,
                "native_two_qubit_gates": 4,
                "depth": 8,
            }
        ]
        fig_fid = build_fidelity_comparison_figure(rows, noise="backend")
        self.assertIsNotNone(fig_fid)
        fig_over = build_overhead_comparison_figure(rows)
        self.assertIsNotNone(fig_over)
        proc_fig = build_processor_figure("five_node_multipath")
        self.assertIsNotNone(proc_fig)

    def test_cli_generates_report_by_default(self):
        """By default, the CLI generates the HTML report at results/visual_summary.html."""
        test_args = [
            "qweave",
            "--processor", "five_node_multipath",
            "--algorithm", "shortest_path",
            "--noise", "none",
            "--shots", "10",
        ]
        buffer = io.StringIO()
        with patch("sys.argv", test_args), patch("sys.stdout", buffer):
            cli_main()

        output = buffer.getvalue()
        self.assertIn("Visual report generated: results/visual_summary.html", output)
        self.assertTrue(Path("results/visual_summary.html").is_file())

    def test_cli_no_report_flag_skips_generation(self):
        """Passing --no-report must suppress visual report generation."""
        test_args = [
            "qweave",
            "--processor", "five_node_multipath",
            "--algorithm", "shortest_path",
            "--noise", "none",
            "--shots", "10",
            "--no-report",
        ]
        buffer = io.StringIO()
        with patch("sys.argv", test_args), patch("sys.stdout", buffer):
            cli_main()

        output = buffer.getvalue()
        self.assertNotIn("Visual report generated:", output)
