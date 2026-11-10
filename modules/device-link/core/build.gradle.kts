plugins {
    id("org.jetbrains.kotlin.jvm")
}

group = "org.niknolig"
version = "0.1.0"

kotlin {
    jvmToolchain(17)
}

dependencies {
    // Lightweight Ed25519 for Android versions without Keystore Ed25519 (API < 33).
    implementation("org.bouncycastle:bcprov-jdk18on:1.80")
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    useJUnit()
}
