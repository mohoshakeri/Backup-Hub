import tests.test_auth
import tests.test_backup_provider_common
import tests.test_backups
import tests.test_download_tokens
import tests.test_frontend
import tests.test_security
import unittest


def load_tests(loader: unittest.TestLoader, standard_tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite: unittest.TestSuite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(tests.test_auth))
    suite.addTests(loader.loadTestsFromModule(tests.test_backup_provider_common))
    suite.addTests(loader.loadTestsFromModule(tests.test_backups))
    suite.addTests(loader.loadTestsFromModule(tests.test_download_tokens))
    suite.addTests(loader.loadTestsFromModule(tests.test_frontend))
    suite.addTests(loader.loadTestsFromModule(tests.test_security))
    return suite
