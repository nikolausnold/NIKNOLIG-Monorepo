import SwiftUI

enum AppIdentity {
    static let name = "NIKNOLIG Defense"
    static let bundleIdentifier = "com.niknolig.defense.ios"
}

@main
struct NiknoligDefenseApp: App {
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        Text("DEFENSE")
                            .font(.caption.bold())
                            .foregroundStyle(Color(red: 200 / 255, green: 241 / 255, blue: 105 / 255))
                        Text(AppIdentity.name)
                            .font(.largeTitle.bold())
                        GroupBox("Eigenständiger Sicherheitsbereich") {
                            Text("Lokales iOS-Grundgerüst. Keine Überwachung, Alarmierung oder Geräteverbindung implementiert.")
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        Text("Keine gemeinsamen Konten, App-Daten oder Laufzeitrechte mit NIKNOLIG. Produktfunktionen bleiben bis zur SecurityChain-P0-Freigabe gesperrt.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                }
                .background(Color(red: 12 / 255, green: 17 / 255, blue: 16 / 255))
            }
            .preferredColorScheme(.dark)
        }
    }
}
