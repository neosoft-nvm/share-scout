export interface ResourceItem {
  id?: string;
  warning?: string;
  mountMode?: 'system';
  name: string;
  kind: 'Network share' | 'Google Drive' | 'OneDrive';
  source: string;
  target?: string;
  auto: boolean;
  status: 'Connected' | 'Connecting…' | 'Disconnected';
}

export interface DiscoveredDevice {
  address: string;
  name?: string;
  category?: 'Desktop' | 'NAS' | 'Server' | 'Laptop';
}

export interface DiscoveredShare {
  name: string;
  comment?: string;
  permission?: 'Read/Write' | 'Read Only' | 'Guest Access' | 'Password Protected' | 'Guest';
}

export interface Credentials { username: string; password: string; domain: string; }
export interface ScanResult {
  devices: DiscoveredDevice[];
  networks: { network: string; local: string; limited: boolean }[];
  cancelled: boolean;
}
export interface CloudQuestion {
  State: string;
  Error?: string;
  Option?: { Name?: string; Help?: string; Default?: string | boolean; Required?: boolean;
    Exclusive?: boolean; IsPassword?: boolean; Examples?: { Value: string; Help?: string }[] };
}
export interface Diagnostics {
  windows: boolean;
  version: string;
  checks: { name: string; status: string; desc: string; ok: boolean }[];
}
