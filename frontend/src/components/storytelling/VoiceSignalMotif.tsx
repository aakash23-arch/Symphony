import React from 'react';
import { cn } from '../../lib/cn';

export interface VoiceSignalMotifProps {
  className?: string;
  variant?: 'hero' | 'transition' | 'closing' | 'minimal';
  state?: 'listening' | 'analysing' | 'complete';
}

/**
 * Symphony Central Symbolic Voice Motif.
 *
 * An original geometric artwork unifying:
 *  1. Ear / Acoustic listening contour (Human voice listening aperture)
 *  2. Headphone silhouette & sound transducer receivers
 *  3. Traversing multi-harmonic voice waveform
 *  4. Precision radar / signal detection calibration ring
 *
 * States:
 *  - 'listening': Hero ambient pulse & acoustic reception
 *  - 'analysing': Mid-page multi-phase spectral analysis
 *  - 'complete': Closing converged assurance & verification lock
 */
export const VoiceSignalMotif: React.FC<VoiceSignalMotifProps> = ({
  className,
  variant = 'hero',
  state = 'listening',
}) => {
  const isHero = variant === 'hero';
  const isClosing = variant === 'closing';
  const isTransition = variant === 'transition';

  return (
    <div
      className={cn(
        'relative flex items-center justify-center select-none transition-transform duration-500 hover:scale-[1.03]',
        isHero && 'w-full max-w-[340px] sm:max-w-[440px] aspect-square',
        isClosing && 'w-full max-w-[280px] sm:max-w-[380px] aspect-square',
        isTransition && 'w-full max-w-[240px] sm:max-w-[320px] aspect-square',
        variant === 'minimal' && 'w-32 h-32',
        className,
      )}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 400 400"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full overflow-visible"
      >
        <defs>
          <pattern id="symphony-grid-dot-motif" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="0.75" fill="#E4E4E7" />
          </pattern>

          {/* Subtly moving wave clip */}
          <linearGradient id="symphony-grad-beam" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#09090B" stopOpacity="0.2" />
            <stop offset="50%" stopColor="#09090B" stopOpacity="1" />
            <stop offset="100%" stopColor="#09090B" stopOpacity="0.2" />
          </linearGradient>
        </defs>

        {/* 1. Background Grid Aperture */}
        <circle cx="200" cy="200" r="184" fill="url(#symphony-grid-dot-motif)" opacity="0.7" />
        <circle cx="200" cy="200" r="184" stroke="#E4E4E7" strokeWidth="1" strokeDasharray="4 6" />

        {/* 2. Concentric Precision Detection & Scanning Rings */}
        <circle cx="200" cy="200" r="156" stroke="#D4D4D8" strokeWidth="1" />
        <circle
          cx="200"
          cy="200"
          r="132"
          stroke="#E4E4E7"
          strokeWidth="1"
          strokeDasharray="3 6"
          className="animate-spin"
          style={{ animationDuration: state === 'analysing' ? '30s' : '60s' }}
        />
        <circle
          cx="200"
          cy="200"
          r="105"
          stroke={state === 'complete' ? '#059669' : '#09090B'}
          strokeWidth={state === 'complete' ? '1.5' : '1'}
          strokeDasharray={state === 'complete' ? undefined : '1 5'}
        />

        {/* 3. Cardinal Calibration Ticks */}
        <line x1="200" y1="8" x2="200" y2="24" stroke="#09090B" strokeWidth="2" />
        <line x1="200" y1="376" x2="200" y2="392" stroke="#09090B" strokeWidth="2" />
        <line x1="8" y1="200" x2="24" y2="200" stroke="#09090B" strokeWidth="2" />
        <line x1="376" y1="200" x2="392" y2="200" stroke="#09090B" strokeWidth="2" />

        {/* Diagonal Crosshairs */}
        <line x1="56" y1="56" x2="68" y2="68" stroke="#71717A" strokeWidth="1.5" />
        <line x1="344" y1="56" x2="332" y2="68" stroke="#71717A" strokeWidth="1.5" />
        <line x1="56" y1="344" x2="68" y2="332" stroke="#71717A" strokeWidth="1.5" />
        <line x1="344" y1="344" x2="332" y2="332" stroke="#71717A" strokeWidth="1.5" />

        {/* 4. Headphone Acoustic Band Silhouette */}
        <path
          d="M 100 215 C 100 130, 140 85, 200 85 C 260 85, 300 130, 300 215"
          stroke="#09090B"
          strokeWidth="3.5"
          strokeLinecap="round"
        />

        {/* 5. Acoustic Transducer Receivers */}
        <rect x="88" y="198" width="24" height="64" rx="12" fill="#FFFFFF" stroke="#09090B" strokeWidth="2.5" />
        <line x1="100" y1="210" x2="100" y2="250" stroke="#71717A" strokeWidth="1.5" strokeDasharray="2 3" />

        <rect x="288" y="198" width="24" height="64" rx="12" fill="#FFFFFF" stroke="#09090B" strokeWidth="2.5" />
        <line x1="300" y1="210" x2="300" y2="250" stroke="#71717A" strokeWidth="1.5" strokeDasharray="2 3" />

        {/* 6. Central Abstract Ear Silhouette */}
        <path
          d="M 185 140 
             C 232 140, 252 165, 248 198 
             C 243 226, 222 234, 218 248 
             C 212 262, 206 276, 185 276 
             C 168 276, 156 264, 156 248 
             C 156 226, 178 216, 184 200 
             C 188 186, 178 172, 162 172"
          stroke="#09090B"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />

        {/* Inner Tragus & Concha Contour */}
        <path
          d="M 174 204 C 190 204, 196 220, 186 230 C 176 238, 170 228, 172 216"
          stroke="#71717A"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
        />

        {/* 7. Traversing Voice Waveform (State-dependent dynamics) */}
        {state === 'listening' && (
          <>
            {/* Listening State: Continuous Harmonic Wave */}
            <path
              d="M 40 200 
                 L 80 200 
                 Q 95 185, 110 200 
                 T 135 200 
                 Q 150 165, 165 235 
                 Q 180 135, 195 265 
                 Q 210 155, 225 245 
                 Q 240 180, 255 220 
                 T 280 200 
                 L 360 200"
              stroke="#09090B"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M 60 200 
                 Q 100 215, 130 200 
                 Q 155 225, 175 175 
                 Q 195 235, 215 175 
                 Q 235 215, 260 200 
                 L 340 200"
              stroke="#A1A1AA"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeDasharray="3 3"
            />
          </>
        )}

        {state === 'analysing' && (
          <>
            {/* Analysing State: High-Frequency Discontinuities & Analysis Beams */}
            <path
              d="M 30 200 
                 L 70 200 
                 Q 85 160, 100 240 
                 Q 115 150, 130 250 
                 Q 145 130, 160 270 
                 Q 175 110, 190 290 
                 Q 205 120, 220 280 
                 Q 235 140, 250 260 
                 Q 265 170, 280 230 
                 L 370 200"
              stroke="#09090B"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Spectral frequency ticks */}
            {[-40, -20, 0, 20, 40].map((offset) => (
              <line
                key={offset}
                x1={200 + offset}
                y1={170}
                x2={200 + offset}
                y2={230}
                stroke="#DC2626"
                strokeWidth="1"
                strokeDasharray="2 4"
                opacity="0.6"
              />
            ))}
          </>
        )}

        {state === 'complete' && (
          <>
            {/* Complete State: Converged Harmonic Waveform & Assurance Seal */}
            <path
              d="M 40 200 
                 L 80 200 
                 Q 110 180, 140 200 
                 Q 170 160, 200 240 
                 Q 230 160, 260 200 
                 L 360 200"
              stroke="#059669"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx="200" cy="200" r="12" fill="#059669" fillOpacity="0.1" stroke="#059669" strokeWidth="1.5" />
            <path d="M 194 200 L 198 204 L 206 196" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}

        {/* 8. Focal Signal Detection Core Reticle */}
        {state !== 'complete' && (
          <>
            <circle cx="200" cy="200" r="5" fill="#09090B" />
            <circle
              cx="200"
              cy="200"
              r="15"
              stroke="#09090B"
              strokeWidth="1"
              strokeDasharray="2 3"
              className="animate-spin"
              style={{ animationDuration: '18s' }}
            />
          </>
        )}

        {/* 9. Scientific Coordinate Readout Accents */}
        <text x="200" y="66" textAnchor="middle" fill="#888888" fontSize="8" fontFamily="-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Plus Jakarta Sans', sans-serif" fontWeight="600" letterSpacing="0.12em">
          {state === 'listening'
            ? 'ACOUSTIC APERTURE // 16.0 kHz'
            : state === 'analysing'
            ? 'SPECTRAL MULTI-MODEL DISCRIMINATOR'
            : 'CRYPTOGRAPHIC ASSURANCE SEALED'}
        </text>
        <text x="200" y="340" textAnchor="middle" fill="#888888" fontSize="8" fontFamily="-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Plus Jakarta Sans', sans-serif" fontWeight="600" letterSpacing="0.12em">
          {state === 'listening'
            ? 'STATE: LISTENING / INGESTION'
            : state === 'analysing'
            ? 'STATE: L3 FORENSIC INFERENCE'
            : 'STATE: VERDICT CONFIRMED'}
        </text>
      </svg>
    </div>
  );
};
