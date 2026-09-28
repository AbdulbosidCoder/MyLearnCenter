// "Дата" — the app's own character: a small data robot with a chart on its chest.
// `dim` draws a shadowed version for parts of the path that are not open yet.

export function Mascot({ size = 140, dim = false, wave = false }: { size?: number; dim?: boolean; wave?: boolean }) {
  const c = dim
    ? { body: "var(--mascot-dim)", belly: "var(--mascot-dim-2)", accent: "var(--mascot-dim-2)", eye: "var(--mascot-dim-2)" }
    : { body: "#2fb3a3", belly: "#e9fbf7", accent: "#ffb020", eye: "#1b2b34" };
  return (
    <svg width={size} height={size} viewBox="0 0 140 150" aria-hidden="true" className={`mascot${wave ? " wave" : ""}`}>
      <ellipse cx="70" cy="142" rx="38" ry="6" fill="#000" opacity="0.18" />
      {/* antenna */}
      <path d="M70 26V12" stroke={c.body} strokeWidth="5" strokeLinecap="round" />
      <circle cx="70" cy="10" r="7" fill={c.accent} />
      {/* feet */}
      <rect x="44" y="124" width="18" height="14" rx="7" fill={c.body} />
      <rect x="78" y="124" width="18" height="14" rx="7" fill={c.body} />
      {/* arms */}
      <path d="M26 82c-10 4-14 14-10 22" stroke={c.body} strokeWidth="10" strokeLinecap="round" fill="none" />
      <g className="mascot-arm">
        <path d="M114 80c10-6 16-18 12-30" stroke={c.body} strokeWidth="10" strokeLinecap="round" fill="none" />
      </g>
      {/* body */}
      <rect x="24" y="24" width="92" height="106" rx="40" fill={c.body} />
      {/* face screen */}
      <rect x="38" y="40" width="64" height="40" rx="18" fill={c.belly} />
      <circle cx="56" cy="60" r="7" fill={c.eye} />
      <circle cx="84" cy="60" r="7" fill={c.eye} />
      {!dim && <circle cx="58.5" cy="57.5" r="2.4" fill="#fff" />}
      {!dim && <circle cx="86.5" cy="57.5" r="2.4" fill="#fff" />}
      <path d="M62 71c5 4 11 4 16 0" stroke={c.eye} strokeWidth="3" strokeLinecap="round" fill="none" />
      {/* bar chart on the chest */}
      <rect x="50" y="90" width="40" height="28" rx="8" fill={c.belly} />
      <rect x="56" y="104" width="6" height="9" rx="2" fill={dim ? c.accent : "#3a8ef6"} />
      <rect x="67" y="98" width="6" height="15" rx="2" fill={c.accent} />
      <rect x="78" y="94" width="6" height="19" rx="2" fill={dim ? c.accent : "#e5484d"} />
    </svg>
  );
}
