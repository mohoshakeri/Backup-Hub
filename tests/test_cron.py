import importlib
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import tasks.cron
import utils.config


class CronTaskTestCase(unittest.TestCase):
    def test_cron_line_uses_application_config(self) -> None:
        with patch.dict("os.environ", {"BACKUP_HUB_CRON": "*/10 * * * *"}):
            importlib.reload(utils.config)
            cron_task = importlib.reload(tasks.cron)

            output = io.StringIO()
            with redirect_stdout(output):
                cron_task.main()

        self.assertEqual(output.getvalue(), "*/10 * * * * python -m tasks.backup\n")

        importlib.reload(utils.config)
        importlib.reload(tasks.cron)
