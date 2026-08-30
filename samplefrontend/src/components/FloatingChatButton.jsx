import { useEffect, useRef, useState } from "react";

export default function FloatingChatButton({ onClick }) {
  const [position, setPosition] = useState({ x: 24, y: window.innerHeight / 2 });
  const dragging = useRef(false);
  const moved = useRef(false);

  useEffect(() => {
    function keepInsideWindow() {
      setPosition((current) => ({ x: Math.max(12, Math.min(window.innerWidth - 56, current.x)), y: Math.max(70, Math.min(window.innerHeight - 70, current.y)) }));
    }
    window.addEventListener("resize", keepInsideWindow);
    return () => window.removeEventListener("resize", keepInsideWindow);
  }, []);

  function startDrag(event) {
    event.currentTarget.setPointerCapture(event.pointerId);
    dragging.current = true;
    moved.current = false;
  }

  function moveDrag(event) {
    if (!dragging.current) return;
    moved.current = true;
    setPosition({ x: Math.max(12, Math.min(window.innerWidth - 56, window.innerWidth - event.clientX)), y: Math.max(70, Math.min(window.innerHeight - 70, event.clientY)) });
  }

  function endDrag() {
    dragging.current = false;
  }

  return <button type="button" className="floating-chat-button" style={{ right: position.x, top: position.y }} onPointerDown={startDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onClick={() => { if (!moved.current) onClick(); }} aria-label="Open data assistant" title="Open data assistant">💬</button>;
}
