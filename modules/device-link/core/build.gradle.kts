plugins {
    id("org.jetbrains.kotlin.jvm")
}

group = "org.niknolig"
version = "0.1.0"

kotlin {
    jvmToolchain(17)
}

dependencies {
    testImplementation("org.bouncycastle:bcprov-jdk18on:1.86")
    testImplementation("junit:junit:4.13.2")
}

tasks.test {
    useJUnit()
}
