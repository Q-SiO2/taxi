from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "run-android-device.ps1"


class AndroidDeviceLauncherSourceTests(unittest.TestCase):
    def test_launcher_has_a_bounded_post_build_reconnect_wait(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("DeviceReconnectTimeoutSeconds", source)
        self.assertIn("$reconnectDeadline", source)
        self.assertIn("Start-Sleep -Seconds 2", source)

    def test_launcher_preserves_the_original_authorized_device_identity(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("$currentDevices[0] -eq $connectedDevices[0]", source)
        self.assertIn("Refusing to install on another device", source)

    def test_launcher_restores_adb_reverse_after_a_reconnect(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        build_end = source.index("$reconnectDeadline")

        self.assertIn(
            'Invoke-CheckedCommand $adb reverse "tcp:$ApiPort" "tcp:$ApiPort"',
            source[build_end:],
        )


if __name__ == "__main__":
    unittest.main()
