import tests.test_auth
import tests.test_backups
import tests.test_frontend
import unittest


def load_tests(loader: unittest.TestLoader, standard_tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite: unittest.TestSuite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromModule(tests.test_auth))
    suite.addTests(loader.loadTestsFromModule(tests.test_backups))
    suite.addTests(loader.loadTestsFromModule(tests.test_frontend))
    return suite
