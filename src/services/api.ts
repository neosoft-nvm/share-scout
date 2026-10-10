import { ResourceItem, DiscoveredDevice, DiscoveredShare } from '../types';

const STORAGE_KEY = 'sharescout_connections_v1';

// Initial default demo resources if storage is empty
const DEFAULT_ITEMS: ResourceItem[] = [
  {
    name: 'Family Photos',
    kind: 'Network share',
    source: 'smb://192.168.1.120/Family Photos',
    target: '',
    auto: true,
    status: 'Connected',
  },
  {
    name: 'Google Drive',
    kind: 'Google Drive',
    source: 'Google Drive',
    target: '~/ShareScout/Google Drive',
    auto: true,
    status: 'Connected',
  },
  {
    name: 'Backup NAS',
    kind: 'Network share',
    source: 'smb://192.168.1.200/Backup',
    target: '',
    auto: false,
    status: 'Disconnected',
  },
];

export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
};

export const loadResources = async (): Promise<ResourceItem[]> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<ResourceItem[]>('get_saved_resources');
    } catch {
      // fallback
    }
  }
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEFAULT_ITEMS));
    return DEFAULT_ITEMS;
  }
  try {
    return JSON.parse(raw);
  } catch {
    return DEFAULT_ITEMS;
  }
};

export const saveResources = async (items: ResourceItem[]): Promise<void> => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('save_resources', { items });
    } catch {
      // ignore
    }
  }
};

export const mountResource = async (item: ResourceItem): Promise<boolean> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<boolean>('mount_resource', { item });
    } catch {
      // ignore
    }
  }
  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 600));
  return true;
};

export const unmountResource = async (item: ResourceItem): Promise<boolean> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<boolean>('unmount_resource', { item });
    } catch {
      // ignore
    }
  }
  await new Promise((resolve) => setTimeout(resolve, 400));
  return true;
};

export const openInFileManager = async (item: ResourceItem): Promise<void> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('open_file_manager', { path: item.target || item.source });
      return;
    } catch {
      // ignore
    }
  }
  console.log('Opening file manager for:', item.target || item.source);
};

export const scanLocalNetwork = async (): Promise<DiscoveredDevice[]> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<DiscoveredDevice[]>('scan_local_network');
    } catch {
      // fallback
    }
  }
  // Mock devices for standalone / browser testing
  await new Promise((resolve) => setTimeout(resolve, 800));
  return [
    { address: '192.168.1.120', name: 'Synology NAS', category: 'NAS' },
    { address: '192.168.1.155', name: 'LivingRoom-PC', category: 'Desktop' },
    { address: '192.168.1.180', name: 'Backup-Server', category: 'Server' },
  ];
};

export const listDeviceShares = async (address: string): Promise<DiscoveredShare[]> => {
  if (isTauri()) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      return await invoke<DiscoveredShare[]>('list_device_shares', { address });
    } catch {
      // fallback
    }
  }
  await new Promise((resolve) => setTimeout(resolve, 500));
  if (address === '192.168.1.120') {
    return [
      { name: 'Family Photos', comment: 'Family memories and archives', permission: 'Read/Write' },
      { name: 'Public', comment: 'Shared public files', permission: 'Guest Access' },
      { name: 'Media', comment: 'Home streaming media', permission: 'Read Only' },
    ];
  }
  return [
    { name: 'Documents', comment: 'User documents', permission: 'Read/Write' },
    { name: 'Shared', comment: 'General shared folder', permission: 'Read/Write' },
  ];
};
