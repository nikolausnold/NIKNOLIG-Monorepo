import java.net.InetAddress
import java.net.URI

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

dependencies {
    implementation(project(":support-core"))
    testImplementation("junit:junit:4.13.2")
}

val backendBaseUrl = providers.gradleProperty("niknoligDefenseBackendUrl")
    .orElse(providers.environmentVariable("NIKNOLIG_DEFENSE_BACKEND_URL"))
    .orElse("https://api.niknolig.com")
    .orNull
    ?.trim()
    .orEmpty()

fun validateBackendBaseUrl(value: String) {
    if (value.isEmpty()) return
    val uri = runCatching { URI(value) }.getOrNull()
        ?: error("NIKNOLIG Defense backend URL must be an absolute HTTPS origin.")
    val host = uri.host?.lowercase()?.trimEnd('.')
        ?: error("NIKNOLIG Defense backend URL must include a hostname.")
    require(uri.scheme.equals("https", ignoreCase = true) &&
        uri.rawUserInfo == null && uri.rawQuery == null && uri.rawFragment == null &&
        uri.path in listOf("", "/") && (uri.port == -1 || uri.port in 1..65535)
    ) { "NIKNOLIG Defense backend URL must be an HTTPS origin without credentials, path, query, or fragment." }
    require(host != "localhost" && !host.endsWith(".localhost") &&
        host != "backend.invalid" && !host.endsWith(".invalid") &&
        !isLoopbackOrUnspecifiedAddress(host)
    ) { "NIKNOLIG Defense backend URL must not use a placeholder or loopback host." }
}

fun isLoopbackOrUnspecifiedAddress(host: String): Boolean {
    if (!host.contains(':') && !host.matches(Regex("[0-9.]+"))) return false
    return runCatching {
        val address = InetAddress.getByName(host)
        address.isLoopbackAddress || address.isAnyLocalAddress
    }.getOrDefault(true)
}

validateBackendBaseUrl(backendBaseUrl)

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
    compileSdk = 35
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
        targetSdk = 35
        versionCode = updateVersionCode ?: 1
        versionName = updateVersionCode?.let { "0.1.$it" } ?: "0.1.0"
        buildConfigField("String", "BACKEND_BASE_URL", "\"$backendBaseUrl\"")
    }

    buildTypes {
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
