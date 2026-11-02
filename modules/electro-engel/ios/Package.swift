// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ElectroEngelCore",
    platforms: [.iOS(.v16), .macOS(.v13)],
    products: [
        .library(name: "ElectroEngelCore", targets: ["ElectroEngelCore"]),
    ],
    targets: [
        .target(
            name: "ElectroEngelCore",
            path: ".",
            exclude: ["Tests"]
        ),
        .testTarget(
            name: "ElectroEngelCoreTests",
            dependencies: ["ElectroEngelCore"],
            path: "Tests"
        ),
    ]
)
