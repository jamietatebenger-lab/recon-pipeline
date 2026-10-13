"""Pure standard-library tests; do not install or execute reconnaissance tools."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "doctor.py"
sys.path.insert(0, str(ROOT / "scripts"))
import doctor


class DoctorTests(unittest.TestCase):
    def test_offline_diagnostics_do_not_touch_network(self):
        def forbidden_lookup(*args, **kwargs):
            raise AssertionError("unexpected DNS request")
        result = doctor.diagnose(offline=True, root=ROOT, dns_lookup=forbidden_lookup)
        self.assertFalse(any(item["name"].startswith("dns:") for item in result))
        self.assertTrue(any(item["name"] == "python" for item in result))

    def test_missing_required_files_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = doctor.diagnose(offline=True, root=Path(tmp))
            self.assertTrue(any(r["status"] == "error" and r["name"] == "Pipfile" for r in result))

    def test_dns_errors_do_not_crash_doctor(self):
        def fail(*_a, **_kw):
            raise OSError("test offline")
        result = doctor.diagnose(offline=False, root=ROOT, dns_lookup=fail)
        dns = [r for r in result if r["name"].startswith("dns:")]
        self.assertEqual(2, len(dns))
        self.assertTrue(all(r["status"] == "error" for r in dns))

    def test_json_output(self):
        p = subprocess.run([sys.executable, str(SCRIPT), "--offline", "--json"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, p.returncode, p.stderr + p.stdout)
        self.assertIn('"name": "python"', p.stdout)


if __name__ == "__main__":
    unittest.main()
