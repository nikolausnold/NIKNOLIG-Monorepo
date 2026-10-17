import SwiftUI

enum AppIdentity {
    static let name = "NIKNOLIG"
    static let bundleIdentifier = "com.niknolig.app.ios"
}

@main
struct NiknoligApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        Text(AppIdentity.name)
                            .font(.largeTitle.bold())
                        Text("Dein persönlicher Systembegleiter")
                            .font(.title2)
                        GroupBox("Elektro-Engel") {
                            Text("Lokale iOS-Vorschau. Noch keine Assistenz-, Geräte- oder Backend-Anbindung.")
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        Text("Gerätezugriff, Anmeldung und Datenübertragung bleiben bis zur SecurityChain-P0-Freigabe gesperrt.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                }
                .background(Color(red: 12 / 255, green: 17 / 255, blue: 16 / 255))
            }
            .tint(Color(red: 200 / 255, green: 241 / 255, blue: 105 / 255))
            .preferredColorScheme(.dark)
        }
    }
}
