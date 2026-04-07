import React, { useEffect, useRef } from 'react';

const CanvasOverlay = ({ predictions, width, height, color = '#4CAF50' }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !predictions) return;

    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw Bounding Boxes
    if (predictions.boxes) {
      predictions.boxes.forEach(box => {
        const [x1, y1, x2, y2] = box.box;
        const confidence = box.conf;
        
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

        // Label Background
        ctx.fillStyle = color;
        ctx.fillRect(x1, y1 - 20, 40, 20);
        
        // Label Text
        ctx.fillStyle = 'white';
        ctx.font = '12px Inter, sans-serif';
        ctx.fillText(`${(confidence * 100).toFixed(0)}%`, x1 + 5, y1 - 5);
      });
    }

    // Draw Segmentation Masks (Polygons)
    if (predictions.masks) {
       predictions.masks.forEach(mask => {
           if (mask.xyn) {
               ctx.beginPath();
               ctx.strokeStyle = color;
               ctx.fillStyle = `${color}33`; // 20% opacity
               ctx.lineWidth = 1.5;

               mask.xyn.forEach((point, index) => {
                   // Points are normalized [0-1]
                   const px = point[0] * canvas.width;
                   const py = point[1] * canvas.height;
                   if (index === 0) ctx.moveTo(px, py);
                   else ctx.lineTo(px, py);
               });
               
               ctx.closePath();
               ctx.stroke();
               ctx.fill();
           }
       });
    }
  }, [predictions, width, height, color]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 10
      }}
    />
  );
};

export default CanvasOverlay;
