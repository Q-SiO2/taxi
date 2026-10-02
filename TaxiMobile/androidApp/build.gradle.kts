import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import java.net.URI
import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.provider.Property
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.InputDirectory
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction
import java.security.MessageDigest

abstract class ValidateTaxiMobileReleaseConfiguration : DefaultTask() {
    @get:Input
    abstract val apiBaseUrl: Property<String>

    @get:Input
    abstract val mapStyleUrl: Property<String>

    @get:Input
    abstract val versionCodeValue: Property<String>

    @get:Input
    abstract val versionNameValue: Property<String>

    @get:Input
    abstract val firebaseConfigurationPresent: Property<Boolean>

    @get:Input
    abstract val signingConfigurationPresent: Property<Boolean>

    @get:Input
    abstract val crashReportingEnabled: Property<Boolean>

    @get:Input
    abstract val allowMissingFirebaseVerification: Property<Boolean>

    @get:Input
    abstract val allowUnsignedReleaseVerification: Property<Boolean>

    @TaskAction
    fun validate() {
        fun requireHttpsUrl(name: String, value: String, requireRootPath: Boolean) {
            val uri = try {
                URI(value)
            } catch (error: Exception) {
                throw GradleException("$name must be a valid absolute HTTPS URL.", error)
            }
            if (
                uri.scheme != "https" || uri.host.isNullOrBlank() || uri.userInfo != null || uri.fragment != null ||
                uri.host.endsWith(".invalid") || (requireRootPath && uri.path !in listOf("", "/"))
            ) {
                throw GradleException(
                    "$name must use an explicit production HTTPS host without credentials, fragments, or .invalid placeholders.",
                )
            }
            if (requireRootPath && uri.query != null) {
                throw GradleException("$name must not include a query string; it is the API origin only.")
            }
        }

        if (apiBaseUrl.get().isBlank() || mapStyleUrl.get().isBlank()) {
            throw GradleException(
                "Release builds require taximobileReleaseApiBaseUrl and taximobileReleaseMapStyleUrl.",
            )
        }
        requireHttpsUrl("taximobileReleaseApiBaseUrl", apiBaseUrl.get(), requireRootPath = true)
        requireHttpsUrl("taximobileReleaseMapStyleUrl", mapStyleUrl.get(), requireRootPath = false)
        if (versionCodeValue.get().toIntOrNull()?.let { it > 0 } != true) {
            throw GradleException("Release builds require a positive integer taximobileVersionCode.")
        }
        if (!Regex("(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(\\.(0|[1-9][0-9]*))?").matches(versionNameValue.get())) {
            throw GradleException("Release builds require a versioned taximobileVersionName such as 1.0.0.")
        }
        if (!firebaseConfigurationPresent.get() && !allowMissingFirebaseVerification.get()) {
            throw GradleException(
                "Release builds require flavor-aware Firebase configuration. " +
                    "Only CI artifact verification may set taximobileAllowMissingFirebaseForVerification=true.",
            )
        }
        if (!signingConfigurationPresent.get() && !allowUnsignedReleaseVerification.get()) {
            throw GradleException(
                "Release builds require external signing properties. " +
                    "Only CI artifact verification may set taximobileAllowUnsignedReleaseForVerification=true.",
            )
        }
        if (!crashReportingEnabled.get() && !allowMissingFirebaseVerification.get()) {
            throw GradleException(
                "Distributable release builds require taximobileCrashReportingEnabled=true. " +
                    "Providerless CI verification artifacts may leave it disabled.",
            )
        }
    }
}

abstract class ValidateRoleLauncherAssets : DefaultTask() {
    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val androidAppDirectory: DirectoryProperty

