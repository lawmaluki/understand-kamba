// Draws a shareable translation card as a PNG, entirely in the browser (canvas).
import type { Direction } from "./api";

export type CardFormat = "post" | "story";

export const CARD_SIZES: Record<CardFormat, { width: number; height: number; label: string }> = {
  post: { width: 1080, height: 1350, label: "Post 4:5" },
  story: { width: 1080, height: 1920, label: "Story 9:16" },
};

export const SITE_URL = "understand-kamba.vercel.app";

const C = {
  background: "#fefcef", // pale cream; matches the dialog's preview panel
  butter100: "#fdf5cc",
  butter300: "#f8e27a",
  wave: "#f2dd5c",
  ink: "#171717",
  text: "#262626",
  soft: "#525252",
  muted: "#737373",
  line: "#e5e5e5",
};

interface CardInput {
  source: string;
  translation: string;
  direction: Direction;
  format: CardFormat;
}

/** The page's Geist font stack (next/font gives it a generated family name). */
function fontFamily(): string {
  const geist = getComputedStyle(document.documentElement).getPropertyValue("--font-geist-sans").trim();
  return `${geist || "system-ui"}, system-ui, -apple-system, "Segoe UI", sans-serif`;
}

function roundedRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

/** Word-wraps text to maxWidth; very long words are split. */
function wrap(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = [];
  let line = "";
  for (const word of text.split(/\s+/).filter(Boolean)) {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width <= maxWidth) {
      line = candidate;
      continue;
    }
    if (line) lines.push(line);
    line = word;
    while (ctx.measureText(line).width > maxWidth && line.length > 1) {
      let cut = line.length - 1;
      while (cut > 1 && ctx.measureText(line.slice(0, cut)).width > maxWidth) cut--;
      lines.push(line.slice(0, cut));
      line = line.slice(cut);
    }
  }
  if (line) lines.push(line);
  return lines;
}

/** Largest font size (stepping down from max) whose wrapped text fits the box;
 * at the minimum size, extra lines are dropped and the last one ends in "…". */
function fitText(
  ctx: CanvasRenderingContext2D,
  text: string,
  font: (size: number) => string,
  maxWidth: number,
  maxHeight: number,
  maxSize: number,
  minSize: number,
  lineHeight: number
): { lines: string[]; size: number; height: number } {
  for (let size = maxSize; size >= minSize; size -= 2) {
    ctx.font = font(size);
    const lines = wrap(ctx, text, maxWidth);
    if (lines.length * size * lineHeight <= maxHeight) return { lines, size, height: lines.length * size * lineHeight };
  }
  ctx.font = font(minSize);
  const maxLines = Math.max(1, Math.floor(maxHeight / (minSize * lineHeight)));
  const lines = wrap(ctx, text, maxWidth).slice(0, maxLines);
  let last = lines[lines.length - 1] ?? "";
  while (last && ctx.measureText(`${last}…`).width > maxWidth) last = last.slice(0, -1);
  lines[lines.length - 1] = `${last.trimEnd()}…`;
  return { lines, size: minSize, height: lines.length * minSize * lineHeight };
}

function drawLines(ctx: CanvasRenderingContext2D, lines: string[], x: number, y: number, size: number, lineHeight: number) {
  // y is the top of the text block; place each baseline about 0.8em below its line's top.
  lines.forEach((l, i) => ctx.fillText(l, x, y + i * size * lineHeight + size * 0.92));
}

/** The app's waveform mark on a butter circle. */
function logo(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number) {
  ctx.save();
  ctx.fillStyle = C.butter300;
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = C.ink;
  const bars = [0.42, 0.72, 1.0, 0.72, 0.42];
  const bw = r * 0.13;
  const gap = r * 0.12;
  const total = bars.length * bw + (bars.length - 1) * gap;
  bars.forEach((h, i) => {
    const bh = r * h;
    roundedRect(ctx, cx - total / 2 + i * (bw + gap), cy - bh / 2, bw, bh, bw / 2);
    ctx.fill();
  });
  ctx.restore();
}

function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, family: string) {
  ctx.save();
  ctx.font = `600 25px ${family}`;
  ctx.fillStyle = C.muted;
  if ("letterSpacing" in ctx) (ctx as CanvasRenderingContext2D & { letterSpacing: string }).letterSpacing = "4px";
  ctx.fillText(text.toUpperCase(), x, y);
  ctx.restore();
}

