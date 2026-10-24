// Internal rehearsal only: do not expose source/static files to the LAN or
// launch an unsolicited native browser window. Production bundling is unchanged.
if (config.devServer) {
    const path = require("path");
    const projectRoot = path.resolve(__dirname, "../../../..");
    config.devServer.host = "127.0.0.1";
    config.devServer.allowedHosts = ["127.0.0.1", "localhost"];
    config.devServer.open = false;
    if (Array.isArray(config.devServer.static)) {
        config.devServer.static = config.devServer.static.filter((entry) => {
            const directory = typeof entry === "string" ? entry : entry.directory;
            return !directory || path.resolve(directory) !== projectRoot;
        });
    }
}
