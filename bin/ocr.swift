// Text boxes in images with macOS Vision (built in, free, local).
// Usage: ocr <image> [<image> ...]  →  one JSON line per image:
//   {"file": "...", "boxes": [{"text": "...", "x": 0.1, "y": 0.2, "w": 0.5, "h": 0.06, "conf": 0.98}]}
// x, y are the top-left corner as fractions of the image (origin top-left); h approximates the text height.
import Foundation
import Vision
import AppKit

func boxes(_ path: String) -> [[String: Any]] {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return [] }
    var out: [[String: Any]] = []
    let req = VNRecognizeTextRequest { r, _ in
        for o in (r.results as? [VNRecognizedTextObservation]) ?? [] {
            guard let c = o.topCandidates(1).first else { continue }
            let b = o.boundingBox
            out.append(["text": c.string, "x": b.minX, "y": 1 - b.maxY, "w": b.width, "h": b.height, "conf": c.confidence])
        }
    }
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["zh-Hant", "en-US"]
    req.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    return out
}

for path in CommandLine.arguments.dropFirst() {
    let rec: [String: Any] = ["file": path, "boxes": boxes(path)]
    if let d = try? JSONSerialization.data(withJSONObject: rec), let s = String(data: d, encoding: .utf8) { print(s) }
}
