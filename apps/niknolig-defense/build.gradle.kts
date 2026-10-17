plugins {
    id("com.android.application")
}

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
    }

    buildTypes {
        getByName("release") {
            if (releaseSigningConfigured) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}

compilerOptions {
    jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
}
