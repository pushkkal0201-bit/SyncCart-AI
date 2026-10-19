import { useEffect, useRef, useState } from "react";
import { Button, Card, StatusPill } from "@synccart/design-system";

type Props = {
  busy: boolean;
  onDetected: (barcode: string) => Promise<void>;
  onClose: () => void;
};

export function BarcodeScanner({ busy, onDetected, onClose }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [manual, setManual] = useState("");
  const [mode, setMode] = useState<"idle" | "live" | "unsupported">("idle");
  const [message, setMessage] = useState("Aim the camera at an EAN/UPC barcode.");

  useEffect(() => () => streamRef.current?.getTracks().forEach((track) => track.stop()), []);

  async function startLive() {
    if (!("BarcodeDetector" in window) || !navigator.mediaDevices?.getUserMedia) {
      setMode("unsupported");
      setMessage("Live barcode scanning is unavailable in this browser or insecure HTTP context. Use manual barcode entry below.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      const video = videoRef.current;
      if (!video) return;
      video.srcObject = stream;
      await video.play();
      setMode("live");
      setMessage("Scanner active. Hold the barcode steady inside the frame.");
      const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "upc_e", "code_128"] });
      let stopped = false;
      const scan = async () => {
        if (stopped || busy || !videoRef.current) return;
        try {
          const codes = await detector.detect(videoRef.current);
          const value = codes[0]?.rawValue?.trim();
          if (value) {
            stopped = true;
            navigator.vibrate?.(80);
            stream.getTracks().forEach((track) => track.stop());
            await onDetected(value);
            return;
          }
        } catch {
          // Detection errors are transient while frames initialize.
        }
        window.setTimeout(scan, 220);
      };
      scan();
    } catch {
      setMode("unsupported");
      setMessage("Camera permission was unavailable. On a phone over LAN HTTP, browsers may block live camera APIs. Manual entry still works for the demo.");
    }
  }

  async function submitManual(event: React.FormEvent) {
    event.preventDefault();
    const value = manual.trim();
    if (!value || busy) return;
    await onDetected(value);
  }

  return (
    <div className="scanner-screen">
      <header className="topbar">
        <button className="icon-button" onClick={onClose} aria-label="Close scanner">←</button>
        <div><p className="eyebrow">Scan & Go</p><h1>Scan product</h1></div>
        <StatusPill tone={mode === "live" ? "good" : "info"}>{mode === "live" ? "LIVE" : "READY"}</StatusPill>
      </header>

      <Card className="scanner-card">
        <div className="camera-stage">
          <video ref={videoRef} muted playsInline className={mode === "live" ? "camera-video" : "camera-video hidden"} />
          {mode !== "live" ? (
            <div className="camera-placeholder">
              <div className="scan-frame"><span /><span /><span /><span /></div>
              <p>Use your rear camera to scan EAN / UPC barcodes.</p>
            </div>
          ) : <div className="scan-overlay"><div className="scan-line" /></div>}
        </div>
        <p className="scanner-message">{message}</p>
        <Button onClick={startLive} disabled={busy || mode === "live"}>{mode === "live" ? "Scanner active" : "Start camera scanner"}</Button>
      </Card>

      <Card className="manual-card">
        <p className="eyebrow">Demo fallback</p>
        <h3>Enter barcode manually</h3>
        <form onSubmit={submitManual} className="manual-form">
          <input value={manual} onChange={(e) => setManual(e.target.value)} inputMode="numeric" placeholder="e.g. 8900000000036" aria-label="Barcode" />
          <Button disabled={busy || !manual.trim()}>{busy ? "Adding…" : "Add product"}</Button>
        </form>
        <p className="microcopy">This fallback keeps the live demo usable even when mobile browsers block camera access on local HTTP.</p>
      </Card>
    </div>
  );
}
