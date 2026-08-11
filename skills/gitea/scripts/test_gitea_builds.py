import os
import tempfile
import unittest
from pathlib import Path

from gitea_builds import extract_config_path, load_dotfile


class DotfileTests(unittest.TestCase):
    def test_loads_comments_exports_and_quoted_values(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as dotfile:
            dotfile.write(
                '# Gitea settings\n'
                'export GITEA_URL="https://gitea.example.com" # instance\n'
                'GITEA_TOKEN=secret-token\n'
            )
            path = Path(dotfile.name)

        try:
            self.assertEqual(
                load_dotfile(path),
                {
                    'GITEA_URL': 'https://gitea.example.com',
                    'GITEA_TOKEN': 'secret-token',
                },
            )
        finally:
            path.unlink()

    def test_extracts_config_without_changing_other_arguments(self):
        config, args = extract_config_path(
            ['owner', 'repo', '--config', '~/.config/gitea', '--run', '42']
        )
        self.assertEqual(config, '~/.config/gitea')
        self.assertEqual(args, ['owner', 'repo', '--run', '42'])

    def test_environment_values_can_override_dotfile_values(self):
        settings = {
            'GITEA_URL': 'https://from-file.example.com',
            'GITEA_TOKEN': 'from-file',
        }
        old_url = os.environ.get('GITEA_URL')
        old_token = os.environ.get('GITEA_TOKEN')
        try:
            os.environ['GITEA_URL'] = 'https://from-environment.example.com'
            for key, value in settings.items():
                os.environ.setdefault(key, value)
            self.assertEqual(os.environ['GITEA_URL'], 'https://from-environment.example.com')
            self.assertEqual(os.environ['GITEA_TOKEN'], 'from-file')
        finally:
            if old_url is None:
                os.environ.pop('GITEA_URL', None)
            else:
                os.environ['GITEA_URL'] = old_url
            if old_token is None:
                os.environ.pop('GITEA_TOKEN', None)
            else:
                os.environ['GITEA_TOKEN'] = old_token


if __name__ == '__main__':
    unittest.main()
