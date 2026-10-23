plugins {
    id("org.jetbrains.kotlin.jvm")
    id("application")
}

group = "org.elektroengel"
version = "0.1.0"

kotlin {
    jvmToolchain(17)
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    useJUnit()
}

application {
    mainClass.set("org.elektroengel.core.LocalAnalysisServerKt")
}
