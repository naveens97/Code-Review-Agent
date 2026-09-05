import { useEffect, useRef, useState } from "react";

function emojiForScore(score) {
  if (score >= 90) return "🤩";
  if (score >= 75) return "😊";
  if (score >= 60) return "🙂";
  if (score >= 40) return "😐";
  if (score >= 20) return "😟";
  return "💀";
}

function colorForScore(score) {
  if (score >= 90) return "#3dd68c";
  if (score >= 75) return "#5fa8ff";
  if (score >= 60) return "#e8a33d";
  if (score >= 40) return "#f09a47";
  if (score >= 20) return "#f0475d";
  return "#d63049";
}

export default function RatingGauge({ score, label }) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef(null);

  useEffect(() => {
    const start = performance.now();
    const duration = 1000;
    const to = score;

    function tick(now) {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setProgress(to * eased);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [score]);

  const displayScore = Math.round(progress);
  const emoji = emojiForScore(score);
  const color = colorForScore(score);

  return (
    <div
      className="gauge-wrap"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px 0 12px",
        gap: 4,
      }}
    >
      <div
        style={{
          fontSize: 72,
          lineHeight: 1,
          filter: `drop-shadow(0 0 18px ${color}60)`,
          animation: "emojiPop 0.5s ease-out",
        }}
      >
        {emoji}
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: 3, marginTop: 8 }}>
        <span
          style={{
            fontSize: 42,
            fontWeight: 800,
            color,
            lineHeight: 1,
            fontFamily: "'Inter', sans-serif",
            letterSpacing: "-1px",
            textShadow: `0 0 12px ${color}50`,
          }}
        >
          {displayScore}
        </span>
        <span
          style={{
            fontSize: 16,
            fontWeight: 500,
            color: "var(--ink-faint)",
          }}
        >
          /100
        </span>
      </div>

      <div
        style={{
          fontSize: 13,
          fontWeight: 700,
          color,
          textTransform: "uppercase",
          letterSpacing: "2px",
          marginTop: 2,
        }}
      >
        {label}
      </div>

      <style>{`
        @keyframes emojiPop {
          0% { transform: scale(0.3) rotate(-15deg); opacity: 0; }
          60% { transform: scale(1.15) rotate(5deg); opacity: 1; }
          100% { transform: scale(1) rotate(0deg); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

