pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
    plugins {
        id("com.android.application") version "8.11.1"
        id("org.jetbrains.kotlin.android") version "2.2.21"
        id("org.jetbrains.kotlin.jvm") version "2.2.21"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "NIKNOLIG-Monorepo"
include(":niknolig", ":niknolig-defense")
project(":niknolig").projectDir = file("apps/niknolig")
project(":niknolig-defense").projectDir = file("apps/niknolig-defense")
include(":electro-engel-core")
project(":electro-engel-core").projectDir = file("modules/electro-engel/core")
include(":support-core")
project(":support-core").projectDir = file("modules/support/core")
