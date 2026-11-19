"""审计必须识别未暂存文件、二进制嵌入标识、凭据和私人路径。"""
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from audit_release import scan
from release_files import candidates,copy_candidate

class AuditTests(unittest.TestCase):
    def test_credential_formats(self):
        for prefix in ('sk-','ghp_','github_pat_'):
            self.assertIn('服务密钥',scan((prefix+'x'*40).encode()))
    def test_binary_embedded_identifier_is_detected(self):
        self.assertIn('本机隐私标识',scan(b'RIFF\0hidden-id',['hidden-id']))
    def test_private_home_vs_documented_placeholders(self):
        self.assertIn('个人HOME路径',scan(('/Users/'+'someone/private').encode()))
        self.assertEqual(scan(b'/Users/me/example /Users/you/ComicDesk /home/user/demo'),[])
    def test_explicit_privacy_terms(self):
        self.assertIn('本机隐私标识',scan(b'local-team',['local-team']))
    def test_candidate_includes_untracked_and_current_content(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'tracked.txt').write_text('new');(root/'new.txt').write_text('untracked')
            with patch('release_files.subprocess.check_output',return_value=b'tracked.txt\0new.txt\0'):
                self.assertEqual(candidates(root),['new.txt','tracked.txt'])
                target=root/'out';copy_candidate(target,root)
            self.assertEqual((target/'tracked.txt').read_text(),'new');self.assertEqual((target/'new.txt').read_text(),'untracked')
    def test_candidate_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'link.txt').symlink_to(root/'outside.txt')
            with patch('release_files.subprocess.check_output',return_value=b'link.txt\0'):
                with self.assertRaises(ValueError):candidates(root)
