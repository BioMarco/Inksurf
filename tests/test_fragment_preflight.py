import unittest

from inksurf.fragment_preflight import normalize_files, parse_cli_output


class FragmentPreflightTests(unittest.TestCase):
    def test_normalizes_and_sorts_listing(self) -> None:
        payload = [
            {"name": "train.zip", "totalBytes": 123, "creationDate": "2023-01-01"},
            {"ref": "sample.csv", "size": 7},
        ]
        self.assertEqual(
            normalize_files(payload),
            [
                {"name": "sample.csv", "bytes": 7, "creation_date": None},
                {"name": "train.zip", "bytes": 123, "creation_date": "2023-01-01"},
            ],
        )

    def test_accepts_wrapped_listing(self) -> None:
        self.assertEqual(
            normalize_files({"files": [{"fileName": "test.zip", "bytes": "42"}]}),
            [{"name": "test.zip", "bytes": 42, "creation_date": None}],
        )

    def test_rejects_invalid_listing(self) -> None:
        with self.assertRaises(ValueError):
            normalize_files({"files": "not-a-list"})

    def test_parses_paginated_cli_output(self) -> None:
        payload, token = parse_cli_output('Next Page Token = opaque-token\n[{"name":"a"}]')
        self.assertEqual(payload, [{"name": "a"}])
        self.assertEqual(token, "opaque-token")

    def test_parses_final_cli_page(self) -> None:
        payload, token = parse_cli_output('[{"name":"z"}]')
        self.assertEqual(payload, [{"name": "z"}])
        self.assertIsNone(token)


if __name__ == "__main__":
    unittest.main()
