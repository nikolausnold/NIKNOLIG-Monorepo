import XCTest
@testable import NiknoligDefense

final class AppIdentityTests: XCTestCase {
    func testProductIdentity() {
        XCTAssertEqual(AppIdentity.name, "NIKNOLIG Defense")
        XCTAssertEqual(AppIdentity.bundleIdentifier, "com.niknolig.defense.ios")
    }

    func testHostHasOwnBundleIdentifier() {
        XCTAssertEqual(Bundle.main.bundleIdentifier, AppIdentity.bundleIdentifier)
        XCTAssertNotEqual(Bundle.main.bundleIdentifier, "com.niknolig.app.ios")
    }
}
