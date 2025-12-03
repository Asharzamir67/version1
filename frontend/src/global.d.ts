// src/global.d.ts
interface Window {
  electron?: {
    onWindowFocus: (callback: () => void) => () => void;
  };
}