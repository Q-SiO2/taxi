"""Run the actual webpack fragment without building the application."""

import json
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[3]
FRAGMENT = ROOT / "TaxiMobile/webApp/webpack.config.d/local-development.js"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "Node runtime is required.")
class UnionDemoWebConfigurationTests(unittest.TestCase):
    def evaluate(self, config):
        script = """
const fs = require('fs'), vm = require('vm'), path = require('path');
const config = JSON.parse(process.argv[2]);
const context = {config, require, __dirname: path.resolve('fixture/build/js/packages/app')};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
process.stdout.write(JSON.stringify(config));
"""
        result = subprocess.run(
            [NODE, "-e", script, str(FRAGMENT), json.dumps(config)],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_dev_server_is_loopback_only_and_does_not_open_native_browser(self):
        result = self.evaluate({"devServer": {"open": True, "host": "0.0.0.0", "port": 8080}})
        self.assertEqual(result["devServer"]["host"], "127.0.0.1")
        self.assertEqual(result["devServer"]["allowedHosts"], ["127.0.0.1", "localhost"])
        self.assertFalse(result["devServer"]["open"])
        self.assertEqual(result["devServer"]["port"], 8080)

    def test_app_source_root_is_not_a_static_asset_directory(self):
        root = str((Path.cwd() / "fixture").resolve())
        assets = str((Path(root) / "generated-assets").resolve())
        result = self.evaluate({"devServer": {"static": [
            {"directory": root}, {"directory": assets, "watch": False}, root,
        ]}})
        self.assertEqual(result["devServer"]["static"], [{"directory": assets, "watch": False}])

    def test_production_configuration_is_unchanged(self):
        original = {"mode": "production", "output": {"filename": "webApp.js"}}
        self.assertEqual(self.evaluate(original), original)


if __name__ == "__main__":
    unittest.main()
