"""Parse complete CI sources before checking their expression semantics."""
from pathlib import Path
import unittest

import yaml


SKILL_ROOT = Path(__file__).resolve().parents[2]


def repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / '.github/workflows/harness-ci.yml').is_file():
            return candidate
    raise AssertionError('source workflow is unavailable')


class CIWorkflowYAMLTests(unittest.TestCase):
    def test_complete_workflow_and_template_parse_with_single_line_expressions(self):
        sources = (
            (repository_root() / '.github/workflows/harness-ci.yml', 'quality'),
            (SKILL_ROOT / 'assets/templates/PROJECT_CI.template.yml', 'checks'),
        )
        for path, job in sources:
            with self.subTest(path=path):
                document = yaml.safe_load(path.read_text(encoding='utf-8'))
                self.assertIsInstance(document, dict)
                group = document['concurrency']['group']
                base = document['jobs'][job]['env']['DIFF_BASE_SHA']
                for expression in (group, base):
                    self.assertIsInstance(expression, str)
                    self.assertNotIn('\n', expression)
                    self.assertTrue(expression.endswith('}}'))
                self.assertIn("github.event_name == 'workflow_dispatch'", group)
                self.assertIn('github.ref', group)
                self.assertIn('inputs.base_sha', base)
                self.assertIn('github.event.pull_request.base.sha', base)
                self.assertIn('github.event.merge_group.base_sha', base)
                # Neither the source workflow nor the consumer template has a push trigger.
                self.assertNotIn('github.event.before', base)

    def test_parser_rejects_the_original_unindented_expression_closures(self):
        malformed = (
            "concurrency:\n  group: prefix-${{\n    github.ref\n  }}\n",
            "env:\n  DIFF_BASE_SHA: ${{\n    github.event.before\n  }}\n",
        )
        for document in malformed:
            with self.subTest(document=document):
                with self.assertRaises(yaml.YAMLError):
                    yaml.safe_load(document)


if __name__ == '__main__':
    unittest.main()
