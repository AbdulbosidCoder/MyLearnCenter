// Small flat icons drawn inline, so they take the colour of the text around them.
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 24, children, ...rest }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" {...rest}>
      {children}
    </svg>
  );
}

export const HomeIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 11.2 12 4l9 7.2V20a1 1 0 0 1-1 1h-5.5v-6h-5v6H4a1 1 0 0 1-1-1z" fill="#ff9a3c" />
    <path d="M1.8 11.6 12 3.4l10.2 8.2" stroke="#e5484d" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    <rect x="9.5" y="15" width="5" height="6" rx="1" fill="#8a4b1d" />
  </Svg>
);

export const TrophyIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M7 3h10v5a5 5 0 0 1-10 0z" fill="#ffc53d" />
    <path d="M7 5H4a3 3 0 0 0 3 4M17 5h3a3 3 0 0 1-3 4" stroke="#e8a317" strokeWidth="2" />
    <path d="M10 13h4l1 5H9z" fill="#e8a317" />
    <rect x="7" y="18" width="10" height="3" rx="1" fill="#b7791f" />
  </Svg>
);

export const TargetIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="9" fill="#e5484d" />
    <circle cx="12" cy="12" r="6" fill="#fff" />
    <circle cx="12" cy="12" r="3" fill="#e5484d" />
  </Svg>
);

export const UserIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="12" r="10" fill="#8e7cf0" />
    <circle cx="12" cy="10" r="3.5" fill="#fff" />
    <path d="M5.5 18.5a7 7 0 0 1 13 0" fill="#fff" />
  </Svg>
);

export const RobotIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="7" width="16" height="12" rx="4" fill="#2fb3a3" />
    <circle cx="9" cy="13" r="2" fill="#fff" />
    <circle cx="15" cy="13" r="2" fill="#fff" />
    <path d="M12 7V4" stroke="#2fb3a3" strokeWidth="2" strokeLinecap="round" />
    <circle cx="12" cy="3.5" r="1.5" fill="#ffc53d" />
  </Svg>
);

export const UsersIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="9" cy="9" r="3.5" fill="#3a8ef6" />
    <path d="M2.5 19a6.5 6.5 0 0 1 13 0z" fill="#3a8ef6" />
    <circle cx="17" cy="10" r="2.8" fill="#7cb8ff" />
    <path d="M14 19a5 5 0 0 1 8 0z" fill="#7cb8ff" />
  </Svg>
);

export const FlameIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M12 2c1 4 6 6 6 12a6 6 0 0 1-12 0c0-3 2-5 3-6 0 2 1 3 2 3 0-3-1-6 1-9z" fill="#ff8a1f" />
    <path d="M12 12c1 2 3 3 3 5a3 3 0 0 1-6 0c0-1.5 1-2.5 3-5z" fill="#ffd23f" />
  </Svg>
);

export const BoltIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M13.5 2 4.5 13.5H11L9.5 22l10-12.5H13z" fill="#ffc800" />
  </Svg>
);

export const ClockIcon = (p: IconProps) => (
  <Svg {...p}>
    <circle cx="12" cy="13" r="8.5" fill="#3a8ef6" />
    <circle cx="12" cy="13" r="6.2" fill="#fff" />
    <path d="M12 9.5V13l2.5 1.8" stroke="#3a8ef6" strokeWidth="2" strokeLinecap="round" />
    <rect x="10" y="2" width="4" height="2.5" rx="1" fill="#3a8ef6" />
  </Svg>
);

export const StarIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="m12 2.8 2.8 5.8 6.3.9-4.6 4.4 1.1 6.3L12 17.2l-5.6 3 1.1-6.3L2.9 9.5l6.3-.9z" fill="currentColor" />
  </Svg>
);

export const BookIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 5.5C5.5 4 8.5 4 11 5.5V20c-2.5-1.5-5.5-1.5-8 0zM21 5.5C18.5 4 15.5 4 13 5.5V20c2.5-1.5 5.5-1.5 8 0z" fill="currentColor" />
  </Svg>
);

export const PencilIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M4 20l1-4.5L15.5 5a2.1 2.1 0 0 1 3 3L8 18.5z" fill="currentColor" />
    <path d="M4 20l4.5-1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const CheckIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);

export const LockIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="5" y="10.5" width="14" height="10" rx="2.5" fill="currentColor" />
    <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" stroke="currentColor" strokeWidth="2.4" />
  </Svg>
);

export const ChestIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="3" y="9" width="18" height="11" rx="2" fill="currentColor" />
    <path d="M3 9a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v2H3z" fill="currentColor" opacity="0.75" />
    <rect x="10" y="10" width="4" height="5" rx="1" fill="var(--surface)" />
  </Svg>
);

export const ListIcon = (p: IconProps) => (
  <Svg {...p}>
    <rect x="4" y="3" width="16" height="18" rx="3" stroke="currentColor" strokeWidth="2" />
    <path d="M8 8h8M8 12h8M8 16h5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </Svg>
);

export const FolderIcon = (p: IconProps) => (
  <Svg {...p}>
    <path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" fill="#f0b400" />
    <path d="M3 9h18v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" fill="#ffc53d" />
    <path d="M12 11v6M9.5 13.5 12 11l2.5 2.5" stroke="#8a5a00" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </Svg>
);
