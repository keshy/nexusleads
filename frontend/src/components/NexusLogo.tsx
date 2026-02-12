interface NexusLogoProps {
  size?: number
  className?: string
}

export default function NexusLogo({ size = 32, className = '' }: NexusLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer hexagon ring */}
      <path
        d="M32 4L56 18V46L32 60L8 46V18L32 4Z"
        stroke="url(#nexus-gradient)"
        strokeWidth="2"
        fill="none"
        opacity="0.6"
      />
      {/* Inner hexagon */}
      <path
        d="M32 12L48 22V42L32 52L16 42V22L32 12Z"
        fill="url(#nexus-gradient)"
        opacity="0.15"
      />
      {/* Neural network nodes */}
      <circle cx="32" cy="14" r="3" fill="url(#nexus-gradient)" />
      <circle cx="48" cy="23" r="3" fill="url(#nexus-gradient)" />
      <circle cx="48" cy="41" r="3" fill="url(#nexus-gradient)" />
      <circle cx="32" cy="50" r="3" fill="url(#nexus-gradient)" />
      <circle cx="16" cy="41" r="3" fill="url(#nexus-gradient)" />
      <circle cx="16" cy="23" r="3" fill="url(#nexus-gradient)" />
      {/* Center node - larger */}
      <circle cx="32" cy="32" r="5" fill="url(#nexus-gradient)" />
      {/* Connection lines from center to vertices */}
      <line x1="32" y1="32" x2="32" y2="14" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      <line x1="32" y1="32" x2="48" y2="23" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      <line x1="32" y1="32" x2="48" y2="41" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      <line x1="32" y1="32" x2="32" y2="50" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      <line x1="32" y1="32" x2="16" y2="41" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      <line x1="32" y1="32" x2="16" y2="23" stroke="url(#nexus-gradient)" strokeWidth="1" opacity="0.5" />
      {/* Pulse ring animation */}
      <circle cx="32" cy="32" r="8" stroke="url(#nexus-gradient)" strokeWidth="1" fill="none" opacity="0.3">
        <animate attributeName="r" values="8;18;8" dur="3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0.3;0;0.3" dur="3s" repeatCount="indefinite" />
      </circle>
      <defs>
        <linearGradient id="nexus-gradient" x1="8" y1="4" x2="56" y2="60" gradientUnits="userSpaceOnUse">
          <stop stopColor="#06b6d4" />
          <stop offset="0.5" stopColor="#8b5cf6" />
          <stop offset="1" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
    </svg>
  )
}
