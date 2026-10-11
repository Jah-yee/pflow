"""Tests for shell stderr display in CLI error output.

This test validates that stderr from shell nodes is properly displayed
in verbose mode when a shell command fails.

Related bug: Shell node stderr not surfaced in error messages
"""

import json

from click.testing import CliRunner

from pflow.cli.main import main
from tests.shared.markdown_utils import write_workflow_file


class TestShellStderrDisplay:
    """Test shell stderr is displayed in CLI error output."""

    def test_shell_stderr_displayed_in_verbose_mode(self, tmp_path):
        """Stderr from failed shell nodes should be displayed in verbose mode.

        When a shell command fails and writes to stderr, the error output
        should include the stderr content to help users debug the issue.
        """
        workflow = {
            "ir_version": "0.1.0",
            "nodes": [
                {
                    "id": "failing-command",
                    "type": "shell",
                    "params": {
                        # Command that writes to stderr and fails
                        "command": "echo 'This error message should be visible' >&2; exit 1"
                    },
                }
            ],
            "edges": [],
        }

        workflow_path = tmp_path / "test.pflow.md"
        write_workflow_file(workflow, workflow_path)

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--verbose", str(workflow_path)])

        assert result.exit_code != 0

        # Verify stderr is displayed in verbose output
        assert "Stderr:" in result.output or "Stderr:" in (result.stderr or "")
        assert "This error message should be visible" in result.output or "This error message should be visible" in (
            result.stderr or ""
        )

    def test_shell_stderr_in_json_output(self, tmp_path):
        """JSON output should include shell_stderr field for failed shell nodes."""
        workflow = {
            "ir_version": "0.1.0",
            "nodes": [
                {
                    "id": "failing-command",
                    "type": "shell",
                    "params": {"command": "echo 'stderr content here' >&2; exit 1"},
                }
            ],
            "edges": [],
        }

        workflow_path = tmp_path / "test.pflow.md"
        write_workflow_file(workflow, workflow_path)

        # mix_stderr=False: under click 8.1 (transitive pin from litellm 1.83.x),
        # CliRunner defaults to mix_stderr=True which merges stderr into stdout
        # and breaks json.loads(result.stdout). Click 8.2 flipped the default;
        # 8.3+ removed the kwarg.
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--output-format", "json", str(workflow_path)])

        assert result.exit_code != 0

        # Parse JSON output
        output = json.loads(result.stdout)

        # Verify shell_stderr is in the error structure
        assert "errors" in output
        assert len(output["errors"]) > 0

        error = output["errors"][0]
        assert "stderr content here" in error["context"]["shell_stderr"]

    def test_long_stderr_preview_keeps_the_tail_where_the_cause_is(self, tmp_path):
        """A long stderr shows its head AND its tail in both text previews (#755).

        Tools write the cause last, after progress noise. The cause marker sits only at
        the very end of ~1,100 chars of stderr and is printed via ``%s`` so it never
        appears in the command text — the text channels must show it, and JSON keeps
        the whole stderr.
        """
        command = (
            "i=0; while [ $i -lt 60 ]; do printf 'progress-noise-%02d ' $i >&2; i=$((i+1)); done; "
            "printf 'CAUSE-%s-TAIL' AT >&2; exit 3"
        )
        workflow = {
            "ir_version": "0.1.0",
            "nodes": [{"id": "noisy", "type": "shell", "params": {"command": command}}],
            "edges": [],
        }
        workflow_path = tmp_path / "test.pflow.md"
        write_workflow_file(workflow, workflow_path)
        runner = CliRunner(mix_stderr=False)

        text = runner.invoke(main, [str(workflow_path)])
        lines = (text.output + (text.stderr or "")).splitlines()
        headline = next(line for line in lines if line.startswith("Command failed with exit code 3:"))
        details = next(line for line in lines if line.startswith("    Stderr: "))
        for preview in (headline, details):
            assert "progress-noise-00" in preview  # the head stays
            assert "progress-noise-30" not in preview  # the middle is cut
            assert "chars omitted]" in preview
            assert preview.endswith("CAUSE-AT-TAIL")  # the tail stays

        as_json = runner.invoke(main, ["--output-format", "json", str(workflow_path)])
        error = json.loads(as_json.stdout)["errors"][0]
        assert error["context"]["shell_stderr"].startswith("progress-noise-00")
        assert "progress-noise-30" in error["context"]["shell_stderr"]  # JSON carries the full text
        assert error["context"]["shell_stderr"].endswith("CAUSE-AT-TAIL")

    def test_no_stderr_section_when_stderr_empty(self, tmp_path):
        """No stderr section should appear when shell has no stderr output."""
        workflow = {
            "ir_version": "0.1.0",
            "nodes": [
                {
                    "id": "no-stderr",
                    "type": "shell",
                    "params": {
                        # Fails with exit code but no stderr
                        "command": "exit 1"
                    },
                }
            ],
            "edges": [],
        }

        workflow_path = tmp_path / "test.pflow.md"
        write_workflow_file(workflow, workflow_path)

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["--verbose", str(workflow_path)])

        assert result.exit_code != 0

        # Should show shell details but NOT stderr section (since it's empty)
        combined_output = result.output + (result.stderr or "")
        assert "Shell details:" in combined_output
        assert "Command:" in combined_output
        # Stderr line should not appear when stderr is empty
        # (we check this by ensuring "Stderr:" doesn't appear with empty content)
