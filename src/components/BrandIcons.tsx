import React from 'react';

// Card 1: Radar / Compass scanner target
export const RadarIcon: React.FC<{ className?: string }> = ({ className = 'w-12 h-12' }) => (
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    <circle cx="24" cy="24" r="21" stroke="#4f46e5" strokeWidth="2.5" fill="#eef2ff" />
    <circle cx="24" cy="24" r="14" stroke="#818cf8" strokeWidth="2" strokeDasharray="3 3" />
    <circle cx="24" cy="24" r="7" stroke="#6366f1" strokeWidth="2" />
    <circle cx="24" cy="24" r="2.5" fill="#4338ca" />
    <line x1="24" y1="3" x2="24" y2="45" stroke="#a5b4fc" strokeWidth="1.5" />
    <line x1="3" y1="24" x2="45" y2="24" stroke="#a5b4fc" strokeWidth="1.5" />
    <line x1="24" y1="24" x2="38" y2="10" stroke="#4f46e5" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);

// Card 2: Google Drive + Microsoft OneDrive dual brand logo
export const CloudDualIcon: React.FC<{ className?: string }> = ({ className = 'h-12' }) => (
  <div className={`flex items-center gap-2.5 ${className}`}>
    {/* Google Drive Official Colors */}
    <svg viewBox="0 0 87.3 78" className="w-10 h-9" xmlns="http://www.w3.org/2000/svg">
      <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
      <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00ac47"/>
      <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/>
      <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
      <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
      <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
    </svg>

    {/* Microsoft OneDrive Cloud Logo */}
    <svg viewBox="0 0 32 32" className="w-11 h-9" xmlns="http://www.w3.org/2000/svg">
      <path d="M19.3 10.1c-1.2 0-2.4.4-3.3 1.1-.9-2.1-3-3.6-5.5-3.6-3.3 0-6 2.7-6 6 0 .4.1.8.1 1.2C2 15.6 0 18.2 0 21.3 0 24.9 3 27.9 6.7 27.9h14.5c4.1 0 7.4-3.3 7.4-7.4 0-3.9-3.1-7.1-7-7.4-.6-1.7-2.3-3-4.3-3z" fill="#0078d4" />
      <path d="M22.5 14.5c-.4 0-.8.1-1.2.2 1 1 1.7 2.4 1.7 4 0 2.2-1.3 4.1-3.2 5h6.4c3.2 0 5.8-2.6 5.8-5.8 0-3.1-2.4-5.6-5.4-5.8-.8-1.5-2.4-2.6-4.1-2.6v5z" fill="#1490df" opacity="0.8" />
    </svg>
  </div>
);

// Card 3: Share Folder with Sharing Nodes
export const ShareFolderIcon: React.FC<{ className?: string }> = ({ className = 'w-12 h-12' }) => (
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
    {/* Folder outline */}
    <path d="M6 14C6 11.7909 7.79086 10 10 10H18.5858C19.6466 10 20.664 10.4214 21.4142 11.1716L24.8284 14.5858C25.5786 15.336 26.596 15.7574 27.6569 15.7574H38C40.2091 15.7574 42 17.5482 42 19.7574V34C42 36.2091 40.2091 38 38 38H10C7.79086 38 6 36.2091 6 34V14Z" stroke="#4f46e5" strokeWidth="2.5" strokeLinejoin="round" fill="#ffffff"/>
    {/* Sharing node network badge */}
    <circle cx="34" cy="30" r="3" fill="#4f46e5" />
    <circle cx="39" cy="24" r="2.5" fill="#4f46e5" />
    <circle cx="39" cy="36" r="2.5" fill="#4f46e5" />
    <line x1="34" y1="30" x2="39" y2="24" stroke="#4f46e5" strokeWidth="1.8" />
    <line x1="34" y1="30" x2="39" y2="36" stroke="#4f46e5" strokeWidth="1.8" />
  </svg>
);

// Table SMB Icon (PC + Screen)
export const SmbIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <line x1="8" y1="21" x2="16" y2="21" />
    <line x1="12" y1="17" x2="12" y2="21" />
  </svg>
);

// Table Google Drive Icon
export const GoogleDriveSmallIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg viewBox="0 0 87.3 78" className={className} xmlns="http://www.w3.org/2000/svg">
    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da"/>
    <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44c-.8 1.4-1.2 2.95-1.2 4.5h27.5z" fill="#00ac47"/>
    <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335"/>
    <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d"/>
    <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc"/>
    <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00"/>
  </svg>
);

// Table OneDrive Icon
export const OneDriveSmallIcon: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg viewBox="0 0 32 32" className={className} xmlns="http://www.w3.org/2000/svg">
    <path d="M19.3 10.1c-1.2 0-2.4.4-3.3 1.1-.9-2.1-3-3.6-5.5-3.6-3.3 0-6 2.7-6 6 0 .4.1.8.1 1.2C2 15.6 0 18.2 0 21.3 0 24.9 3 27.9 6.7 27.9h14.5c4.1 0 7.4-3.3 7.4-7.4 0-3.9-3.1-7.1-7-7.4-.6-1.7-2.3-3-4.3-3z" fill="#0078d4" />
  </svg>
);
