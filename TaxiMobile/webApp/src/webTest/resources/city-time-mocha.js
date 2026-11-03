/* global mocha */
// Karma loads required files before installing Mocha's BDD globals.
mocha.suite.beforeEach("city-time provider startup", function cityTimeProviderStartupBudget() {
    const current = this.currentTest;
    if (current && current.parent && current.parent.title === "ScheduledCityTimeBrowserTest") {
        current.timeout(10_000);
    }
});
