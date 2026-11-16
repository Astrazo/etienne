import re
import subprocess
import sys
import textwrap
import unittest


class LoggingConfigTests(unittest.TestCase):
    def run_logging_script(self, script: str) -> str:
        # Logging configuration is process-wide. Keep the test runner untouched.
        result = subprocess.run(
            [sys.executable, "-c", textwrap.dedent(script)],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        # Developer terminals may force ANSI colors even for captured output.
        return re.sub(r"\x1b\[[0-9;]*m", "", result.stderr)

    def test_server_and_application_messages_share_format_without_duplicates(self):
        output = self.run_logging_script("""
            import logging
            from loguru import logger
            from uvicorn import Config
            from etienne.logging_config import LOGGING_CONFIG

            config = Config("unused:app", log_config=LOGGING_CONFIG)
            # Reload workers apply the configuration again.
            config.configure_logging()
            logger.info("Application ready")
            logging.getLogger("uvicorn.error").info("Server ready")
            logging.getLogger("uvicorn.access").info(
                '%s - "%s %s HTTP/%s" %d',
                "127.0.0.1:1234", "GET", "/health", "1.1", 200,
            )
            logging.getLogger("fastapi").warning("Framework warning")
            logging.getLogger("example_library").info("Library ready")
            logger.debug("Hidden application debug")
            logging.getLogger("uvicorn.error").debug("Hidden server debug")
        """)
        lines = output.splitlines()
        self.assertEqual(len(lines), 5, output)
        for message in (
            "Application ready",
            "Server ready",
            '127.0.0.1:1234 - "GET /health HTTP/1.1" 200',
            "Framework warning",
            "Library ready",
        ):
            self.assertEqual(output.count(message), 1, output)
        for line in lines:
            self.assertRegex(line, r"\d{4}-\d{2}-\d{2} .* \| (INFO|WARNING) +\|")

    def test_preserves_exception_and_original_caller(self):
        output = self.run_logging_script("""
            import logging
            from uvicorn import Config
            from etienne.logging_config import LOGGING_CONFIG

            Config("unused:app", log_config=LOGGING_CONFIG)

            def handle_request():
                try:
                    raise ValueError("Example failure")
                except ValueError:
                    logging.getLogger("uvicorn.error").exception("Request failed")

            handle_request()
        """)
        self.assertIn("__main__:handle_request:", output)
        self.assertIn("ERROR", output)
        self.assertEqual(output.count("Request failed"), 1, output)
        self.assertIn("Traceback (most recent call last):", output)
        self.assertIn("ValueError: Example failure", output)