    @TaskAction
    fun validate() {
        val appDirectory = androidAppDirectory.get().asFile
        val roleRoots = listOf("passenger", "driver").associateWith { role ->
            appDirectory.resolve("src/$role/res")
        }
        val required = listOf(
            "drawable/ic_launcher_background.xml",
            "drawable/ic_launcher_foreground.xml",
            "drawable/ic_launcher_legacy.xml",
            "mipmap-anydpi/ic_launcher.xml",
            "mipmap-anydpi/ic_launcher_round.xml",
            "mipmap-anydpi-v26/ic_launcher.xml",
            "mipmap-anydpi-v26/ic_launcher_round.xml",
        )
        roleRoots.forEach { (role, root) ->
            required.forEach { relative ->
                if (!root.resolve(relative).isFile) {
                    throw GradleException("Missing $role launcher resource: $relative")
                }
            }
            val background = root.resolve("drawable/ic_launcher_background.xml").readText()
            if ("#0B1F3A" !in background) {
                throw GradleException("$role launcher must use the approved navy.900 background.")
            }
        }
        fun digest(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val passengerForeground = roleRoots.getValue("passenger")
            .resolve("drawable/ic_launcher_foreground.xml").readBytes()
        val driverForeground = roleRoots.getValue("driver")
            .resolve("drawable/ic_launcher_foreground.xml").readBytes()
        if (digest(passengerForeground) == digest(driverForeground)) {
            throw GradleException("Passenger and driver launcher foregrounds must remain visibly distinct.")
        }
        val manifest = appDirectory.resolve("src/main/AndroidManifest.xml").readText()
        if ("@style/Theme.TaxiMobile.Starting" !in manifest) {
            throw GradleException("The Android manifest must use the navy TaxiMobile starting theme.")
        }
    }
}

val releaseApiBaseUrl = providers.gradleProperty("taximobileReleaseApiBaseUrl")
// The emulator can reach the development machine at 10.0.2.2. A physical
// Android device can instead use 127.0.0.1 with `adb reverse tcp:8000
// tcp:8000`, supplied through this property at build time. Keep this strictly
// debug-only: release endpoints must remain explicit TLS configuration.
val debugApiBaseUrl = providers.gradleProperty("taximobileDebugApiBaseUrl")
    .orElse("http://10.0.2.2:8000")
val debugMapStyleUrl = providers.gradleProperty("taximobileDebugMapStyleUrl")
    .orElse("https://tiles.openfreemap.org/styles/positron")
val releaseMapStyleUrl = providers.gradleProperty("taximobileReleaseMapStyleUrl")
val releaseVersionCode = providers.gradleProperty("taximobileVersionCode")
val releaseVersionName = providers.gradleProperty("taximobileVersionName")
val allowUnsignedReleaseVerificationProvider = providers.gradleProperty("taximobileAllowUnsignedReleaseForVerification")
    .map(String::toBooleanStrict)
    .orElse(false)
val allowMissingFirebaseVerificationProvider = providers.gradleProperty("taximobileAllowMissingFirebaseForVerification")
    .map(String::toBooleanStrict)
    .orElse(false)
val releaseCrashReportingEnabled = providers.gradleProperty("taximobileCrashReportingEnabled")
    .map(String::toBooleanStrict)
    .orElse(false)

fun Provider<String>.orInvalid(defaultValue: String) = orElse(defaultValue)
fun String.buildConfigString(): String = "\"${replace("\\", "\\\\").replace("\"", "\\\"")}\""

plugins {
    alias(libs.plugins.androidApplication)
    alias(libs.plugins.composeCompiler)
    alias(libs.plugins.googleServices) apply false
}

// Local builds remain possible before Firebase onboarding. Once the correct
// flavor-aware configuration is present, the official plugin processes it.
val projectFirebaseConfigurationPresent = fileTree(projectDir) {
    include("google-services.json", "src/**/google-services.json")
}.files.isNotEmpty()
if (projectFirebaseConfigurationPresent) {
    apply(plugin = "com.google.gms.google-services")
    apply(plugin = "com.google.firebase.crashlytics")
}

kotlin {
    compilerOptions {
        jvmTarget = JvmTarget.JVM_11
    }
}
dependencies {
    implementation(project(":shared"))

    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtimeCompose)
    // Activity Result lint evaluates the Fragment dependency directly. Declare
    // the already-resolved modern version explicitly so release lint can prove
    // the permission launcher is backed by Fragment 1.3.0 or newer.
    implementation(libs.androidx.fragment)
    implementation(libs.kotlinx.coroutinesAndroid)
    // The Android composition root owns the concrete Ktor OkHttp client. Keep
    // the engine dependency here instead of leaking Android transport details
    // into the shared module.
    implementation(libs.ktor.client.core)
    implementation(libs.ktor.client.okhttp)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.crashlytics)

    implementation(libs.compose.uiToolingPreview)
    debugImplementation(libs.compose.uiTooling)
}

