import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";


const loaderUrl = new URL(
    "../webApp/src/webMain/resources/compatibility.js",
    import.meta.url,
);
const loaderSource = await readFile(loaderUrl, "utf8");


function response(status, extra = {}) {
    return {
        ok: true,
        async json() {
            return { status, ...extra };
        },
    };
}


async function settle() {
    // The loader starts an async check from its IIFE. Repeated microtask turns
    // make that check deterministic without sleeping or exposing internals.
    for (let turn = 0; turn < 8; turn += 1) {
        await Promise.resolve();
    }
}


async function runLoader({
    pathname = "/operations",
    hash = "",
    hostname = "app.test",
    origin = "https://app.test",
    version = "1.0.0",
    build = "1",
    fetchResults = [response("SUPPORTED")],
} = {}) {
    const message = { textContent: "" };
    const actionListeners = new Map();
    const action = {
        hidden: true,
        textContent: "",
        addEventListener(name, listener) {
            actionListeners.set(name, listener);
        },
        click() {
            actionListeners.get("click")?.();
        },
    };
    const boot = {
        querySelector(selector) {
            return selector === "span" ? message : null;
        },
    };
    const scripts = [];
    const document = {
        getElementById(id) {
            if (id === "boot-status") return boot;
            if (id === "boot-action") return action;
            return null;
        },
        querySelector(selector) {
            if (selector === "meta[name='taximobile-client-version']") {
                return { content: version };
            }
            if (selector === "meta[name='taximobile-client-build']") {
                return { content: build };
            }
            return null;
        },
        createElement(tag) {
            assert.equal(tag, "script");
            const listeners = new Map();
            return {
                src: "",
                async: true,
                addEventListener(name, listener) {
                    listeners.set(name, listener);
                },
                dispatch(name) {
                    listeners.get(name)?.();
                },
            };
        },
        body: {
            appendChild(script) {
                scripts.push(script);
            },
        },
    };

    const calls = [];
    const pendingResults = [...fetchResults];
    async function fetch(input, init = {}) {
        calls.push({ input, init });
        const next = pendingResults.shift();
        if (next instanceof Error) throw next;
        assert.notEqual(next, undefined, "unexpected fetch call without a queued result");
        return typeof next === "function" ? next(input, init) : next;
    }

    let reloads = 0;
    const timerIds = [];
    const clearedTimerIds = [];
    const window = {
        location: {
            pathname,
            hash,
            hostname,
            origin,
            href: `${origin}${pathname}${hash}`,
            reload() {
                reloads += 1;
            },
        },
        fetch,
        setTimeout(_callback, _milliseconds) {
            const id = timerIds.length + 1;
            timerIds.push(id);
            return id;
        },
        clearTimeout(id) {
            clearedTimerIds.push(id);
        },
    };

    vm.runInNewContext(loaderSource, {
        AbortController,
        Error,
        Headers,
        Request,
        URL,
        document,
        window,
    }, { filename: loaderUrl.pathname });
    await settle();

    return {
        action,
        calls,
        clearedTimerIds,
        message,
        reloads: () => reloads,
        scripts,
        timerIds,
        window,
    };
}


