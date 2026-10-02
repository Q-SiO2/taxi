from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "validate_mobile_live_updates", Path(__file__).resolve().parents[1] / "validate_mobile_live_updates.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class LiveUpdateSourceValidationTest(unittest.TestCase):
    def test_current_repository_wiring(self) -> None:
        MODULE.validate_mobile_live_updates()

    def test_regressions_are_rejected(self) -> None:
        mutations = (
            ("android", "LaunchedEffect(dependencies, liveUpdatesEnabled)", "LaunchedEffect(true)"),
            ("ios", "LaunchedEffect(dependencies, liveUpdatesEnabled)", "LaunchedEffect(true)"),
            ("android", "currentCoroutineContext().ensureActive()", "Unit"),
            ("ios", "owner == dependencies.appCoordinator.liveSessionLifetime.value", "true"),
            ("subscription", "lifetime.collectLatest", "lifetime.collect"),
            ("subscription", "if (!owner.active)", "if (false)"),
            ("subscription", "waitForRetry(retry.nextDelayMillis())", "Unit"),
            ("subscription", "withTimeoutOrNull(connectTimeoutMillis)", "run"),
            ("subscription", "withTimeoutOrNull(refreshTimeoutMillis)", "run"),
            ("subscription", "socket.cancelAndJoin()", "Unit"),
            ("subscription", "AppActionKind.LOGOUT", "AppActionKind.REFRESH"),
            ("gateway", "catch (error: CancellationException)", "catch (error: IllegalStateException)"),
            ("gateway", "onConnected()", "Unit"),
            ("gateway", "for (frame in incoming)", "for (frame in emptyList())"),
            ("authentication", "sessionMutex.withLock", "run"),
            ("authentication", "!current.ending", "true"),
            ("authentication", "ending = true", "ending = false"),
            ("lifetime", "val generation: Long", "val token: String"),
            ("coordinator", "liveSubscription?.run(onRefresh)", "Unit"),
            ("coordinator", "authentication.beginSessionEnd()", "Unit"),
            ("coordinator", "suspend fun logout(): AppUiState", "suspend fun signOut(): AppUiState"),
        )
        for name, before, after in mutations:
            with self.subTest(source=name, mutation=before), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for source_name, relative in MODULE.SOURCES.items():
                    content = (MODULE.ROOT / relative).read_text(encoding="utf-8")
                    if source_name == name:
                        self.assertIn(before, content)
                        content = content.replace(before, after)
                    target = root / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                with self.assertRaises(MODULE.LiveUpdateConfigurationError):
                    MODULE.validate_mobile_live_updates(root)

    def test_missing_source_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(MODULE.LiveUpdateConfigurationError):
                MODULE.validate_mobile_live_updates(Path(directory))


if __name__ == "__main__":
    unittest.main()
