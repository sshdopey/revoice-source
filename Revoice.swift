import Cocoa
import WebKit
import AVFoundation
import CoreAudio
import UniformTypeIdentifiers

final class StudioBackground: NSView {
    override func draw(_ dirtyRect: NSRect) {
        NSColor(srgbRed: 23/255, green: 27/255, blue: 33/255, alpha: 1).setFill(); bounds.fill()
        let sidebar: CGFloat = bounds.width <= 950 ? 195 : 225
        NSColor(srgbRed: 20/255, green: 24/255, blue: 30/255, alpha: 1).setFill()
        NSRect(x: 0, y: 0, width: sidebar, height: bounds.height).fill()
        NSColor(srgbRed: 48/255, green: 55/255, blue: 64/255, alpha: 1).setFill()
        NSRect(x: sidebar-1, y: 0, width: 1, height: bounds.height).fill()
    }
}
final class RevoiceDelegate: NSObject, NSApplicationDelegate, WKScriptMessageHandler, WKNavigationDelegate, WKUIDelegate, NSMenuItemValidation, NSWindowDelegate, NSMenuDelegate {
    var window: NSWindow!
    var web: WKWebView!
    var engine: Process?
    var output = Data()
    var token = UUID().uuidString + UUID().uuidString
    var port: Int?
    var terminating = false
    var audioActivity: NSObjectProtocol?
    var deviceRefreshWork: DispatchWorkItem?
    var hardwareListener: AudioObjectPropertyListenerBlock?
    var audioLive = false
    var microphoneMuted = false
    var voiceEnabled = true
    var monitoringEnabled = false
    var installingMicrophone = false
    var statusItem: NSStatusItem?
    var statusTimer: Timer?
    var statusRequestPending = false
    var library: [[String: Any]] = []
    var selectedVoice = ""
    var enginePhase = "Opening"
    var menuBarVisible: Bool { !UserDefaults.standard.bool(forKey: "hideMenuBarIcon") }

