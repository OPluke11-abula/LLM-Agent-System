import unittest

from skills.query_db import QueryDBArgs, query_db


class QueryDBSkillTests(unittest.TestCase):
    def test_query_db_accepts_select_query(self) -> None:
        args = QueryDBArgs(query="SELECT * FROM users", limit=5)
        result = query_db(args)
        self.assertIn("SELECT * FROM users", result)
        self.assertIn("limit=5", result)

    def test_query_db_rejects_non_select_query(self) -> None:
        args = QueryDBArgs(query="DELETE FROM users", limit=1)
        with self.assertRaises(ValueError):
            query_db(args)

    def test_query_db_rejects_multi_statement_query(self) -> None:
        args = QueryDBArgs(query="SELECT * FROM users; DROP TABLE users", limit=1)
        with self.assertRaises(ValueError):
            query_db(args)

    def test_query_db_rejects_file_write_clause(self) -> None:
        args = QueryDBArgs(
            query="SELECT * INTO OUTFILE '/tmp/users.csv' FROM users",
            limit=1,
        )
        with self.assertRaises(ValueError):
            query_db(args)


if __name__ == "__main__":
    unittest.main()
