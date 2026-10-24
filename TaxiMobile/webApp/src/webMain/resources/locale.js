/* App-owned Compose browser locale adapter. Loaded before either JS/Wasm bundle. */
(() => {
    "use strict";
    const descriptor = Object.getOwnPropertyDescriptor(Navigator.prototype, "languages");
    let selected = null;
    let languages = null;
    let available = false;
    try {
        if (descriptor && typeof descriptor.get === "function") {
            Object.defineProperty(Navigator.prototype, "languages", {
                ...descriptor,
                get() { return languages || descriptor.get.call(this); }
            });
            available = true;
        }
    } catch (_) { /* The visible language control reports an unavailable adapter. */ }
    window.taximobileSetLocale = (language) => {
        if (!available || !["en", "fr", "ar"].includes(language)) return false;
        document.documentElement.lang = language;
        document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
        if (selected !== language) {
            selected = language;
            languages = Object.freeze([language]);
            window.dispatchEvent(new Event("languagechange"));
        }
        return true;
    };
})();