    func menuItem(_ menu: NSMenu, _ title: String, _ action: Selector, _ key: String = "", _ modifiers: NSEvent.ModifierFlags = [.command]) {
        let item = NSMenuItem(title: title, action: action, keyEquivalent: key)
        item.target = self; item.keyEquivalentModifierMask = modifiers; menu.addItem(item)
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let menu = NSMenu()
        let appItem = NSMenuItem(); menu.addItem(appItem)
        let appMenu = NSMenu(title: "Revoice"); appItem.submenu = appMenu
        menuItem(appMenu, "About Revoice", #selector(about))
        menuItem(appMenu, "Settings…", #selector(openSettings), ",")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide Revoice", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = appMenu.addItem(withTitle: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h"); hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        menuItem(appMenu, "Run in Background", #selector(hideToBackground), "q")
        menuItem(appMenu, "Show menu-bar icon", #selector(toggleMenuBarIcon))
        menuItem(appMenu, "Quit Revoice", #selector(quitRevoice), "q", [.command, .option])
        let audioItem = NSMenuItem(); menu.addItem(audioItem); let audio = NSMenu(title: "Audio"); audioItem.submenu = audio
        addVoiceMenu(to: audio)
        audio.addItem(.separator())
        menuItem(audio, "Voice conversion", #selector(toggleConversion), "v", [.command, .option])
        menuItem(audio, "Hear myself", #selector(toggleMonitoring))
        menuItem(audio, "Mute microphone", #selector(toggleMute), "m", [.command, .shift])
        let windowItem = NSMenuItem(); menu.addItem(windowItem); let windowMenu = NSMenu(title: "Window"); windowItem.submenu = windowMenu
        menuItem(windowMenu, "Show Revoice", #selector(showWindow))
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        menuItem(windowMenu, "Close to Background", #selector(hideToBackground), "w")
        NSWindow.allowsAutomaticWindowTabbing = false
        for (title, action, key, modifiers) in [
            ("Undo", "undo:", "z", NSEvent.ModifierFlags.command),
            ("Redo", "redo:", "z", [.command, .shift]),
            ("Cut", "cut:", "x", .command),
            ("Copy", "copy:", "c", .command),
            ("Paste", "paste:", "v", .command),
            ("Select All", "selectAll:", "a", .command)
        ] {
            let shortcut = NSMenuItem(title: title, action: Selector(action), keyEquivalent: key)
            shortcut.keyEquivalentModifierMask = modifiers
            shortcut.isHidden = true; shortcut.allowsKeyEquivalentWhenHidden = true
            appMenu.addItem(shortcut)
        }
        NSApp.mainMenu = menu
        let config = WKWebViewConfiguration(); config.websiteDataStore = .nonPersistent(); config.userContentController.add(self, name: "revoice")
        web = WKWebView(frame: .zero, configuration: config); web.navigationDelegate = self; web.uiDelegate = self
        config.userContentController.addUserScript(WKUserScript(source: "document.addEventListener('contextmenu', event => event.preventDefault(), true);", injectionTime: .atDocumentStart, forMainFrameOnly: true))
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1060, height: 790), styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView], backing: .buffered, defer: false)
        window.title = "Revoice"; window.titleVisibility = .hidden; window.titlebarAppearsTransparent = true
        window.tabbingMode = .disallowed; window.delegate = self; window.isReleasedWhenClosed = false
        window.appearance = NSAppearance(named: .darkAqua)
        window.backgroundColor = NSColor(srgbRed: 23/255, green: 27/255, blue: 33/255, alpha: 1)
        window.minSize = NSSize(width: 820, height: 650)
        let surface = StudioBackground(); window.contentView = surface
        web.translatesAutoresizingMaskIntoConstraints = false; surface.addSubview(web)
        NSLayoutConstraint.activate([web.leadingAnchor.constraint(equalTo: surface.leadingAnchor), web.trailingAnchor.constraint(equalTo: surface.trailingAnchor), web.bottomAnchor.constraint(equalTo: surface.bottomAnchor), web.topAnchor.constraint(equalTo: (window.contentLayoutGuide as! NSLayoutGuide).topAnchor)])
        window.center(); window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true)
        configureStatusItem()
        statusTimer = Timer(timeInterval: 2, repeats: true) { [weak self] _ in self?.refreshNativeState() }
        RunLoop.main.add(statusTimer!, forMode: .common)
        web.loadHTMLString("<style>body{font:17px -apple-system;background:#1c2128;color:#f4f5f7;padding:64px}h1{font-size:40px}</style><h1>Revoice</h1><p>Opening your voice library…</p>", baseURL: nil)
        startEngine()
        observeAudioDevices()
        if !microphoneDriverPresent() {
            DispatchQueue.main.async { self.offerMicrophoneSetup() }
        }
    }
    func microphoneDriverPresent() -> Bool {
        FileManager.default.fileExists(atPath: "/Library/Audio/Plug-Ins/HAL/RevoiceMicrophone.driver/Contents/MacOS/RevoiceMicrophone")
    }
    func offerMicrophoneSetup() {
        guard !installingMicrophone else { return }
        if microphoneDriverPresent() { return }
        let alert = NSAlert()
        alert.messageText = "Finish setting up Revoice"
        alert.informativeText = "Revoice Microphone lets your calling apps hear your selected voice. It is included in Revoice. macOS will ask for administrator approval to install it once; audio may briefly pause during setup."
        alert.addButton(withTitle: "Finish setup")
        alert.addButton(withTitle: "Not now")
        alert.beginSheetModal(for: window) { response in
            if response == .alertFirstButtonReturn { self.installMicrophone() }
        }
    }
    func installMicrophone() {
        guard !installingMicrophone,
              let package = Bundle.main.resourceURL?.appendingPathComponent("Revoice Microphone.pkg"),
              FileManager.default.fileExists(atPath: package.path) else { return }
        installingMicrophone = true
        let progress = NSAlert()
        progress.messageText = "Setting up Revoice Microphone…"
        progress.informativeText = "Approve the macOS request to finish setup."
        progress.addButton(withTitle: "Setting up…").isEnabled = false
        progress.beginSheetModal(for: window)
        let quotedPath = "'" + package.path.replacingOccurrences(of: "'", with: "'\\''") + "'"
        let command = "/usr/sbin/installer -pkg " + quotedPath + " -target /"
        let literal = command.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
        DispatchQueue.global(qos: .userInitiated).async {
            let process = Process()
            process.executableURL = URL(fileURLWithPath: "/usr/bin/osascript")
            process.arguments = ["-e", "do shell script \"" + literal + "\" with administrator privileges"]
            let errors = Pipe(); process.standardError = errors; process.standardOutput = FileHandle.nullDevice
            var succeeded = false
            var cancelled = false
            do {
                try process.run()
                let details = errors.fileHandleForReading.readDataToEndOfFile()
                process.waitUntilExit()
                succeeded = process.terminationStatus == 0
                cancelled = String(data: details, encoding: .utf8)?.contains("(-128)") == true
            } catch { }
            DispatchQueue.main.async {
                self.installingMicrophone = false
                self.window.endSheet(progress.window)
                if succeeded && self.microphoneDriverPresent() {
                    self.refreshAudioDevices()
                } else {
                    let failure = NSAlert()
                    failure.messageText = cancelled ? "Setup cancelled" : "Microphone setup needs attention"
                    failure.informativeText = cancelled ? "No administrator approval was given. You can finish setup from Revoice Settings whenever you are ready." : "Revoice could not finish microphone setup. Check administrator access and free disk space, then retry from Settings."
                    failure.addButton(withTitle: "OK")
                    failure.beginSheetModal(for: self.window)
                }
            }
        }
    }
    func refreshAudioDevices() {
        guard let port = port else { return }
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/control")!)
        request.httpMethod = "POST"
        request.setValue(token, forHTTPHeaderField: "X-Revoice-Token")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = Data("{\"action\":\"refresh\"}".utf8)
        URLSession.shared.dataTask(with: request).resume()
    }
    func observeAudioDevices() {
        var address = AudioObjectPropertyAddress(mSelector: kAudioHardwarePropertyDevices, mScope: kAudioObjectPropertyScopeGlobal, mElement: kAudioObjectPropertyElementMain)
        let listener: AudioObjectPropertyListenerBlock = { [weak self] _, _ in
            guard let self = self, !self.terminating else {return}
            self.deviceRefreshWork?.cancel()
            let work = DispatchWorkItem { [weak self] in
                guard let self = self, let port = self.port, !self.terminating else {return}
                var request = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/control")!)
                request.httpMethod = "POST"; request.setValue(self.token, forHTTPHeaderField: "X-Revoice-Token")
                request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                request.httpBody = Data("{\"action\":\"refresh\"}".utf8)
                URLSession.shared.dataTask(with: request).resume()
            }
            self.deviceRefreshWork = work
            DispatchQueue.main.asyncAfter(deadline: .now()+0.35, execute: work)
        }
        hardwareListener = listener
        AudioObjectAddPropertyListenerBlock(AudioObjectID(kAudioObjectSystemObject), &address, DispatchQueue.main, listener)
    }
    func startEngine() {
        guard let resources = Bundle.main.resourceURL else { return }
        let process = Process(); process.qualityOfService = .userInteractive; let pipe = Pipe(); let errors = Pipe()
        process.executableURL = resources.appendingPathComponent("runtime/bin/python3.12")
        process.arguments = ["-B", "-u", resources.appendingPathComponent("backend/app.py").path]
        var env = ProcessInfo.processInfo.environment
        env["PYTHONHOME"] = resources.appendingPathComponent("runtime").path
        env["PYTHONPATH"] = resources.appendingPathComponent("runtime/lib/python3.12/site-packages").path
        env["REVOICE_ENGINE"] = resources.appendingPathComponent("engine").path; env["REVOICE_TOKEN"] = token
        env["OMP_NUM_THREADS"] = "1"; process.environment = env
        env["PYTHONDONTWRITEBYTECODE"] = "1"; process.environment = env
        process.standardOutput = pipe; process.standardError = errors; engine = process
        pipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let bytes = h.availableData; guard !bytes.isEmpty else { h.readabilityHandler = nil; return }
            DispatchQueue.main.async { self?.received(bytes) }
        }
        let logDir = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Revoice")
        try? FileManager.default.createDirectory(at: logDir, withIntermediateDirectories: true)
        let logURL = logDir.appendingPathComponent("launcher.log")
        FileManager.default.createFile(atPath: logURL.path, contents: nil)
        let log = try? FileHandle(forWritingTo: logURL)
        errors.fileHandleForReading.readabilityHandler = { h in let bytes = h.availableData; if bytes.isEmpty {h.readabilityHandler = nil} else {try? log?.write(contentsOf: bytes)} }
        process.terminationHandler = { [weak self] p in DispatchQueue.main.async { guard let self = self, !self.terminating else {return}; self.showError("The voice engine stopped (code \(p.terminationStatus)). Quit and reopen Revoice. Details are saved in launcher.log.") } }
        do { try process.run() } catch { showError(error.localizedDescription) }
    }
    func received(_ bytes: Data) {
        output.append(bytes)
        while let range = output.range(of: Data([10])) {
            let line = output.subdata(in: 0..<range.lowerBound); output.removeSubrange(0...range.lowerBound)
            if let object = try? JSONSerialization.jsonObject(with: line) as? [String: Any] {
                if let p = object["port"] as? Int, port == nil {
                    port = p
                    let origin = "http://127.0.0.1:\(p)"
                    let authentication = "if (location.origin === '\(origin)') window.__revoiceToken = '\(token)';"
                    web.configuration.userContentController.addUserScript(WKUserScript(source: authentication, injectionTime: .atDocumentStart, forMainFrameOnly: true))
                    web.load(URLRequest(url: URL(string: origin + "/")!))
                }
                if let live = object["audio_live"] as? Bool {
                    if live && audioActivity == nil {audioActivity = ProcessInfo.processInfo.beginActivity(options: [.userInitiated, .latencyCritical], reason: "Converting live microphone audio")}
                    if !live, let activity = audioActivity {ProcessInfo.processInfo.endActivity(activity); audioActivity = nil}
                }
            }
        }
    }
    func showError(_ text: String) {
        let safe = text.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;")
        web.loadHTMLString("<style>body{font:17px -apple-system;padding:64px;background:#1c2128;color:#f4f5f7}</style><h1>Revoice needs attention</h1><p>\(safe)</p>", baseURL: nil)
    }
    func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters, initiatedByFrame frame: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        guard frame.isMainFrame, frame.request.url?.host == "127.0.0.1" else { completionHandler(nil); return }
        let panel = NSOpenPanel()
        panel.title = "Choose a voice ZIP"
        panel.prompt = "Choose ZIP"
        panel.allowedContentTypes = [.zip]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.beginSheetModal(for: window) { response in
            completionHandler(response == .OK ? panel.urls : nil)
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        publishDesktopState(); refreshNativeState()
    }
    func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
        guard message.frameInfo.isMainFrame, message.frameInfo.securityOrigin.host == "127.0.0.1", message.frameInfo.securityOrigin.port == port, let command = message.body as? String else {return}
        if command == "show-menu-bar" || command == "hide-menu-bar" {
            setMenuBarVisible(command == "show-menu-bar")
        } else if command == "quit-app" {
            quitRevoice()
        } else if command == "engine-guide" {
            NSWorkspace.shared.open(URL(string: "https://prj-beatrice.com/")!)
        } else if command.hasPrefix("state:"), let data = String(command.dropFirst(6)).data(using: .utf8), let state = try? JSONSerialization.jsonObject(with: data) as? [String: Bool] {
            audioLive = state["live"] ?? false; microphoneMuted = state["muted"] ?? false; voiceEnabled = state["enabled"] ?? false; monitoringEnabled = state["hear"] ?? false
        } else if command == "install" {
            if microphoneDriverPresent() { refreshAudioDevices() } else { offerMicrophoneSetup() }
        } else if command == "microphone" {
            func report(_ granted: Bool) {DispatchQueue.main.async {self.web.evaluateJavaScript("window.dispatchEvent(new CustomEvent('revoice-microphone',{detail:\(granted ? "true" : "false")}))")}}
            switch AVCaptureDevice.authorizationStatus(for: .audio) {
            case .authorized: report(true)
            case .notDetermined: AVCaptureDevice.requestAccess(for: .audio) {report($0)}
            default: report(false)
            }
        } else if command == "logs" {
            NSWorkspace.shared.open(FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/Revoice"))
        } else if command.hasPrefix("save-recording:"), let p = port {
            let identity = String(command.dropFirst("save-recording:".count))
            guard UUID(uuidString: identity) != nil else {return}
            var request = URLRequest(url: URL(string: "http://127.0.0.1:\(p)/recording?id=\(identity)")!)
            request.setValue(token, forHTTPHeaderField: "X-Revoice-Token")
            URLSession.shared.dataTask(with: request) { data, response, error in
                func report(_ object: [String: Any]) {
                    guard let bytes = try? JSONSerialization.data(withJSONObject: object), let json = String(data: bytes, encoding: .utf8) else {return}
                    DispatchQueue.main.async {self.web.evaluateJavaScript("window.dispatchEvent(new CustomEvent('revoice-recording-download',{detail:" + json + "}))")}
                }
                guard let data = data, (response as? HTTPURLResponse)?.statusCode == 200 else {report(["ok":false,"error":error?.localizedDescription ?? "The temporary recording is no longer available."]);return}
                do {
                    let downloads = try FileManager.default.url(for: .downloadsDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
                    let formatter = DateFormatter(); formatter.dateFormat = "yyyy-MM-dd_HH-mm-ss"
                    let name = "Revoice-" + formatter.string(from: Date()) + "-" + String(identity.prefix(8)) + ".wav"
                    try data.write(to: downloads.appendingPathComponent(name), options: .withoutOverwriting)
                    report(["ok":true,"id":identity,"name":name])
                } catch {report(["ok":false,"error":error.localizedDescription])}
            }.resume()
        } else if command == "licenses" {
            if let url = Bundle.main.resourceURL?.appendingPathComponent("Licenses") {NSWorkspace.shared.open(url)}
        }
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        if let url = action.request.url, url.scheme == "http", url.host == "127.0.0.1", url.port == port {decisionHandler(.allow)} else if action.request.url?.scheme == "about" {decisionHandler(.allow)} else {decisionHandler(.cancel)}
    }
    func addVoiceMenu(to menu: NSMenu) {
        let item = NSMenuItem(title: "Voice", action: nil, keyEquivalent: "")
        let submenu = NSMenu(title: "Voices"); submenu.delegate = self
        item.submenu = submenu; menu.addItem(item)
    }
    func configureStatusItem() {
        if let old = statusItem { NSStatusBar.system.removeStatusItem(old); statusItem = nil }
        guard menuBarVisible else { return }
        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
        let image = NSImage(size: NSSize(width: 20, height: 20), flipped: false) { _ in
            NSColor.black.setStroke()
            let path = NSBezierPath(); path.lineWidth = 1.8; path.lineCapStyle = .round; path.lineJoinStyle = .round
            path.move(to: NSPoint(x: 8, y: 17)); path.line(to: NSPoint(x: 5, y: 17))
            path.curve(to: NSPoint(x: 3, y: 15), controlPoint1: NSPoint(x: 3, y: 17), controlPoint2: NSPoint(x: 3, y: 17))
            path.line(to: NSPoint(x: 3, y: 5)); path.curve(to: NSPoint(x: 5, y: 3), controlPoint1: NSPoint(x: 3, y: 3), controlPoint2: NSPoint(x: 3, y: 3)); path.line(to: NSPoint(x: 8, y: 3))
            path.move(to: NSPoint(x: 13, y: 17)); path.curve(to: NSPoint(x: 13, y: 10), controlPoint1: NSPoint(x: 20, y: 16), controlPoint2: NSPoint(x: 20, y: 12))
            path.curve(to: NSPoint(x: 13, y: 3), controlPoint1: NSPoint(x: 20, y: 8), controlPoint2: NSPoint(x: 20, y: 4)); path.stroke(); return true
        }
        image.isTemplate = true; item.button?.image = image
        item.button?.setAccessibilityLabel("Revoice controls")
        let menu = NSMenu(title: "Revoice controls"); menu.delegate = self
        let header = NSMenuItem(title: "Revoice", action: nil, keyEquivalent: "")
        header.attributedTitle = NSAttributedString(string: "Revoice", attributes: [.font: NSFont.systemFont(ofSize: 14, weight: .semibold)])
        menu.addItem(header)
        let state = NSMenuItem(title: "Opening…", action: nil, keyEquivalent: ""); state.tag = 41; menu.addItem(state)
        menu.addItem(.separator()); addVoiceMenu(to: menu)
        menuItem(menu, "Voice conversion", #selector(toggleConversion))
        menuItem(menu, "Mute microphone", #selector(toggleMute))
        menuItem(menu, "Hear myself", #selector(toggleMonitoring))
        menu.addItem(.separator())
        menuItem(menu, "Open Revoice", #selector(showWindow))
        menuItem(menu, "Hide menu-bar icon", #selector(toggleMenuBarIcon))
        menu.addItem(.separator()); menuItem(menu, "Quit Revoice", #selector(quitRevoice))
        item.menu = menu; statusItem = item; updateStatusLabel()
    }
    func updateStatusLabel() {
        let name = library.first { $0["id"] as? String == selectedVoice }?["name"] as? String ?? "Choose a voice"
        let label = !audioLive ? enginePhase : (microphoneMuted ? "Microphone muted" : (voiceEnabled ? name : "Natural voice"))
        statusItem?.menu?.item(withTag: 41)?.title = label
        statusItem?.button?.toolTip = "Revoice · " + label
    }
    func menuNeedsUpdate(_ menu: NSMenu) {
        if menu.title == "Voices" {
            menu.removeAllItems()
            for voice in library {
                guard let name = voice["name"] as? String, let id = voice["id"] as? String else { continue }
                let item = NSMenuItem(title: name, action: #selector(selectVoice(_:)), keyEquivalent: "")
                item.target = self; item.representedObject = id; item.state = id == selectedVoice ? .on : .off
                menu.addItem(item)
            }
            if menu.items.isEmpty { let empty = NSMenuItem(title: "Add a voice in Revoice", action: #selector(showWindow), keyEquivalent: ""); empty.target = self; menu.addItem(empty) }
        }
        updateStatusLabel(); refreshNativeState()
    }
    func refreshNativeState() {
        guard let port = port, !terminating, !statusRequestPending else { return }
        statusRequestPending = true
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/status")!, timeoutInterval: 3)
        request.setValue(token, forHTTPHeaderField: "X-Revoice-Token")
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            let state = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
            DispatchQueue.main.async {
                guard let self = self else { return }; self.statusRequestPending = false
                guard let state = state, (response as? HTTPURLResponse)?.statusCode == 200 else { self.audioLive = false; self.enginePhase = "Engine unavailable"; self.updateStatusLabel(); return }
                self.enginePhase = state["phase"] as? String ?? "Ready"
                self.audioLive = self.enginePhase == "Live"
                self.microphoneMuted = state["muted"] as? Bool ?? false
                self.voiceEnabled = state["enabled"] as? Bool ?? true
                self.monitoringEnabled = state["hear"] as? Bool ?? false
                self.library = state["voices"] as? [[String: Any]] ?? []
                self.selectedVoice = state["voice"] as? String ?? ""
                self.updateStatusLabel()
            }
        }.resume()
    }
    func sendControl(_ payload: [String: Any]) {
        guard let port = port, !terminating else { return }
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(port)/control")!, timeoutInterval: 10)
        request.httpMethod = "POST"; request.setValue(token, forHTTPHeaderField: "X-Revoice-Token")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                guard let self = self else { return }
                if (response as? HTTPURLResponse)?.statusCode != 200 {
                    self.showWindow(); let alert = NSAlert(); alert.messageText = "Couldn’t change the audio setting"
                    let result = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
                    alert.informativeText = result?["error"] as? String ?? error?.localizedDescription ?? "Try again from Revoice."
                    alert.beginSheetModal(for: self.window)
                }
                self.refreshNativeState()
            }
        }.resume()
    }
    @objc func selectVoice(_ item: NSMenuItem) {
        if let id = item.representedObject as? String { sendControl(["voice": id]) }
    }
    @objc func toggleMenuBarIcon() { setMenuBarVisible(!menuBarVisible) }
    func setMenuBarVisible(_ visible: Bool) {
        UserDefaults.standard.set(!visible, forKey: "hideMenuBarIcon")
        configureStatusItem(); publishDesktopState()
    }
    func publishDesktopState() {
        web.evaluateJavaScript("window.dispatchEvent(new CustomEvent('revoice-desktop',{detail:{menuBarVisible:\(menuBarVisible ? "true" : "false")}}))")
    }

    func menuCommand(_ command: String) {
        showWindow()
        web.evaluateJavaScript("window.dispatchEvent(new CustomEvent('revoice-menu',{detail:'\(command)'}))")
    }
    @objc func openSettings() {menuCommand("settings")}
    @objc func toggleConversion() {sendControl(["enabled": !voiceEnabled])}
    @objc func toggleMonitoring() {sendControl(["hear": !monitoringEnabled])}
    @objc func toggleMute() {sendControl(["muted": !microphoneMuted])}
    @objc func showWindow() {
        NSApp.setActivationPolicy(.regular)
        if window.isMiniaturized { window.deminiaturize(nil) }
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); refreshNativeState()
    }
    func validateMenuItem(_ item: NSMenuItem) -> Bool {
        if item.action == #selector(toggleConversion) {item.state = voiceEnabled ? .on : .off; return port != nil}
        if item.action == #selector(toggleMonitoring) {item.state = monitoringEnabled ? .on : .off; return audioLive}
        if item.action == #selector(toggleMute) {item.state = microphoneMuted ? .on : .off; return audioLive}
        if item.action == #selector(toggleMenuBarIcon) {item.state = menuBarVisible ? .on : .off}
        if item.action == #selector(selectVoice(_:)) {item.state = item.representedObject as? String == selectedVoice ? .on : .off; return port != nil}

        return true
    }
    @objc func about() { let alert = NSAlert(); alert.messageText = "Revoice 0.2.4"; alert.informativeText = "Local voice conversion for Apple Silicon Macs. Includes Beatrice 2.0.0-rc.3, local noise reduction and Revoice Microphone. Audio stays on your Mac."; alert.runModal() }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {false}
    func windowShouldClose(_ sender: NSWindow) -> Bool { hideToBackground(); return false }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { showWindow(); return false }
    @objc func hideToBackground() {
        guard window.attachedSheet == nil else { NSSound.beep(); return }
        window.orderOut(nil); NSApp.setActivationPolicy(.accessory)
    }
    @objc func quitRevoice() { NSApp.terminate(nil) }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if installingMicrophone { return .terminateCancel }
        terminating = true
        statusTimer?.invalidate()
        if let item = statusItem { NSStatusBar.system.removeStatusItem(item) }

        guard let process = engine, process.isRunning else {return .terminateNow}
        process.terminate()
        DispatchQueue.global().async { process.waitUntilExit(); DispatchQueue.main.async {NSApp.reply(toApplicationShouldTerminate: true)} }
        DispatchQueue.main.asyncAfter(deadline: .now()+12) { if process.isRunning {kill(process.processIdentifier, SIGKILL)} }
        return .terminateLater
    }
}
let app = NSApplication.shared
let delegate = RevoiceDelegate(); app.delegate = delegate; app.setActivationPolicy(.regular); app.run()
