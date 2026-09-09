"use strict";

(() => {
    const boot = document.getElementById("boot-status");
    const message = boot?.querySelector("span");
    const action = document.getElementById("boot-action");
    const version = document.querySelector("meta[name='taximobile-client-version']")?.content ?? "";
    const build = document.querySelector("meta[name='taximobile-client-build']")?.content ?? "";
    const path = `/${window.location.pathname.trim().replace(/^\/+|\/+$/g, "").toLowerCase()}`;
    const hash = window.location.hash.trim().toLowerCase().replace(/^#/, "");
    const applicant = path === "/apply" || path.startsWith("/apply/") ||
        hash === "/apply" || hash.startsWith("/apply?");
    const surface = applicant ? "WEB_APPLICANT" : "WEB_OPERATIONS";
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(window.location.hostname.toLowerCase());
    const apiBase = local ? `http://${window.location.hostname}:8000/api/v1` :
        `${window.location.origin.replace(/\/$/, "")}/api/v1`;
    const apiUrl = new URL(apiBase);
    const apiPathPrefix = `${apiUrl.pathname.replace(/\/$/, "")}/`;
    const nativeFetch = window.fetch.bind(window);
    let checking = false;
    let started = false;
    let actionHandler = () => {};

    function show(detail, label, handler) {
        if (message) message.textContent = detail;
        actionHandler = handler ?? (() => {});
        if (!action) return;
        if (label) {
            action.textContent = label;
            action.hidden = false;
        } else {
            action.hidden = true;
        }
    }

    function startApplication() {
        started = true;
        window.fetch = (input, init = {}) => {
            const target = new URL(typeof input === "string" ? input : input.url, window.location.href);
            if (target.origin !== apiUrl.origin || !target.pathname.startsWith(apiPathPrefix)) {
                return nativeFetch(input, init);
            }
            const headers = new Headers(input instanceof Request ? input.headers : undefined);
            new Headers(init.headers).forEach((value, name) => headers.set(name, value));
            headers.set("X-TaxiMobile-Client", surface);
            headers.set("X-TaxiMobile-Version", version);
            headers.set("X-TaxiMobile-Build", build);
            return nativeFetch(input, { ...init, headers });
        };
        const script = document.createElement("script");
        script.src = "webApp.js";
        script.async = false;
        script.addEventListener("error", () => {
            started = false;
            show("TaxiMobile could not load this release.", "Try again", () => window.location.reload());
        });
        document.body.appendChild(script);
    }

    async function checkCompatibility() {
        if (checking || started) return;
        checking = true;
        show("Checking that this TaxiMobile release is supported…");
        try {
            const controller = new AbortController();
            const timeout = window.setTimeout(() => controller.abort(), 10000);
            let response;
            try {
                response = await nativeFetch(`${apiBase}/client-compatibility`, {
                    method: "GET",
                    credentials: "include",
                    signal: controller.signal,
                    headers: {
                        "X-TaxiMobile-Client": surface,
                        "X-TaxiMobile-Version": version,
                        "X-TaxiMobile-Build": build,
                    },
                });
            } finally {
                window.clearTimeout(timeout);
            }
            if (!response.ok) throw new Error("compatibility check failed");
            const policy = await response.json();
            if (policy.status === "UPGRADE_REQUIRED") {
                show(
                    `A newer TaxiMobile release is required. Refresh to load version ` +
                        `${policy.minimum_version} or later (policy ${policy.policy_revision}).`,
                    "Reload",
                    () => window.location.reload(),
                );
            } else if (policy.status === "SUPPORTED" || policy.status === "UPDATE_AVAILABLE") {
                startApplication();
            } else {
                throw new Error("unknown compatibility state");
            }
        } catch (_) {
            show(
                "TaxiMobile cannot verify this release. Sign-in and actions remain disabled.",
                "Try again",
                checkCompatibility,
            );
        } finally {
            checking = false;
        }
    }

    action?.addEventListener("click", () => actionHandler());
    checkCompatibility();
})();
