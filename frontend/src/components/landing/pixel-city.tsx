/**
 * The hero's backdrop: a pixel-art sunset skyline, drawn as crisp rectangles.
 *
 * Deliberately low resolution (160x90 units, blown up) so every edge lands on a pixel — the
 * look is a game, not a stock photo, and it costs one inline SVG instead of a megabyte of
 * video. Nothing here is from anybody's game: it is squares.
 */

/** Skyline blocks: [x, width, height]. Hand-placed so the silhouette has a rhythm. */
const TOWERS: Array<[number, number, number]> = [
  [0, 11, 16],
  [11, 7, 24],
  [18, 13, 11],
  [31, 8, 29],
  [39, 10, 19],
  [49, 6, 34],
  [55, 12, 14],
  [67, 9, 26],
  [76, 14, 9],
  [90, 7, 31],
  [97, 11, 17],
  [108, 9, 23],
  [117, 13, 12],
  [130, 8, 28],
  [138, 12, 18],
  [150, 10, 25],
];

const HORIZON = 62;

/** Lit windows, so the city reads as alive rather than as a bar chart. */
function windows(): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  for (const [x, w, h] of TOWERS) {
    for (let wx = x + 2; wx < x + w - 1; wx += 3) {
      for (let wy = HORIZON - h + 3; wy < HORIZON - 2; wy += 4) {
        // Deterministic "randomness": no hydration mismatch, same picture every render.
        if ((wx * 7 + wy * 13) % 5 < 2) out.push([wx, wy]);
      }
    }
  }
  return out;
}

export function PixelCity({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 160 90"
      preserveAspectRatio="xMidYMax slice"
      shapeRendering="crispEdges"
      aria-hidden
      className={className}
    >
      {/* Sky, in bands rather than a smooth gradient: pixel art has no dithering budget. */}
      <rect x="0" y="0" width="160" height="22" fill="#190a3a" />
      <rect x="0" y="22" width="160" height="10" fill="#3b1060" />
      <rect x="0" y="32" width="160" height="8" fill="#7a1570" />
      <rect x="0" y="40" width="160" height="7" fill="#c21f6a" />
      <rect x="0" y="47" width="160" height="8" fill="#f24d3d" />
      <rect x="0" y="55" width="160" height="7" fill="#ff8a2b" />

      {/* Sun: a disc with slits cut through it, the one shape that says "that sunset". */}
      <circle cx="80" cy="50" r="22" fill="#ffd166" />
      <circle cx="80" cy="50" r="22" fill="#ff5f6d" opacity="0.45" />
      {[36, 41, 45, 49, 53, 57].map((y, i) => (
        <rect key={y} x="56" y={y} width="48" height={1 + (i % 3)} fill="#190a3a" opacity="0.5" />
      ))}

      {/* Skyline. */}
      {TOWERS.map(([x, w, h]) => (
        <rect key={`${x}-${w}`} x={x} y={HORIZON - h} width={w} height={h} fill="#15082e" />
      ))}
      {windows().map(([x, y]) => (
        <rect key={`${x}-${y}`} x={x} y={y} width="1" height="2" fill="#c8ff2e" opacity="0.75" />
      ))}

      {/* Ground, and the grid running away towards the city. */}
      <rect x="0" y={HORIZON} width="160" height={90 - HORIZON} fill="#0a0618" />
      {[64, 67, 71, 76, 82, 89].map((y) => (
        <rect key={y} x="0" y={y} width="160" height="1" fill="#ff2d8d" opacity="0.45" />
      ))}
      {Array.from({ length: 17 }, (_, i) => i).map((i) => {
        // Verticals fan out from the vanishing point, so the ground reads as receding.
        const spread = (i - 8) * 1.6;
        return (
          <polygon
            key={i}
            points={`${80 + spread},${HORIZON} ${80 + spread * 9},90 ${80 + spread * 9 + 1},90 ${80 + spread + 0.4},${HORIZON}`}
            fill="#ff2d8d"
            opacity="0.3"
          />
        );
      })}
    </svg>
  );
}
