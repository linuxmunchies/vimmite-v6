// Give a newly-created Application Launcher the Vimmite mark while preserving
// any icon the user has selected explicitly.
if (applet.readConfig("icon", "start-here-kde") == "start-here-kde" ||
    applet.readConfig("icon", "start-here-kde") == "start-here") {
    applet.currentConfigGroup = ["General"]
    applet.writeConfig("icon", "start-here-vimmite")
}
