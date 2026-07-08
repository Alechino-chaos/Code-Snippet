import json
import os
import shutil
from io import StringIO
import unittest
import uuid
from unittest.mock import patch

from rich.console import Console

import main


class SnipTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = os.path.join(os.getcwd(), f"test_tmp_{uuid.uuid4().hex}")
        os.makedirs(self.temp_dir)
        self.addCleanup(lambda: shutil.rmtree(self.temp_dir, ignore_errors=True))
        self.db_path = os.path.join(self.temp_dir, "snips.json")
        self.config_path = os.path.join(self.temp_dir, "config.json")

        patches = [
            patch.object(main, "DEFAULT_DB_PATH", self.db_path),
            patch.object(main, "CONFIG_FILE", self.config_path),
            patch.object(main, "console", Console(file=StringIO(), force_terminal=False)),
            patch.object(main, "save_json_atomic", self.write_json_atomic),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def write_json_atomic(self, path, data):
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")

    def write_db(self, data):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def read_db(self):
        with open(self.db_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def assert_v2_snippet(self, data, tag, code, language="python", note=""):
        self.assertEqual(data["__schema_version"], 2)
        snippet = data["snippets"][tag]
        self.assertEqual(snippet["code"], code)
        self.assertEqual(snippet["language"], language)
        self.assertEqual(snippet["note"], note)
        self.assertIn("created_at", snippet)
        self.assertIn("updated_at", snippet)

    def test_get_db_path_uses_default_when_no_config_exists(self):
        self.assertEqual(main.get_db_path(), self.db_path)

    def test_get_db_path_uses_configured_path(self):
        custom_path = os.path.join(self.temp_dir, "custom.json")
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump({"db_path": custom_path}, f)

        self.assertEqual(main.get_db_path(), custom_path)

    def test_load_data_returns_empty_dict_when_db_missing(self):
        self.assertEqual(main.load_data(), main.empty_data())

    def test_load_data_normalizes_legacy_json(self):
        self.write_db({"demo": "print('hi')"})

        data = main.load_data()

        self.assert_v2_snippet(data, "demo", "print('hi')")

    def test_load_data_reads_v2_json(self):
        self.write_db(
            {
                "__schema_version": 2,
                "snippets": {
                    "demo": {
                        "code": "console.log('hi')",
                        "language": "javascript",
                        "note": "browser",
                        "created_at": "2026-07-08T18:00:00",
                        "updated_at": "2026-07-08T18:01:00",
                    }
                },
            }
        )

        data = main.load_data()

        self.assert_v2_snippet(data, "demo", "console.log('hi')", "javascript", "browser")

    def test_load_data_reports_broken_json(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            f.write("{broken")

        with self.assertRaises(main.SnipError):
            main.load_data()

    def test_load_data_reports_unknown_structure(self):
        self.write_db({"__schema_version": 1, "items": []})

        with self.assertRaises(main.SnipError):
            main.load_data()

    def test_load_data_reports_missing_snippets_field(self):
        self.write_db({"__schema_version": 2})

        with self.assertRaises(main.SnipError):
            main.load_data()

    def test_add_snippet_saves_new_tag(self):
        with (
            patch("builtins.input", side_effect=["print('hi')", "END"]),
            patch.object(main, "now_iso", return_value="2026-07-08T18:00:00"),
        ):
            main.add_snippet("demo", language="python", note="hello")

        self.assert_v2_snippet(self.read_db(), "demo", "print('hi')", "python", "hello")

    def test_add_snippet_refuses_empty_tag(self):
        with self.assertRaises(main.SnipError):
            main.add_snippet(" ")

    def test_add_snippet_refuses_overwrite_by_default(self):
        self.write_db({"demo": "old"})

        with patch("builtins.input", side_effect=["new", "END", ""]):
            main.add_snippet("demo")

        self.assertEqual(self.read_db(), {"demo": "old"})

    def test_add_snippet_migrates_legacy_data_when_saved(self):
        self.write_db({"demo": "old"})

        with patch("builtins.input", side_effect=["new", "END"]):
            main.add_snippet("other")

        data = self.read_db()
        self.assert_v2_snippet(data, "demo", "old")
        self.assert_v2_snippet(data, "other", "new")

    def test_edit_snippet_updates_code_and_metadata(self):
        self.write_db(
            {
                "__schema_version": 2,
                "snippets": {
                    "demo": {
                        "code": "old",
                        "language": "python",
                        "note": "old note",
                        "created_at": "2026-07-08T18:00:00",
                        "updated_at": "2026-07-08T18:00:00",
                    }
                },
            }
        )

        with (
            patch("builtins.input", side_effect=["new", "END"]),
            patch.object(main, "now_iso", return_value="2026-07-08T19:00:00"),
        ):
            main.edit_snippet("demo", language="javascript", note="new note")

        snippet = self.read_db()["snippets"]["demo"]
        self.assertEqual(snippet["code"], "new")
        self.assertEqual(snippet["language"], "javascript")
        self.assertEqual(snippet["note"], "new note")
        self.assertEqual(snippet["created_at"], "2026-07-08T18:00:00")
        self.assertEqual(snippet["updated_at"], "2026-07-08T19:00:00")

    def test_delete_snippet_removes_existing_tag(self):
        self.write_db({"demo": "print('hi')"})

        main.delete_snippet("demo")

        self.assertEqual(self.read_db(), main.empty_data())

    def test_search_matches_tag_note_and_code(self):
        self.write_db(
            {
                "__schema_version": 2,
                "snippets": {
                    "alpha": main.make_snippet("print('one')", note="first"),
                    "beta": main.make_snippet("console.log('two')", language="javascript"),
                },
            }
        )

        with patch.object(main, "add_snippet_row") as add_row:
            main.search_snippet("console")

        self.assertEqual(add_row.call_count, 1)
        self.assertEqual(add_row.call_args.args[2], "beta")

    def test_list_filters_by_language(self):
        self.write_db(
            {
                "__schema_version": 2,
                "snippets": {
                    "py": main.make_snippet("print('hi')", language="python"),
                    "js": main.make_snippet("console.log('hi')", language="javascript"),
                },
            }
        )

        with patch.object(main, "add_snippet_row") as add_row:
            main.list_snippet(language="javascript")

        self.assertEqual(add_row.call_count, 1)
        self.assertEqual(add_row.call_args.args[2], "js")

    def test_export_outputs_v2_json(self):
        self.write_db({"demo": "print('hi')"})
        export_path = os.path.join(self.temp_dir, "export.json")

        main.export_snippets(export_path)

        with open(export_path, "r", encoding="utf-8") as f:
            exported = json.load(f)
        self.assert_v2_snippet(exported, "demo", "print('hi')")

    def test_import_skips_duplicates_by_default(self):
        self.write_db({"demo": "old"})
        import_path = os.path.join(self.temp_dir, "import.json")
        with open(import_path, "w", encoding="utf-8") as f:
            json.dump({"demo": "new", "other": "value"}, f)

        main.import_snippets(import_path)

        data = self.read_db()
        self.assert_v2_snippet(data, "demo", "old")
        self.assert_v2_snippet(data, "other", "value")

    def test_import_overwrites_duplicates_when_requested(self):
        self.write_db({"demo": "old"})
        import_path = os.path.join(self.temp_dir, "import.json")
        with open(import_path, "w", encoding="utf-8") as f:
            json.dump({"demo": "new"}, f)

        main.import_snippets(import_path, overwrite=True)

        self.assert_v2_snippet(self.read_db(), "demo", "new")

    def test_config_command_writes_config_file(self):
        custom_path = os.path.join(self.temp_dir, "custom.json")

        self.assertEqual(main.main(["config", custom_path]), 0)

        with open(self.config_path, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"db_path": custom_path})

    def test_parser_supports_help_and_version(self):
        with (
            patch("sys.stdout", new_callable=StringIO),
            self.assertRaises(SystemExit) as help_exit,
        ):
            main.main(["--help"])
        with (
            patch("sys.stdout", new_callable=StringIO),
            self.assertRaises(SystemExit) as version_exit,
        ):
            main.main(["--version"])

        self.assertEqual(help_exit.exception.code, 0)
        self.assertEqual(version_exit.exception.code, 0)

    def test_find_falls_back_when_language_is_unknown(self):
        self.write_db(
            {
                "__schema_version": 2,
                "snippets": {
                    "demo": main.make_snippet("hello", language="unknown-language")
                },
            }
        )

        main.find_snippet("demo")

    def test_argparse_commands_accept_shortcut_arguments(self):
        parser = main.build_parser()

        self.assertEqual(parser.parse_args(["find", "demo"]).tag, "demo")
        self.assertEqual(parser.parse_args(["delete", "demo"]).tag, "demo")
        self.assertEqual(parser.parse_args(["add", "demo"]).tag, "demo")
        self.assertEqual(parser.parse_args(["edit", "demo"]).tag, "demo")
        self.assertEqual(parser.parse_args(["search", "demo"]).keyword, "demo")
        self.assertEqual(parser.parse_args(["list", "--lang", "python"]).lang, "python")
        self.assertEqual(parser.parse_args(["config", self.db_path]).path, self.db_path)
        self.assertEqual(parser.parse_args(["export", self.db_path]).path, self.db_path)
        self.assertEqual(parser.parse_args(["import", self.db_path]).path, self.db_path)
        self.assertTrue(parser.parse_args(["import", self.db_path, "--overwrite"]).overwrite)


if __name__ == "__main__":
    unittest.main()
