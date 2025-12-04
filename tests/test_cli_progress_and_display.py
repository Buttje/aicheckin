"""Tests for CLI progress indicators and display utilities."""

import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

from vc_commit_helper.cli import (
    ProgressIndicator,
    print_step,
    print_info,
    print_success,
    print_warning,
    print_error,
    print_summary_box,
)


class TestProgressIndicator(unittest.TestCase):
    """Tests for ProgressIndicator context manager."""

    @patch('vc_commit_helper.cli.click.echo')
    @patch('vc_commit_helper.cli.time.time')
    def test_progress_with_spinner(self, mock_time, mock_echo):
        """Test progress indicator with spinner enabled."""
        mock_time.side_effect = [0.0, 1.5]
        
        with ProgressIndicator("Processing", show_spinner=True) as p:
            pass
        
        # Should have called echo twice: start and end
        self.assertEqual(mock_echo.call_count, 2)
        # First call should have spinner character
        self.assertIn("Processing", str(mock_echo.call_args_list[0]))
        # Second call should have checkmark and time
        self.assertIn("✓", str(mock_echo.call_args_list[1]))
        self.assertIn("1.5s", str(mock_echo.call_args_list[1]))

    @patch('vc_commit_helper.cli.click.echo')
    @patch('vc_commit_helper.cli.time.time')
    def test_progress_without_spinner(self, mock_time, mock_echo):
        """Test progress indicator without spinner."""
        mock_time.side_effect = [0.0, 2.3]
        
        with ProgressIndicator("Loading", show_spinner=False) as p:
            pass
        
        # Should have called echo twice
        self.assertEqual(mock_echo.call_count, 2)
        # Should show arrow instead of spinner
        self.assertIn("→", str(mock_echo.call_args_list[0]))
        self.assertIn("Loading", str(mock_echo.call_args_list[0]))

    @patch('vc_commit_helper.cli.click.echo')
    def test_progress_update(self, mock_echo):
        """Test updating progress message."""
        with ProgressIndicator("Working", show_spinner=True) as p:
            p.update("Still working")
        
        # Should have called echo at least 3 times (start, update, end)
        self.assertGreaterEqual(mock_echo.call_count, 3)


class TestDisplayUtilities(unittest.TestCase):
    """Tests for display utility functions."""

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_step(self, mock_echo):
        """Test step printing."""
        print_step(1, 3, "Initialize")
        
        # Should print separator, step text, and separator
        self.assertEqual(mock_echo.call_count, 3)
        call_args = [str(call) for call in mock_echo.call_args_list]
        self.assertTrue(any("Step 1/3" in arg for arg in call_args))
        self.assertTrue(any("Initialize" in arg for arg in call_args))
        self.assertTrue(any("=" in arg for arg in call_args))

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_info(self, mock_echo):
        """Test info message printing."""
        print_info("Information message")
        mock_echo.assert_called_once()
        self.assertIn("Information message", str(mock_echo.call_args))

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_info_with_indent(self, mock_echo):
        """Test info message with indentation."""
        print_info("Indented", indent=2)
        call_str = str(mock_echo.call_args)
        self.assertIn("Indented", call_str)

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_success(self, mock_echo):
        """Test success message printing."""
        print_success("Operation succeeded")
        call_str = str(mock_echo.call_args)
        self.assertIn("✓", call_str)
        self.assertIn("Operation succeeded", call_str)

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_warning(self, mock_echo):
        """Test warning message printing."""
        print_warning("Warning message")
        call_str = str(mock_echo.call_args)
        self.assertIn("⚠", call_str)
        self.assertIn("Warning message", call_str)

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_error(self, mock_echo):
        """Test error message printing."""
        print_error("Error occurred")
        call_str = str(mock_echo.call_args)
        self.assertIn("✗", call_str)
        self.assertIn("Error occurred", call_str)
        # Should use err=True
        self.assertTrue(mock_echo.call_args.kwargs.get('err', False))

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_summary_box(self, mock_echo):
        """Test summary box printing."""
        print_summary_box("Summary", ["Item 1", "Item 2", "Item 3"])
        
        # Should print multiple lines: top border, title, separator, items, bottom border
        self.assertGreaterEqual(mock_echo.call_count, 7)
        call_args = [str(call) for call in mock_echo.call_args_list]
        
        # Check for box characters
        self.assertTrue(any("┌" in arg for arg in call_args))
        self.assertTrue(any("└" in arg for arg in call_args))
        self.assertTrue(any("Summary" in arg for arg in call_args))
        self.assertTrue(any("Item 1" in arg for arg in call_args))

    @patch('vc_commit_helper.cli.click.echo')
    def test_print_summary_box_empty(self, mock_echo):
        """Test summary box with no items."""
        print_summary_box("Empty Summary", [])
        
        # Should still print borders and title
        self.assertGreaterEqual(mock_echo.call_count, 4)


if __name__ == "__main__":
    unittest.main()
