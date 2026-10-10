export interface ResourceItem {
  id?: string;
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
  permission?: 'Read/Write' | 'Read Only' | 'Guest Access';
}
