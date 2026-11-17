/**
 * Tiny pixel sprites, drawn inline inside sentences.
 *
 * The whole page is calm and white; these are the only ornament, and they are what makes it
 * ours rather than another SaaS template. Each sprite is a grid of characters mapped to
 * colours — editing one is editing a picture, not a path.
 *
 * Keep them 12x12. Smaller loses the shape at body size, bigger stops reading as a pixel.
 */

type Palette = Record<string, string>;

interface Sprite {
  rows: string[];
  palette: Palette;
  label: string;
}

const CLAPPER: Sprite = {
  label: "clapperboard",
  rows: [
    "............",
    "..kkkkkkkk..",
    "..kwkwkwkw..",
    "..wkwkwkwk..",
    "..kkkkkkkk..",
    "..bbbbbbbb..",
    "..bbbbbbbb..",
    "..bbllllbb..",
    "..bbbbbbbb..",
    "..bbbbbbbb..",
    "..kkkkkkkk..",
    "............",
  ],
  palette: { k: "#131316", w: "#ffffff", b: "#1e3bea", l: "#c8ff2e" },
};

const CONTROLLER: Sprite = {
  label: "controller",
  rows: [
    "............",
    "............",
    "...pppppp...",
    "..pppppppp..",
    ".pppwppppppp",
    ".ppwwwpprrpp",
    ".pppwppppppp",
    ".ppppppprrpp",
    "..pppppppp..",
    "..pp....pp..",
    "............",
    "............",
  ],
  palette: { p: "#131316", w: "#ffffff", r: "#c8ff2e" },
};

const SPEAKER: Sprite = {
  label: "loud sound",
  rows: [
    "............",
    ".....oo.....",
    "....ooo..t..",
    "..oooooo.t..",
    "..ooooootot.",
    "..ooooootot.",
    "..ooooootot.",
    "..oooooo.t..",
    "....ooo..t..",
    ".....oo.....",
    "............",
    "............",
  ],
  palette: { o: "#ff7a1a", t: "#1e3bea" },
};

const PHONE: Sprite = {
  label: "vertical clip",
  // A play triangle on a white screen: at 12px the shape has to be the whole idea, so the
  // earlier version (an empty frame with a dot) read as a smudge.
  rows: [
    "............",
    "...kkkkkk...",
    "...kwwwwk...",
    "...kwlwwk...",
    "...kwllwk...",
    "...kwlllk...",
    "...kwllwk...",
    "...kwlwwk...",
    "...kwwwwk...",
    "...kkkkkk...",
    "............",
    "............",
  ],
  palette: { k: "#131316", w: "#ffffff", l: "#131316" },
};

const STAR: Sprite = {
  label: "pick",
  rows: [
    "............",
    ".....yy.....",
    ".....yy.....",
    "..y..yy..y..",
    "..yyyyyyyy..",
    "...yyyyyy...",
    "....yyyy....",
    "...yy..yy...",
    "..yy....yy..",
    "............",
    "............",
    "............",
  ],
  palette: { y: "#ffc400" },
};

export const SPRITES = {
  clapper: CLAPPER,
  controller: CONTROLLER,
  speaker: SPEAKER,
  phone: PHONE,
  star: STAR,
} as const;

export type SpriteName = keyof typeof SPRITES;

export function PixelSprite({
  name,
  className = "",
}: {
  name: SpriteName;
  className?: string;
}) {
  const sprite = SPRITES[name];
  const cells: Array<{ x: number; y: number; fill: string }> = [];
  sprite.rows.forEach((row, y) => {
    [...row].forEach((char, x) => {
      const fill = sprite.palette[char];
      if (fill) cells.push({ x, y, fill });
    });
  });
  return (
    <svg
      viewBox="0 0 12 12"
      shapeRendering="crispEdges"
      role="img"
      aria-label={sprite.label}
      className={`inline-block align-[-0.15em] ${className}`}
    >
      {cells.map(({ x, y, fill }) => (
        <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" fill={fill} />
      ))}
    </svg>
  );
}