android {
    namespace = "org.example.taximobile"
    compileSdk = libs.versions.android.compileSdk.get().toInt()

    defaultConfig {
        applicationId = "ma.taximobile"
        minSdk = libs.versions.android.minSdk.get().toInt()
        targetSdk = libs.versions.android.targetSdk.get().toInt()
        versionCode = releaseVersionCode.orElse("1").get().toInt()
        versionName = releaseVersionName.orElse("1.0.0").get()
        buildConfigField("String", "CLIENT_VERSION", "\"1.0.0\"")
    }
    flavorDimensions += "role"
    productFlavors {
        create("passenger") {
            dimension = "role"
            applicationIdSuffix = ".passenger"
            buildConfigField("String", "APP_ROLE", "\"PASSENGER\"")
            resValue("string", "app_name", "TaxiMobile Passenger")
        }
        create("driver") {
            dimension = "role"
            applicationIdSuffix = ".driver"
            buildConfigField("String", "APP_ROLE", "\"DRIVER\"")
            resValue("string", "app_name", "TaxiMobile Driver")
        }
    }
    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
    buildTypes {
        debug {
            resValue("bool", "firebase_crashlytics_collection_enabled", "false")
            buildConfigField("String", "API_BASE_URL", debugApiBaseUrl.get().buildConfigString())
            buildConfigField("String", "MAP_STYLE_URL", debugMapStyleUrl.get().buildConfigString())
        }
        release {
            resValue(
                "bool",
                "firebase_crashlytics_collection_enabled",
                (
                    releaseCrashReportingEnabled.get() &&
                        !allowMissingFirebaseVerificationProvider.get()
                ).toString(),
            )
            isMinifyEnabled = true
            isShrinkResources = true
            buildConfigField(
                "String",
                "CLIENT_VERSION",
                releaseVersionName.orInvalid("0.0.0").get().buildConfigString(),
            )
            buildConfigField(
                "String",
                "API_BASE_URL",
                releaseApiBaseUrl.orInvalid("https://api.taximobile.invalid").get().buildConfigString(),
            )
            buildConfigField(
                "String",
                "MAP_STYLE_URL",
                releaseMapStyleUrl.orInvalid("https://maps.taximobile.invalid/style.json").get().buildConfigString(),
            )
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
        resValues = true
    }
}

val verifyRoleLauncherAssets = tasks.register<ValidateRoleLauncherAssets>("verifyRoleLauncherAssets") {
    group = "verification"
    description = "Verifies role-specific TaxiMobile launcher and navy splash resources."
    androidAppDirectory.set(layout.projectDirectory)
}

tasks.named("preBuild") {
    dependsOn(verifyRoleLauncherAssets)
    dependsOn(rootProject.tasks.named("verifyAndroidShrinker"))
}

val signingPropertyNames = listOf(
    "taximobileSigningStoreFile",
    "taximobileSigningStorePassword",
    "taximobileSigningKeyAlias",
    "taximobileSigningKeyPassword",
)
val suppliedSigningProperties = signingPropertyNames.filter { providers.gradleProperty(it).isPresent }
if (suppliedSigningProperties.isNotEmpty() && suppliedSigningProperties.size != signingPropertyNames.size) {
    throw GradleException(
        "Android release signing is partially configured. Supply all four documented signing properties or none.",
    )
}
if (suppliedSigningProperties.size == signingPropertyNames.size) {
    android.signingConfigs.create("taximobileRelease") {
        storeFile = file(providers.gradleProperty("taximobileSigningStoreFile").get())
        storePassword = providers.gradleProperty("taximobileSigningStorePassword").get()
        keyAlias = providers.gradleProperty("taximobileSigningKeyAlias").get()
        keyPassword = providers.gradleProperty("taximobileSigningKeyPassword").get()
    }
    android.buildTypes.named("release") {
        signingConfig = android.signingConfigs.getByName("taximobileRelease")
    }
}

val validateReleaseConfiguration by tasks.registering(ValidateTaxiMobileReleaseConfiguration::class) {
    group = "verification"
    description = "Reject unsafe or incomplete TaxiMobile Android release configuration."
    apiBaseUrl.set(releaseApiBaseUrl.orElse(""))
    mapStyleUrl.set(releaseMapStyleUrl.orElse(""))
    versionCodeValue.set(releaseVersionCode.orElse("0"))
    versionNameValue.set(releaseVersionName.orElse(""))
    firebaseConfigurationPresent.set(projectFirebaseConfigurationPresent)
    signingConfigurationPresent.set(suppliedSigningProperties.size == signingPropertyNames.size)
    crashReportingEnabled.set(releaseCrashReportingEnabled)
    allowMissingFirebaseVerification.set(allowMissingFirebaseVerificationProvider)
    allowUnsignedReleaseVerification.set(allowUnsignedReleaseVerificationProvider)
}

tasks.matching {
    it.name in setOf("prePassengerReleaseBuild", "preDriverReleaseBuild")
}.configureEach {
    dependsOn(validateReleaseConfiguration)
}
