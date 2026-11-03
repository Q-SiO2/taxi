// Loading the pinned timezone database is measured by the provider tests.
// Give only that suite a startup allowance; keep Mocha's other defaults.
config.client = config.client || {};
config.client.mocha = config.client.mocha || {};
config.client.mocha.require = [].concat(
    config.client.mocha.require || [],
    require("path").resolve(__dirname, "../../../../webApp/src/webTest/resources/city-time-mocha.js")
);
