/// <reference types="vite/client" />

interface BarcodeDetectorOptions { formats?: string[] }
interface BarcodeResult { rawValue: string }
declare class BarcodeDetector {
  constructor(options?: BarcodeDetectorOptions);
  detect(source: ImageBitmapSource): Promise<BarcodeResult[]>;
  static getSupportedFormats(): Promise<string[]>;
}
