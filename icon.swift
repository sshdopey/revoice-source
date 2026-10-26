import AppKit
let size=1024
let bitmap=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:size,pixelsHigh:size,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!
NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:bitmap)
NSColor(calibratedRed:0.09,green:0.11,blue:0.14,alpha:1).setFill()
NSBezierPath(roundedRect:NSRect(x:40,y:40,width:944,height:944),xRadius:210,yRadius:210).fill()
let path=NSBezierPath();path.lineWidth=55;path.lineCapStyle = .round;path.lineJoinStyle = .round
path.move(to:NSPoint(x:418,y:770));path.line(to:NSPoint(x:340,y:770));path.curve(to:NSPoint(x:255,y:682),controlPoint1:NSPoint(x:288,y:770),controlPoint2:NSPoint(x:255,y:735));path.line(to:NSPoint(x:255,y:340));path.curve(to:NSPoint(x:340,y:252),controlPoint1:NSPoint(x:255,y:285),controlPoint2:NSPoint(x:288,y:252));path.line(to:NSPoint(x:418,y:252))
path.move(to:NSPoint(x:600,y:770));path.curve(to:NSPoint(x:605,y:514),controlPoint1:NSPoint(x:812,y:752),controlPoint2:NSPoint(x:812,y:568));path.curve(to:NSPoint(x:600,y:252),controlPoint1:NSPoint(x:812,y:458),controlPoint2:NSPoint(x:812,y:267))
NSColor(calibratedRed:0.702,green:0.945,blue:0.42,alpha:1).setStroke();path.stroke()
NSGraphicsContext.restoreGraphicsState()
try bitmap.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:CommandLine.arguments[1]))