async function supportedApplicantBootsAndScopesIdentityHeaders() {
    const harness = await runLoader({
        pathname: "/apply/casablanca",
        fetchResults: [
            response("SUPPORTED"),
            response("IGNORED"),
            response("IGNORED"),
            response("IGNORED"),
            response("IGNORED"),
        ],
    });

    assert.equal(harness.scripts.length, 1);
    assert.equal(harness.scripts[0].src, "webApp.js");
    assert.equal(harness.scripts[0].async, false);
    assert.equal(harness.calls[0].input, "https://app.test/api/v1/client-compatibility");
    assert.equal(harness.calls[0].init.credentials, "include");
    const preflightHeaders = new Headers(harness.calls[0].init.headers);
    assert.equal(preflightHeaders.get("X-TaxiMobile-Client"), "WEB_APPLICANT");
    assert.equal(preflightHeaders.get("X-TaxiMobile-Version"), "1.0.0");
    assert.equal(preflightHeaders.get("X-TaxiMobile-Build"), "1");
    assert.deepEqual(harness.clearedTimerIds, harness.timerIds);

    await harness.window.fetch("https://app.test/api/v1/rides", {
        headers: { "X-Request-Trace": "kept" },
    });
    const apiHeaders = new Headers(harness.calls[1].init.headers);
    assert.equal(apiHeaders.get("X-Request-Trace"), "kept");
    assert.equal(apiHeaders.get("X-TaxiMobile-Client"), "WEB_APPLICANT");

    const request = new Request("https://app.test/api/v1/profile", {
        headers: { "X-From-Request": "kept", "X-Override": "old" },
    });
    await harness.window.fetch(request, { headers: { "X-Override": "new" } });
    const requestHeaders = new Headers(harness.calls[2].init.headers);
    assert.equal(requestHeaders.get("X-From-Request"), "kept");
    assert.equal(requestHeaders.get("X-Override"), "new");
    assert.equal(requestHeaders.get("X-TaxiMobile-Client"), "WEB_APPLICANT");

    await harness.window.fetch("https://other.test/api/v1/rides", {
        headers: { "X-External": "kept" },
    });
    const externalHeaders = new Headers(harness.calls[3].init.headers);
    assert.equal(externalHeaders.get("X-External"), "kept");
    assert.equal(externalHeaders.has("X-TaxiMobile-Client"), false);

    await harness.window.fetch("https://app.test/api/v10/not-v1", {});
    const wrongPathHeaders = new Headers(harness.calls[4].init.headers);
    assert.equal(wrongPathHeaders.has("X-TaxiMobile-Client"), false);
}


async function upgradeRequiredBlocksBootAndReloads() {
    const harness = await runLoader({
        fetchResults: [response("UPGRADE_REQUIRED", {
            minimum_version: "2.0.0",
            policy_revision: "2026-09-09.1",
        })],
    });

    assert.equal(harness.scripts.length, 0);
    assert.equal(harness.action.hidden, false);
    assert.equal(harness.action.textContent, "Reload");
    assert.match(harness.message.textContent, /version 2\.0\.0 or later/);
    assert.match(harness.message.textContent, /policy 2026-09-09\.1/);
    harness.action.click();
    assert.equal(harness.reloads(), 1);
}


async function failedCheckRemainsBlockedAndCanRetry() {
    const harness = await runLoader({
        fetchResults: [
            { ok: false, async json() { return {}; } },
            response("UPDATE_AVAILABLE"),
        ],
    });

    assert.equal(harness.scripts.length, 0);
    assert.equal(harness.action.hidden, false);
    assert.equal(harness.action.textContent, "Try again");
    assert.match(harness.message.textContent, /actions remain disabled/);
    harness.action.click();
    await settle();
    assert.equal(harness.calls.length, 2);
    assert.equal(harness.scripts.length, 1);
}


async function unknownPolicyFailsClosed() {
    const harness = await runLoader({ fetchResults: [response("SURPRISE")] });
    assert.equal(harness.scripts.length, 0);
    assert.equal(harness.action.textContent, "Try again");
    assert.match(harness.message.textContent, /cannot verify this release/);
}


async function localOperationsUsesDevelopmentApiWithoutLeakingApplicantRole() {
    const harness = await runLoader({
        hostname: "localhost",
        origin: "http://localhost:8080",
        pathname: "/operations",
    });
    assert.equal(harness.calls[0].input, "http://localhost:8000/api/v1/client-compatibility");
    const headers = new Headers(harness.calls[0].init.headers);
    assert.equal(headers.get("X-TaxiMobile-Client"), "WEB_OPERATIONS");
}


async function applicationLoadFailureReturnsToBlockedReloadState() {
    const harness = await runLoader();
    assert.equal(harness.scripts.length, 1);
    harness.scripts[0].dispatch("error");
    assert.equal(harness.action.hidden, false);
    assert.equal(harness.action.textContent, "Try again");
    assert.match(harness.message.textContent, /could not load this release/);
    harness.action.click();
    assert.equal(harness.reloads(), 1);
}


const scenarios = [
    supportedApplicantBootsAndScopesIdentityHeaders,
    upgradeRequiredBlocksBootAndReloads,
    failedCheckRemainsBlockedAndCanRetry,
    unknownPolicyFailsClosed,
    localOperationsUsesDevelopmentApiWithoutLeakingApplicantRole,
    applicationLoadFailureReturnsToBlockedReloadState,
];

for (const scenario of scenarios) {
    await scenario();
}

console.log(`Web compatibility loader runtime tests passed (${scenarios.length} scenarios).`);
