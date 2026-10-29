import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const source = await readFile(new URL("../webApp/src/webMain/resources/locale.js", import.meta.url), "utf8");

function browser(configurable = true) {
    class Navigator {}
    Object.defineProperty(Navigator.prototype, "languages", {
        configurable,
        get() { return ["fr-MA", "en"]; },
    });
    const events = [];
    const window = { dispatchEvent(event) { events.push(event.type); } };
    const document = { documentElement: { lang: "en", dir: "ltr" } };
    const navigator = new Navigator();
    vm.runInNewContext(source, { window, document, Navigator, navigator, Event: class {
        constructor(type) { this.type = type; }
    } });
    return { window, document, navigator, events };
}

{
    const b = browser();
    assert.deepEqual(Array.from(b.navigator.languages), ["fr-MA", "en"]);
    for (const language of ["en", "fr", "ar"]) {
        assert.equal(b.window.taximobileSetLocale(language), true);
        assert.deepEqual(Array.from(b.navigator.languages), [language]);
        assert.equal(b.document.documentElement.lang, language);
        assert.equal(b.document.documentElement.dir, language === "ar" ? "rtl" : "ltr");
    }
    assert.deepEqual(b.events, ["languagechange", "languagechange", "languagechange"]);
    b.window.taximobileSetLocale("ar");
    assert.equal(b.events.length, 3, "Repeated selection must not emit another locale event");
    assert.equal(b.window.taximobileSetLocale("unsupported"), false);
    assert.equal(b.document.documentElement.lang, "ar");
}
{
    const b = browser(false);
    assert.equal(b.window.taximobileSetLocale("ar"), false);
    assert.deepEqual(Array.from(b.navigator.languages), ["fr-MA", "en"]);
    assert.equal(b.document.documentElement.dir, "ltr");
    assert.equal(b.events.length, 0);
}
console.log("Web locale adapter: system fallback, three choices, direction, event ownership and locked browser checks passed.");
