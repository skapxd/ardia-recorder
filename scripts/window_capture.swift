// Records one Ardia window with ScreenCaptureKit: smooth, at native resolution, and unaffected
// by other windows on top of it. Needs screen recording permission.
//
//   window_capture calibrate
//       Looks for the magenta calibration marks drawn by overlay.js in every on-screen Ardia
//       window and prints {"window": id, "x", "y", "w", "h"} (pixels) for the first match.
//   window_capture record <out.mov> <window id>
//       Records that window until SIGINT or SIGTERM. Prints "FIRST <unix time>" when the
//       first frame is written.
import AppKit
import AVFoundation
import CoreGraphics
import Foundation
import ScreenCaptureKit

func fail(_ message: String, _ code: Int32 = 1) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(code)
}

func ardiaWindows() async throws -> [SCWindow] {
    let content = try await SCShareableContent.excludingDesktopWindows(true, onScreenWindowsOnly: true)
    return content.windows.filter {
        $0.owningApplication?.applicationName == "Ardia" && $0.windowLayer == 0 && $0.frame.width > 200
    }
}

func pixelSize(_ filter: SCContentFilter) -> (Int, Int) {
    let scale = CGFloat(filter.pointPixelScale)
    return (Int(filter.contentRect.width * scale), Int(filter.contentRect.height * scale))
}

/// Bounding box of the pure-magenta pixels in an image, or nil.
func magentaBox(_ image: CGImage) -> CGRect? {
    let w = image.width, h = image.height
    var data = [UInt8](repeating: 0, count: w * h * 4)
    guard let ctx = CGContext(data: &data, width: w, height: h, bitsPerComponent: 8, bytesPerRow: w * 4,
                              space: CGColorSpaceCreateDeviceRGB(),
                              bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return nil }
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: w, height: h))
    var minX = w, minY = h, maxX = -1, maxY = -1
    for y in 0..<h {
        let row = y * w * 4
        for x in 0..<w {
            let i = row + x * 4
            if data[i] > 235 && data[i + 1] < 25 && data[i + 2] > 235 {
                minX = min(minX, x); maxX = max(maxX, x); minY = min(minY, y); maxY = max(maxY, y)
            }
        }
    }
    guard maxX > minX, maxY > minY else { return nil }
    return CGRect(x: minX, y: minY, width: maxX - minX + 1, height: maxY - minY + 1)
}

func calibrate() async throws {
    for window in try await ardiaWindows() {
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        (config.width, config.height) = pixelSize(filter)
        config.showsCursor = false
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        if let box = magentaBox(image) {
            print(#"{"window": \#(window.windowID), "x": \#(Int(box.minX)), "y": \#(Int(box.minY)), "w": \#(Int(box.width)), "h": \#(Int(box.height))}"#)
            return
        }
    }
    fail("No Ardia window shows the calibration marks", 2)
}

final class Recorder: NSObject, SCStreamOutput {
    let writer: AVAssetWriter
    let input: AVAssetWriterInput
    var started = false

    init(url: URL, width: Int, height: Int) throws {
        try? FileManager.default.removeItem(at: url)
        writer = try AVAssetWriter(outputURL: url, fileType: .mov)
        input = AVAssetWriterInput(mediaType: .video, outputSettings: [
            AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
            AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: width * height * 8],
        ])
        input.expectsMediaDataInRealTime = true
        writer.add(input)
        writer.startWriting()
    }

    func stream(_ stream: SCStream, didOutputSampleBuffer buffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .screen, buffer.isValid,
              let info = CMSampleBufferGetSampleAttachmentsArray(buffer, createIfNecessary: false) as? [[SCStreamFrameInfo: Any]],
              let raw = info.first?[.status] as? Int, SCFrameStatus(rawValue: raw) == .complete else { return }
        if !started {
            writer.startSession(atSourceTime: buffer.presentationTimeStamp)
            started = true
            print("FIRST \(Date().timeIntervalSince1970)")
            fflush(stdout)
        }
        if input.isReadyForMoreMediaData { input.append(buffer) }
    }
}

func record(to path: String, windowID: CGWindowID) async throws {
    guard let window = try await ardiaWindows().first(where: { $0.windowID == windowID }) else {
        fail("Ardia window \(windowID) not found")
    }
    let filter = SCContentFilter(desktopIndependentWindow: window)
    let config = SCStreamConfiguration()
    (config.width, config.height) = pixelSize(filter)
    config.minimumFrameInterval = CMTime(value: 1, timescale: 30)
    config.showsCursor = false
    config.pixelFormat = kCVPixelFormatType_32BGRA
    let recorder = try Recorder(url: URL(fileURLWithPath: path), width: config.width, height: config.height)
    let stream = SCStream(filter: filter, configuration: config, delegate: nil)
    try stream.addStreamOutput(recorder, type: .screen, sampleHandlerQueue: DispatchQueue(label: "frames"))
    try await stream.startCapture()

    await withCheckedContinuation { (done: CheckedContinuation<Void, Never>) in
        var sources: [DispatchSourceSignal] = []
        for sig in [SIGINT, SIGTERM] {
            signal(sig, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: sig, queue: .main)
            source.setEventHandler { done.resume(); sources.forEach { $0.cancel() } }
            source.resume()
            sources.append(source)
        }
    }
    try await stream.stopCapture()
    recorder.input.markAsFinished()
    await recorder.writer.finishWriting()
    if recorder.writer.status != .completed { fail("Could not write \(path): \(String(describing: recorder.writer.error))") }
}

// ScreenCaptureKit needs a window server connection, which a plain command-line tool lacks.
NSApplication.shared.setActivationPolicy(.prohibited)

let args = CommandLine.arguments
Task {
    do {
        switch args.dropFirst().first {
        case "calibrate": try await calibrate()
        case "record" where args.count == 4:
            guard let id = CGWindowID(args[3]) else { fail("Bad window id") }
            try await record(to: args[2], windowID: id)
        default: fail("usage: window_capture calibrate | record <out.mov> <window id>")
        }
        exit(0)
    } catch {
        fail("\(error.localizedDescription)", 3)
    }
}
dispatchMain()
