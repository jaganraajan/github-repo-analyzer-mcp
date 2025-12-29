"use client";

import { useState } from "react";
import { Camera, X } from "lucide-react";

interface Screenshot {
  data: string; // base64 encoded PNG
  url: string;
}

interface ScreenshotGalleryProps {
  screenshots: Screenshot[];
}

export default function ScreenshotGallery({ screenshots }: ScreenshotGalleryProps) {
  const [selectedScreenshot, setSelectedScreenshot] = useState<number | null>(null);

  if (screenshots.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-sm flex items-center gap-2">
        <Camera className="w-4 h-4" />
        Screenshots
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {screenshots.map((screenshot, idx) => (
          <div
            key={idx}
            className="border rounded-lg overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => setSelectedScreenshot(idx)}
          >
            <div className="bg-gray-50 p-2 border-b">
              <p className="text-xs font-medium truncate">{screenshot.url}</p>
            </div>
            <div className="bg-white p-4 flex items-center justify-center min-h-[200px]">
              <img
                src={`data:image/png;base64,${screenshot.data}`}
                alt={`Screenshot of ${screenshot.url}`}
                className="w-full h-auto rounded object-contain"
                style={{ imageRendering: 'auto', filter: 'none', maxWidth: '100%' }}
                loading="lazy"
              />
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {selectedScreenshot !== null && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedScreenshot(null)}
        >
          <div className="bg-white rounded-lg max-w-6xl max-h-[90vh] overflow-auto relative">
            <button
              onClick={() => setSelectedScreenshot(null)}
              className="absolute top-2 right-2 p-2 hover:bg-gray-100 rounded-full z-10"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="p-4">
              <h3 className="text-lg font-semibold mb-2 truncate">
                {screenshots[selectedScreenshot].url}
              </h3>
              <img
                src={`data:image/png;base64,${screenshots[selectedScreenshot].data}`}
                alt={`Screenshot of ${screenshots[selectedScreenshot].url}`}
                className="w-full h-auto rounded object-contain"
                style={{ imageRendering: 'auto', filter: 'none', maxWidth: '100%' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

