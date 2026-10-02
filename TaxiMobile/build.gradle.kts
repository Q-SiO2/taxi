import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.OutputFile
import org.gradle.api.tasks.TaskAction
import java.security.MessageDigest

plugins {
    // this is necessary to avoid the plugins to be loaded multiple times
    // in each subproject's classloader
    alias(libs.plugins.androidApplication) apply false
    alias(libs.plugins.androidMultiplatformLibrary) apply false
    alias(libs.plugins.composeMultiplatform) apply false
    alias(libs.plugins.composeCompiler) apply false
    alias(libs.plugins.kotlinJvm) apply false
    alias(libs.plugins.kotlinMultiplatform) apply false
    alias(libs.plugins.firebaseCrashlytics) apply false
}

abstract class VerifyAndroidShrinker : DefaultTask() {
    @get:Input
    abstract val expectedR8Version: Property<String>

    @get:Input
    abstract val kotlinVersion: Property<String>

    @get:OutputFile
    abstract val evidenceFile: RegularFileProperty

    @TaskAction
    fun verify() {
        val expected = expectedR8Version.get()
        val kotlin = kotlinVersion.get()
        if (expected != "9.1.56" || !Regex("2\\.4\\.[0-9]+").matches(kotlin)) {
            throw GradleException("Review the R8/Kotlin compatibility contract before upgrading the compiler.")
        }
        // Resolve through AGP's plugin loader: a downloaded jar or CLI version
        // alone is not evidence that Android build tasks actually use it.
        val versionClass = Class.forName(
            "com.android.tools.r8.Version", true,
            com.android.build.gradle.AppPlugin::class.java.classLoader,
        )
        val label = versionClass.getMethod("getVersionString").invoke(null) as String
        // R8 includes its build hash/bot label after the numeric version.
        // Keep prerelease suffixes intact so a -dev build cannot pass this pin.
        val actual = label.substringBefore(" ")
        if (actual != expected) {
            throw GradleException("Android plugin resolved R8 $actual; the reviewed Kotlin 2.4 compiler is $expected.")
        }
        val compilerJar = java.io.File(versionClass.protectionDomain.codeSource.location.toURI())
        if (!compilerJar.isFile) {
            throw GradleException("The resolved R8 compiler must have a readable artifact identity.")
        }
        val digest = MessageDigest.getInstance("SHA-256")
        compilerJar.inputStream().use { input ->
            val buffer = ByteArray(1024 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        val hash = digest.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val output = evidenceFile.get().asFile
        output.parentFile.mkdirs()
        output.writeText(
            """
            {
              "schema_version": 1,
              "evidence_level": "ANDROID_RESOLVED_SHRINKER",
              "deployment_accepted": false,
              "distribution_eligible": false,
              "kotlin_version": "$kotlin",
              "r8_version": "$actual",
              "resolution_scope": "AGP_PLUGIN_CLASSLOADER",
              "compiler_artifact_bytes": ${compilerJar.length()},
              "compiler_artifact_sha256": "$hash"
            }
            """.trimIndent() + "\n",
        )
        logger.lifecycle("Verified Android plugin R8 $actual for Kotlin $kotlin; distribution remains unaccepted.")
    }
}

val verifyAndroidShrinker by tasks.registering(VerifyAndroidShrinker::class) {
    group = "verification"
    description = "Verify the actual Android plugin shrinker version and artifact identity."
    expectedR8Version.set("9.1.56")
    kotlinVersion.set(libs.versions.kotlin.asProvider())
    evidenceFile.set(layout.buildDirectory.file("reports/android-shrinker/resolved-shrinker.json"))
    // Check the loaded compiler in every invocation, not a stale up-to-date report.
    outputs.upToDateWhen { false }
}
