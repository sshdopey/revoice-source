import Cocoa
let size = NSSize(width: 760, height: 560)
let image = NSImage(size: size); image.lockFocus()
let ground = NSColor(calibratedRed: 0.075, green: 0.09, blue: 0.11, alpha: 1)
let pearl = NSColor(calibratedRed: 0.95, green: 0.96, blue: 0.97, alpha: 1)
let secondary = NSColor(calibratedRed: 0.64, green: 0.69, blue: 0.74, alpha: 1)
let lime = NSColor(calibratedRed: 0.70, green: 0.94, blue: 0.42, alpha: 1)
ground.setFill(); NSRect(origin: .zero, size: size).fill()
func text(_ value: String, _ x: CGFloat, _ y: CGFloat, _ font: NSFont, _ color: NSColor) {
    (value as NSString).draw(at: NSPoint(x: x, y: y), withAttributes: [.font: font, .foregroundColor: color])
}
text("Revoice", 46, 470, .systemFont(ofSize: 34, weight: .bold), pearl)
text("Meet your next voice.", 385, 477, .systemFont(ofSize: 25, weight: .semibold), pearl)
text("Drag Revoice into Applications, then open Revoice.", 48, 420, .systemFont(ofSize: 16), secondary)
for index in 0..<39 {
    let t = Double(index) / 38
    let envelope = pow(sin(.pi * t), 0.7)
    let rhythm = abs(sin(t * 23 + 0.8)) * 0.7 + abs(sin(t * 47)) * 0.3
    let height = 2 + envelope * (5 + 15 * rhythm)
    let x = 258 + 244 * t
    let y = 260 + 76 * 4 * t * (1 - t)
    lime.withAlphaComponent(0.12 + envelope * 0.5).setFill()
    NSBezierPath(roundedRect: NSRect(x: x - 1.2, y: y - height / 2, width: 2.4, height: height), xRadius: 1.2, yRadius: 1.2).fill()
}
text("Apple Silicon · macOS 13+", 48, 26, .systemFont(ofSize: 12), secondary)
text("Microphone setup is included.", 491, 26, .systemFont(ofSize: 12), secondary)
image.unlockFocus()
let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!)!
try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
