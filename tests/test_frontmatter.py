"""Tests for noesis_harness.frontmatter.

The parser and emitter are pure and deterministic; these tests pin the
tolerant-parse and quote-safe-emit contract, including the YAML 1.1
ambiguity defenses.
"""

import unittest
from collections import OrderedDict

from noesis_harness.frontmatter import (
    FrontmatterError,
    parse_frontmatter,
    render_frontmatter,
    roundtrip,
    yaml_scalar,
)


class TestParseFrontmatter(unittest.TestCase):
    def test_no_frontmatter_returns_empty_and_original(self):
        text = "plain text\nwithout header\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {})
        self.assertEqual(body, text)

    def test_no_frontmatter_when_delimiter_not_first_line(self):
        text = "\n---\ntitle: x\n---\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {})
        self.assertEqual(body, text)

    def test_basic_key_value(self):
        text = "---\ntitle: Hello\ncount: 3\n---\nbody\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"title": "Hello", "count": 3})
        self.assertEqual(body, "body\n")

    def test_quoted_value_with_colon(self):
        text = '---\nurl: "http://example.com:8080/x"\n---\n'
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["url"], "http://example.com:8080/x")

    def test_single_quoted_value(self):
        text = "---\nname: 'it''s fine'\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["name"], "it's fine")

    def test_inline_list(self):
        text = "---\ntags: [alpha, 'beta gamma', delta]\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["tags"], ["alpha", "beta gamma", "delta"])

    def test_inline_list_with_quoted_comma(self):
        text = '---\ntags: ["a,b", c]\n---\n'
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["tags"], ["a,b", "c"])

    def test_empty_list(self):
        text = "---\ntags: []\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["tags"], [])

    def test_bool_variants(self):
        text = "---\na: true\nb: FALSE\nc: True\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertIs(fields["a"], True)
        self.assertIs(fields["b"], False)
        self.assertIs(fields["c"], True)

    def test_null_variants(self):
        text = "---\na: null\nb: NULL\nc: ~\nd: None\ne:\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertIsNone(fields["a"])
        self.assertIsNone(fields["b"])
        self.assertIsNone(fields["c"])
        self.assertIsNone(fields["d"])
        self.assertEqual(fields["e"], "")

    def test_integer_and_float(self):
        text = "---\ni: 42\nn: -7\nf: 3.14\ng: -0.5\ne: 1e3\n---\n"
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["i"], 42)
        self.assertIsInstance(fields["i"], int)
        self.assertEqual(fields["n"], -7)
        self.assertEqual(fields["f"], 3.14)
        self.assertIsInstance(fields["f"], float)
        self.assertEqual(fields["g"], -0.5)
        self.assertEqual(fields["e"], 1000.0)

    def test_comment_stripping(self):
        text = (
            "---\n"
            "a: value # trailing comment\n"
            'b: "value # not a comment"\n'
            'c: "quoted" # comment after quotes\n'
            "d: plain\n"
            "---\n"
        )
        fields, _ = parse_frontmatter(text)
        self.assertEqual(fields["a"], "value")
        self.assertEqual(fields["b"], "value # not a comment")
        self.assertEqual(fields["c"], "quoted")
        self.assertEqual(fields["d"], "plain")

    def test_unterminated_header_falls_back_gracefully(self):
        text = "---\na: 1\nb: 2\nbody line without colon\nmore\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"a": 1, "b": 2})
        self.assertEqual(body, "body line without colon\nmore\n")

    def test_unterminated_header_stops_at_blank_line(self):
        text = "---\na: 1\n\nrest of body\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"a": 1})
        self.assertEqual(body, "rest of body\n")

    def test_missing_colon_lines_are_ignored(self):
        text = "---\na: 1\nthis line is junk\nb: 2\n---\nafter\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"a": 1, "b": 2})
        self.assertEqual(body, "after\n")

    def test_empty_frontmatter_block(self):
        text = "---\n---\nbody\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {})
        self.assertEqual(body, "body\n")

    def test_body_leading_newlines_stripped(self):
        text = "---\na: 1\n---\n\n\nbody\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"a": 1})
        self.assertEqual(body, "body\n")

    def test_crlf_line_endings(self):
        text = "---\r\ntitle: x\r\n---\r\nbody\r\n"
        fields, body = parse_frontmatter(text)
        self.assertEqual(fields, {"title": "x"})
        self.assertEqual(body, "body\n")

    def test_non_string_raises(self):
        for bad in (None, b"---\n", 123, ["---"]):
            with self.assertRaises(FrontmatterError):
                parse_frontmatter(bad)