export async function renderShareCard({ source, translation, direction, format }: CardInput): Promise<Blob> {
  const { width: W, height: H } = CARD_SIZES[format];
  const family = fontFamily();
  // Make sure the web font is ready before drawing (canvas won't wait for it).
  await Promise.all(["400", "500", "600", "700"].map((w) => document.fonts.load(`${w} 40px ${family}`, "Ũĩ")));

  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Your browser can't draw images.");
  ctx.textBaseline = "alphabetic";

  // Pale cream background.
  ctx.fillStyle = C.background;
  ctx.fillRect(0, 0, W, H);

  const story = format === "story";
  const [from, to] = direction === "en_to_kam" ? ["English", "Kikamba"] : ["Kikamba", "English"];

  // The white card, with a soft warm shadow.
  const footerH = story ? 300 : 220;
  const cardX = 96;
  const cardY = story ? 200 : 96;
  const cardW = W - cardX * 2;
  const cardH = H - cardY - footerH;
  ctx.save();
  ctx.shadowColor = "rgba(140,107,18,0.16)";
  ctx.shadowBlur = 70;
  ctx.shadowOffsetY = 20;
  ctx.fillStyle = "#ffffff";
  roundedRect(ctx, cardX, cardY, cardW, cardH, 52);
  ctx.fill();
  ctx.restore();

  const P = 64; // card padding
  const innerX = cardX + P;
  const innerW = cardW - P * 2;

  // Card header: logo + name, and the direction pill.
  const headerCY = cardY + P + 34;
  logo(ctx, innerX + 40, headerCY, 40);
  ctx.fillStyle = C.ink;
  ctx.font = `600 36px ${family}`;
  ctx.textBaseline = "middle";
  ctx.fillText("Understand Kamba", innerX + 106, headerCY + 1);
  ctx.font = `500 27px ${family}`;
  const pillText = `${from} → ${to}`;
  const pillW = ctx.measureText(pillText).width + 52;
  const pillH = 60;
  ctx.fillStyle = C.butter100;
  roundedRect(ctx, innerX + innerW - pillW, headerCY - pillH / 2, pillW, pillH, pillH / 2);
  ctx.fill();
  ctx.fillStyle = C.text;
  ctx.fillText(pillText, innerX + innerW - pillW + 26, headerCY + 1);
  ctx.textBaseline = "alphabetic";

  let y = headerCY + 34 + 64;

  // Source text.
  label(ctx, from, innerX, y + 22, family);
  y += 44;
  const sourceBox = fitText(ctx, source, (s) => `400 ${s}px ${family}`, innerW, cardH * 0.27, 42, 26, 1.32);
  ctx.fillStyle = C.soft;
  ctx.font = `400 ${sourceBox.size}px ${family}`;
  drawLines(ctx, sourceBox.lines, innerX, y, sourceBox.size, 1.32);
  y += sourceBox.height + 46;

  // Thin divider.
  ctx.fillStyle = C.line;
  ctx.fillRect(innerX, y, innerW, 2);
  y += 48;

  // Translation: the star of the card.
  label(ctx, to, innerX, y + 22, family);
  y += 44;
  const waveH = 60;
  const translationBox = fitText(
    ctx,
    translation,
    (s) => `700 ${s}px ${family}`,
    innerW,
    cardY + cardH - P - waveH - 40 - y,
    story ? 70 : 60,
    32,
    1.24
  );
  ctx.fillStyle = C.ink;
  ctx.font = `700 ${translationBox.size}px ${family}`;
  drawLines(ctx, translationBox.lines, innerX, y, translationBox.size, 1.24);

  // Waveform and caption along the bottom of the card.
  const waveCY = cardY + cardH - P - waveH / 2;
  const bars = 36;
  const barW = 7;
  const waveW = innerW * 0.58;
  const gap = (waveW - bars * barW) / (bars - 1);
  ctx.fillStyle = C.wave;
  for (let i = 0; i < bars; i++) {
    const h = 14 + Math.abs(Math.sin(i * 1.7) * Math.cos(i * 0.43)) * 46;
    roundedRect(ctx, innerX + i * (barW + gap), waveCY - h / 2, barW, h, barW / 2);
    ctx.fill();
  }
  ctx.fillStyle = C.muted;
  ctx.font = `400 26px ${family}`;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText(direction === "en_to_kam" ? "Hear it in Kikamba" : "Speak Kikamba, read English", innerX + innerW, waveCY);

  // Footer below the card.
  ctx.textAlign = "center";
  const footerY = cardY + cardH + footerH / 2;
  ctx.fillStyle = C.text;
  ctx.font = `500 32px ${family}`;
  ctx.fillText("Translate English ⇄ Kikamba", W / 2, footerY - 20);
  ctx.fillStyle = C.muted;
  ctx.font = `400 26px ${family}`;
  ctx.fillText(SITE_URL, W / 2, footerY + 24);
  ctx.textAlign = "left";
  ctx.textBaseline = "alphabetic";

  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("Couldn't create the image."))), "image/png")
  );
}
