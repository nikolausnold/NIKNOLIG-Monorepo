import XCTest
@testable import Niknolig

final class AppIdentityTests: XCTestCase {
    func testProductIdentity() {
        XCTAssertEqual(AppIdentity.name, "NIKNOLIG")
        XCTAssertEqual(AppIdentity.bundleIdentifier, "com.niknolig.app.ios")
    }

    func testHostHasOwnBundleIdentifier() {
        XCTAssertEqual(Bundle.main.bundleIdentifier, AppIdentity.bundleIdentifier)
        XCTAssertNotEqual(Bundle.main.bundleIdentifier, "com.niknolig.defense.ios")
    }
}
