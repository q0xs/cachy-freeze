from __future__ import annotations

import unittest

from cachy_freeze.errors import CachyFreezeError
from cachy_freeze.users import UserManager


class UserValidationTests(unittest.TestCase):
    def test_username_contract(self) -> None:
        self.assertEqual(UserManager.validate_username("person_01"), "person_01")
        for invalid in ("LocalAdm", "1person", "bad.name", "../root"):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager.validate_username(invalid)

    def test_password_policy(self) -> None:
        UserManager.validate_password("Correct-Horse-42")
        for invalid in ("short", "alllowercasebutlong", "Colon:Password42"):
            with self.subTest(invalid=invalid), self.assertRaises(CachyFreezeError):
                UserManager.validate_password(invalid)


if __name__ == "__main__":
    unittest.main()
