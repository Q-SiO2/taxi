rootProject.name = "TaxiMobile"

pluginManagement {
    // AGP 9.0.1 embeds R8 9.0.32, which cannot preserve Kotlin 2.4 metadata.
    // Use Google's documented pluginManagement override, not an AGP/KMP upgrade
    // or disabled shrinking. Keep the resolved-plugin and mapping-header checks
    // in sync when deliberately upgrading this reviewed compiler.
    buildscript {
        repositories {
            google()
        }
        dependencies {
            classpath("com.android.tools:r8:9.1.56")
        }
    }
    repositories {
        google {
            mavenContent {
                includeGroupAndSubgroups("androidx")
                includeGroupAndSubgroups("com.android")
                includeGroupAndSubgroups("com.google")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositories {
        google {
            mavenContent {
                includeGroupAndSubgroups("androidx")
                includeGroupAndSubgroups("com.android")
                includeGroupAndSubgroups("com.google")
            }
        }
        mavenCentral()
    }
}

plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "1.0.0"
}

include(":androidApp")
include(":desktopApp")
include(":shared")
include(":webApp")