class TestYamlScalar(unittest.TestCase):
    def test_scalar_quotes_ambiguous_words(self):
        for word in ("yes", "NO", "on", "Off", "true", "false", "null", "~",
                     "None"):
            self.assertEqual(yaml_scalar(word), '"%s"' % word)

    def test_scalar_empty_string(self):
        self.assertEqual(yaml_scalar(""), '""')

    def test_scalar_numeric_looking_strings_quoted(self):
        self.assertEqual(yaml_scalar("123"), '"123"')
        self.assertEqual(yaml_scalar("1.5"), '"1.5"')
        self.assertEqual(yaml_scalar("-7"), '"-7"')

    def test_scalar_numbers_and_bools(self):
        self.assertEqual(yaml_scalar(None), "null")
        self.assertEqual(yaml_scalar(True), "true")
        self.assertEqual(yaml_scalar(False), "false")
        self.assertEqual(yaml_scalar(42), "42")
        self.assertEqual(yaml_scalar(-1), "-1")
        self.assertEqual(yaml_scalar(3.5), "3.5")

    def test_scalar_plain_string_unquoted(self):
        self.assertEqual(yaml_scalar("hello"), "hello")
        self.assertEqual(yaml_scalar("hello world"), "hello world")

    def test_scalar_special_chars_quoted(self):
        for text in ("a:b", "#hash", "a,b", "{x}", "[x]", "a*b", "a&b",
                     "100%", "a|b", "a>b", "user@host", "a!b"):
            emitted = yaml_scalar(text)
            self.assertTrue(emitted.startswith('"') and emitted.endswith('"'),
                            msg=repr(text))

    def test_scalar_inner_quotes_doubled(self):
        self.assertEqual(yaml_scalar('say "hi"'), '"say ""hi"""')

    def test_scalar_leading_trailing_space_quoted(self):
        self.assertEqual(yaml_scalar(" padded "), '" padded "')

    def test_scalar_list_inline(self):
        self.assertEqual(yaml_scalar(["a", "b"]), "[a, b]")
        self.assertEqual(yaml_scalar([]), "[]")
        self.assertEqual(yaml_scalar(["yes"]), '["yes"]')


class TestRenderAndRoundtrip(unittest.TestCase):
    def test_plain_dict_keys_sorted(self):
        text = render_frontmatter({"z": 1, "a": 2, "m": 3})
        lines = text.splitlines()
        self.assertEqual(lines[0], "---")
        self.assertEqual(lines[1], "a: 2")
        self.assertEqual(lines[2], "m: 3")
        self.assertEqual(lines[3], "z: 1")
        self.assertEqual(lines[4], "---")

    def test_ordered_mapping_preserves_order(self):
        fields = OrderedDict([("z", 1), ("a", 2)])
        text = render_frontmatter(fields)
        lines = text.splitlines()
        self.assertEqual(lines[1], "z: 1")
        self.assertEqual(lines[2], "a: 2")

    def test_render_then_parse_roundtrip_preserves_types(self):
        fields = {
            "title": "A title",
            "count": 3,
            "ratio": 1.25,
            "enabled": True,
            "missing": None,
            "tags": ["x", "y"],
            "empty": "",
        }
        parsed, body = parse_frontmatter(render_frontmatter(fields, "payload"))
        self.assertEqual(parsed, fields)
        self.assertEqual(body, "payload")
        self.assertIsInstance(parsed["count"], int)
        self.assertIsInstance(parsed["ratio"], float)
        self.assertIs(parsed["enabled"], True)
        self.assertIsNone(parsed["missing"])
        self.assertEqual(parsed["tags"], ["x", "y"])

    def test_roundtrip_helper(self):
        fields = {"b": True, "n": None, "s": "yes", "i": 7}
        self.assertEqual(roundtrip(fields), fields)

    def test_render_body_separated_by_blank_line(self):
        text = render_frontmatter({"a": 1}, "hello")
        self.assertEqual(text, "---\na: 1\n---\n\nhello")

    def test_render_empty_body_ends_with_blank_line(self):
        text = render_frontmatter({"a": 1})
        self.assertEqual(text, "---\na: 1\n---\n\n")


if __name__ == "__main__":
    unittest.main()
