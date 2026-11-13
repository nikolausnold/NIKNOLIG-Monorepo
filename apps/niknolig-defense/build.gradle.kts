import java.net.InetAddress
import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

dependencies {
    implementation(project(":electro-engel-core"))
    implementation(project(":support-core"))
    implementation(project(":device-link-core"))
    implementation("com.google.zxing:core:3.5.4")
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20260814")
}

val backendBaseUrl = providers.gradleProperty("niknoligDefenseBackendUrl")
    .orElse(providers.environmentVariable("NIKNOLIG_DEFENSE_BACKEND_URL"))
    .orNull
    ?.trim()
    .orEmpty()
val debugBackendBaseUrl = providers.gradleProperty("niknoligDefenseDebugBackendUrl")
    .orNull
    ?.trim()
    .orEmpty()

fun validateBackendBaseUrl(value: String, allowLoopback: Boolean = false) {
    if (value.isEmpty()) return
    val uri = runCatching { URI(value) }.getOrNull()
        ?: error("NIKNOLIG Defense backend URL must be an absolute HTTPS origin.")
    val host = uri.host?.lowercase()?.trimEnd('.')
        ?: error("NIKNOLIG Defense backend URL must include a hostname.")
    require(uri.scheme.equals("https", ignoreCase = true) &&
        uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null &&
        uri.path in listOf("", "/") && (uri.port == -1 || uri.port in 1..65535)
    ) { "NIKNOLIG Defense backend URL must be an HTTPS origin without credentials, path, query, or fragment." }
    val validHost = if (allowLoopback) {
        host == "127.0.0.1"
    } else {
        host != "localhost" && !host.endsWith(".localhost") &&
            !isLoopbackOrUnspecifiedAddress(host)
    }
    require(validHost && host != "backend.invalid" && !host.endsWith(".invalid")) {
        "NIKNOLIG Defense backend URL must not use a placeholder or loopback host."
    }
}

fun isLoopbackOrUnspecifiedAddress(host: String): Boolean {
    if (!host.contains(':') && !host.matches(Regex("[0-9.]+"))) return false
    return runCatching {
        val address = InetAddress.getByName(host)
        address.isLoopbackAddress || address.isAnyLocalAddress
    }.getOrDefault(true)
}

validateBackendBaseUrl(backendBaseUrl)
validateBackendBaseUrl(debugBackendBaseUrl, allowLoopback = true)

// The device link stays closed until the written SecurityChain-P0 approval exists.
val deviceLinkP0Approved = (providers.gradleProperty("deviceLinkP0Approved")
    .orElse(providers.environmentVariable("NIKNOLIG_DEVICE_LINK_P0_APPROVED"))
    .orNull?.trim() == "true")

fun optionalSetting(property: String, environment: String): String =
    providers.gradleProperty(property).orElse(providers.environmentVariable(environment)).orNull?.trim().orEmpty()

val accountAuthUrl = optionalSetting("niknoligDefenseAccountAuthUrl", "NIKNOLIG_DEFENSE_ACCOUNT_AUTH_URL")
val accountAuthKey = optionalSetting("niknoligDefenseAccountAuthKey", "NIKNOLIG_DEFENSE_ACCOUNT_AUTH_KEY")
require(accountAuthUrl.isEmpty() || accountAuthUrl.startsWith("https://")) {
    "Account auth URL must be an HTTPS origin."
}
require(!accountAuthKey.contains('"') && !accountAuthKey.contains('\\')) { "Invalid account auth key." }

val updateVersionCode = providers.environmentVariable("NIKNOLIG_VERSION_CODE").orNull?.let {
    val code = requireNotNull(it.toIntOrNull()) { "Invalid NIKNOLIG_VERSION_CODE" }
    require(code in 2..2100000000) { "Invalid NIKNOLIG_VERSION_CODE" }
    code
}

val releaseStoreFile = System.getenv("NIKNOLIG_DEFENSE_RELEASE_STORE_FILE")
val releaseStorePassword = System.getenv("NIKNOLIG_DEFENSE_RELEASE_STORE_PASSWORD")
val releaseKeyAlias = System.getenv("NIKNOLIG_DEFENSE_RELEASE_KEY_ALIAS")
val releaseKeyPassword = System.getenv("NIKNOLIG_DEFENSE_RELEASE_KEY_PASSWORD")
val releaseSigningConfigured = listOf(
    releaseStoreFile,
    releaseStorePassword,
    releaseKeyAlias,
    releaseKeyPassword,
).all { !it.isNullOrBlank() }

android {
    namespace = "com.niknolig.defense"
    compileSdk = 37
    buildToolsVersion = "35.0.0"

    buildFeatures {
        buildConfig = true
    }

    signingConfigs {
        if (releaseSigningConfigured) {
            create("release") {
                storeFile = file(releaseStoreFile!!)
                storeType = "PKCS12"
                storePassword = releaseStorePassword!!
                keyAlias = releaseKeyAlias!!
                keyPassword = releaseKeyPassword!!
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.niknolig.defense"
        minSdk = 26
        targetSdk = 37
        versionCode = updateVersionCode ?: 1
        versionName = updateVersionCode?.let { "0.1.$it" } ?: "0.1.0"
        buildConfigField("String", "BACKEND_BASE_URL", "\"$backendBaseUrl\"")
        buildConfigField("boolean", "DEVICE_LINK_P0_APPROVED", deviceLinkP0Approved.toString())
        buildConfigField("String", "ACCOUNT_AUTH_URL", "\"$accountAuthUrl\"")
        buildConfigField("String", "ACCOUNT_AUTH_KEY", "\"$accountAuthKey\"")
    }

    buildTypes {
        getByName("debug") {
            if (debugBackendBaseUrl.isNotEmpty()) {
                buildConfigField("String", "BACKEND_BASE_URL", "\"$debugBackendBaseUrl\"")
            }
        }
        getByName("release") {
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}

val verifyReleaseBackendUrl = tasks.register("verifyReleaseBackendUrl") {
    doLast {
        require(backendBaseUrl.isNotEmpty()) {
            "Set NIKNOLIG_DEFENSE_BACKEND_URL or -PniknoligDefenseBackendUrl to the approved HTTPS backend origin before building a release."
        }
    }
}

tasks.configureEach {
    if (name in setOf("preReleaseBuild", "assembleRelease", "bundleRelease", "installRelease")) {
        dependsOn(verifyReleaseBackendUrl)
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}
