"""Comprehensive CLI tests to improve coverage."""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from click.testing import CliRunner

from vc_commit_helper.cli import main, detect_vcs, prompt_user, EXIT_NO_REPO, EXIT_SUCCESS, EXIT_ALL_DECLINED
from vc_commit_helper.grouping.group_model import CommitGroup


class TestCLIComprehensive(unittest.TestCase):
    """Comprehensive tests for CLI functionality."""

    def test_detect_vcs_both_repos_found(self):
        """Test detect_vcs when both Git and SVN are found."""
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=Path("/repo")):
            with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=Path("/repo")):
                with self.assertRaises(SystemExit) as ctx:
                    detect_vcs(Path("/repo"))
                self.assertEqual(ctx.exception.code, EXIT_NO_REPO)

    def test_detect_vcs_no_repo_found(self):
        """Test detect_vcs when no repository is found."""
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=None):
            with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=None):
                with self.assertRaises(SystemExit) as ctx:
                    detect_vcs(Path("/repo"))
                self.assertEqual(ctx.exception.code, EXIT_NO_REPO)

    def test_detect_vcs_git_found(self):
        """Test detect_vcs when Git repository is found."""
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=Path("/repo")):
            with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=None):
                vcs_type, repo_root = detect_vcs(Path("/repo"))
                self.assertEqual(vcs_type, "git")
                self.assertEqual(repo_root, Path("/repo"))

    def test_detect_vcs_svn_found(self):
        """Test detect_vcs when SVN repository is found."""
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=None):
            with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=Path("/repo")):
                vcs_type, repo_root = detect_vcs(Path("/repo"))
                self.assertEqual(vcs_type, "svn")
                self.assertEqual(repo_root, Path("/repo"))

    @patch("vc_commit_helper.cli.click.prompt")
    def test_prompt_user_accept(self, mock_prompt):
        """Test prompt_user with accept choice."""
        mock_prompt.return_value = "a"
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        result = prompt_user(group, 1, 1)
        self.assertEqual(result, "[feat]: add test")

    @patch("vc_commit_helper.cli.click.prompt")
    def test_prompt_user_decline(self, mock_prompt):
        """Test prompt_user with decline choice."""
        mock_prompt.return_value = "d"
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        result = prompt_user(group, 1, 1)
        self.assertIsNone(result)

    @patch("builtins.open", new_callable=mock_open, read_data="edited message")
    @patch("os.unlink")
    @patch("subprocess.run")
    @patch("tempfile.NamedTemporaryFile")
    @patch("vc_commit_helper.cli.click.prompt")
    @patch("os.environ.get")
    def test_prompt_user_edit_with_editor(self, mock_env_get, mock_prompt, mock_tempfile, mock_subprocess, mock_unlink, mock_file):
        """Test prompt_user with edit choice and EDITOR set."""
        mock_env_get.return_value = "vim"
        mock_prompt.return_value = "e"
        
        # Mock the temporary file
        mock_tmp = MagicMock()
        mock_tmp.name = "/tmp/test_commit.txt"
        mock_tmp.__enter__.return_value = mock_tmp
        mock_tempfile.return_value = mock_tmp
        
        # Mock subprocess to succeed
        mock_subprocess.return_value = Mock(returncode=0)
        
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        
        result = prompt_user(group, 1, 1)
        self.assertEqual(result, "edited message")
        
        # Verify subprocess was called with editor
        mock_subprocess.assert_called_once()
        self.assertEqual(mock_subprocess.call_args[0][0][0], "vim")

    @patch("vc_commit_helper.cli.click.prompt")
    @patch("os.environ.get")
    def test_prompt_user_edit_without_editor(self, mock_env_get, mock_prompt):
        """Test prompt_user with edit choice and no EDITOR."""
        mock_env_get.return_value = None
        mock_prompt.side_effect = ["e", "New commit message", "."]
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        result = prompt_user(group, 1, 1)
        self.assertEqual(result, "New commit message")

    @patch("subprocess.run")
    @patch("vc_commit_helper.cli.click.prompt")
    @patch("os.environ.get")
    def test_prompt_user_edit_with_editor_failure(self, mock_env_get, mock_prompt, mock_subprocess):
        """Test prompt_user when editor fails."""
        mock_env_get.return_value = "vim"
        mock_prompt.side_effect = ["e", "a"]
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        mock_subprocess.side_effect = Exception("Editor failed")
        result = prompt_user(group, 1, 1)
        self.assertEqual(result, "[feat]: add test")

    @patch("vc_commit_helper.cli.click.prompt")
    def test_prompt_user_invalid_then_accept(self, mock_prompt):
        """Test prompt_user with invalid choice then accept."""
        mock_prompt.side_effect = ["x", "a"]
        group = CommitGroup(
            type="feat",
            files=["test.py"],
            message="[feat]: add test",
            diffs={"test.py": "+test"}
        )
        result = prompt_user(group, 1, 1)
        self.assertEqual(result, "[feat]: add test")

    def test_main_with_forced_git_not_found(self):
        """Test main with --vcs=git when not in a Git repo."""
        runner = CliRunner()
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=None):
            result = runner.invoke(main, ["--vcs", "git"])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("not inside a Git repository", result.output)

    def test_main_with_forced_svn_not_found(self):
        """Test main with --vcs=svn when not in an SVN repo."""
        runner = CliRunner()
        with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=None):
            result = runner.invoke(main, ["--vcs", "svn"])
            self.assertNotEqual(result.exit_code, 0)
            self.assertIn("not inside an SVN working copy", result.output)

    def test_main_with_yes_flag_git(self):
        """Test main with --yes flag for Git repository."""
        runner = CliRunner()
        mock_config = {
            "base_url": "http://localhost",
            "port": 11434,
            "model": "llama3"
        }
        mock_changes = [Mock(path="test.py", status="M")]
        mock_groups = [
            CommitGroup(
                type="feat",
                files=["test.py"],
                message="[feat]: add test",
                diffs={"test.py": "+test"}
            )
        ]
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=Path("/repo")):
            with patch("vc_commit_helper.cli.load_config", return_value=mock_config):
                with patch("vc_commit_helper.cli.GitClient") as mock_git_class:
                    mock_client = Mock()
                    mock_client.get_changes.return_value = mock_changes
                    mock_client.get_diff.return_value = "+test"
                    mock_git_class.return_value = mock_client
                    with patch("vc_commit_helper.cli.CommitMessageGenerator") as mock_gen_class:
                        mock_gen = Mock()
                        mock_gen.generate_groups.return_value = mock_groups
                        mock_gen_class.return_value = mock_gen
                        result = runner.invoke(main, ["--yes"])
                        self.assertEqual(result.exit_code, EXIT_SUCCESS)

    def test_main_with_yes_flag_svn(self):
        """Test main with --yes flag for SVN repository."""
        runner = CliRunner()
        mock_config = {
            "base_url": "http://localhost",
            "port": 11434,
            "model": "llama3"
        }
        mock_changes = [Mock(path="test.py", status="M")]
        mock_groups = [
            CommitGroup(
                type="feat",
                files=["test.py"],
                message="[feat]: add test",
                diffs={"test.py": "+test"}
            )
        ]
        with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=Path("/repo")):
            with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=None):
                with patch("vc_commit_helper.cli.load_config", return_value=mock_config):
                    with patch("vc_commit_helper.cli.SVNClient") as mock_svn_class:
                        mock_client = Mock()
                        mock_client.get_changes.return_value = mock_changes
                        mock_client.get_diff.return_value = "+test"
                        mock_svn_class.return_value = mock_client
                        with patch("vc_commit_helper.cli.CommitMessageGenerator") as mock_gen_class:
                            mock_gen = Mock()
                            mock_gen.generate_groups.return_value = mock_groups
                            mock_gen_class.return_value = mock_gen
                            result = runner.invoke(main, ["--yes"])
                            self.assertEqual(result.exit_code, EXIT_SUCCESS)

    def test_main_all_groups_declined(self):
        """Test main when all groups are declined."""
        runner = CliRunner()
        mock_config = {
            "base_url": "http://localhost",
            "port": 11434,
            "model": "llama3"
        }
        mock_changes = [Mock(path="test.py", status="M")]
        mock_groups = [
            CommitGroup(
                type="feat",
                files=["test.py"],
                message="[feat]: add test",
                diffs={"test.py": "+test"}
            )
        ]
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=Path("/repo")):
            with patch("vc_commit_helper.cli.load_config", return_value=mock_config):
                with patch("vc_commit_helper.cli.GitClient") as mock_git_class:
                    mock_client = Mock()
                    mock_client.get_changes.return_value = mock_changes
                    mock_client.get_diff.return_value = "+test"
                    mock_git_class.return_value = mock_client
                    with patch("vc_commit_helper.cli.CommitMessageGenerator") as mock_gen_class:
                        mock_gen = Mock()
                        mock_gen.generate_groups.return_value = mock_groups
                        mock_gen_class.return_value = mock_gen
                        with patch("vc_commit_helper.cli.prompt_user", return_value=None):
                            result = runner.invoke(main, [])
                            self.assertEqual(result.exit_code, EXIT_ALL_DECLINED)

    def test_main_with_verbose_flag(self):
        """Test main with --verbose flag."""
        runner = CliRunner()
        with patch("vc_commit_helper.cli.GitClient.find_repo_root", return_value=None):
            with patch("vc_commit_helper.cli.SVNClient.find_repo_root", return_value=None):
                result = runner.invoke(main, ["--verbose"])
                self.assertNotEqual(result.exit_code, 0)

    def test_main_with_generic_exception(self):
        """Test main with unexpected exception."""
        runner = CliRunner()
        with patch("vc_commit_helper.cli.detect_vcs", side_effect=Exception("Unexpected error")):
            result = runner.invoke(main, [])
            self.assertNotEqual(result.exit_code, 0)