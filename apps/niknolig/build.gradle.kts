plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val releaseSigningValues = listOf(
    "NIKNOLIG_RELEASE_STORE_FILE" to providers.environmentVariable("NIKNOLIG_RELEASE_STORE_FILE").orNull,
    "NIKNOLIG_RELEASE_STORE_PASSWORD" to providers.environmentVariable("NIKNOLIG_RELEASE_STORE_PASSWORD").orNull,
    "NIKNOLIG_RELEASE_KEY_ALIAS" to providers.environmentVariable("NIKNOLIG_RELEASE_KEY_ALIAS").orNull,
    "NIKNOLIG_RELEASE_KEY_PASSWORD" to providers.environmentVariable("NIKNOLIG_RELEASE_KEY_PASSWORD").orNull,
)
val hasReleaseSigningValues = releaseSigningValues.any { it.second != null }
require(!hasReleaseSigningValues || releaseSigningValues.all { !it.second.isNullOrBlank() }) {
    "All NIKNOLIG release signing environment variables must be set together."
}

android {
    namespace = "com.niknolig.app"
    compileSdk = 35
    buildToolsVersion = "35.0.0"

    if (hasReleaseSigningValues) {
        signingConfigs {
            create("release") {
                storeFile = file(requireNotNull(releaseSigningValues[0].second))
                storePassword = requireNotNull(releaseSigningValues[1].second)
                keyAlias = requireNotNull(releaseSigningValues[2].second)
                keyPassword = requireNotNull(releaseSigningValues[3].second)
            }
        }
    }

    buildTypes {
        getByName("release") {
            if (hasReleaseSigningValues) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    defaultConfig {
        applicationId = "com.niknolig.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

kotlin {
    compilerOptions {
        jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17
    }
}
