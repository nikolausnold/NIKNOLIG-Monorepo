// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SupportCore",
    products: [
        .library(name: "SupportCore", targets: ["SupportCore"]),
    ],
    targets: [
        .target(name: "SupportCore"),
        .testTarget(name: "SupportCoreTests", dependencies: ["SupportCore"]),
    ]
)
