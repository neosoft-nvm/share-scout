import type { ResourceItem, DiscoveredShare, Credentials, ScanResult, CloudQuestion, Diagnostics } from '../types';

export class ApiError extends Error {
  auth: boolean;
  constructor(value: unknown) {
    const detail = value && typeof value === 'object' ? value as { message?: string; auth?: boolean } : null;
    super(detail?.message || (typeof value === 'string' ? value : 'The operation could not finish.'));
    this.auth = !!detail?.auth;
  }
}
export const isTauri = () => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : new ApiError(error).message;

export async function desktopCall<T>(method: string, args: Record<string, unknown> = {}): Promise<T> {
  if (!isTauri()) throw new ApiError('Open the ShareScout desktop app to use this feature.');
  try {
    const { invoke } = await import('@tauri-apps/api/core');
    return await invoke<T>('desktop_call', { method, args });
  } catch (error) { throw new ApiError(error); }
}

export const loadResources = () => desktopCall<ResourceItem[]>('load');
export const saveResources = (items: ResourceItem[]) => desktopCall<boolean>('save', { items });
export const mountResource = (item: ResourceItem, credentials?: Credentials, remember = false) =>
  desktopCall<ResourceItem>('mount', { item, credentials, remember });
export const unmountResource = (item: ResourceItem) => desktopCall<boolean>('unmount', { item });
export const openInFileManager = (item: ResourceItem) => desktopCall<boolean>('open', { item });
export const scanLocalNetwork = (scanId: string) => desktopCall<ScanResult>('scan', { scanId });
export const stopScan = (scanId: string) => desktopCall<boolean>('stop_scan', { scanId });
export const listDeviceShares = (address: string, credentials?: Credentials, remember = false) =>
  desktopCall<DiscoveredShare[]>('shares', { address, credentials, remember });
export const pickFolder = () => desktopCall<string | null>('pick_folder');
export const configureFolderShare = (folderPath: string, shareName: string, readOnly: boolean) =>
  desktopCall<{ ok: boolean; wizard?: boolean; message?: string; address?: string; name?: string }>('share', { folderPath, shareName, readOnly });
export const cloudAccounts = () => desktopCall<{ remote: string; provider: 'Google Drive' | 'OneDrive' }[]>('cloud_accounts');
export const cloudStart = (provider: string) => desktopCall<{ session: string; remote: string }>('cloud_start', { provider });
export const cloudStep = (session: string, state?: string, answer?: string | boolean) => desktopCall<CloudQuestion>('cloud_step', { session, state, answer });
export const cloudCancel = (session: string) => desktopCall<boolean>('cloud_cancel', { session });
export const cloudFinish = (session: string) => desktopCall<boolean>('cloud_finish', { session });
export const getDefaults = () => desktopCall<{ windows: boolean; mountRoot: string; drive: string; version: string }>('defaults');
export const runDiagnostics = () => desktopCall<Diagnostics>('diagnostics');
export const repairSharing = () => desktopCall<{ message?: string }>('repair');
export const checkUpdates = () => desktopCall<{ installed: string; latest: string; newer: boolean; canInstall: boolean }>('check_updates');

export const prepareUpdate = (version: string) => desktopCall<string>("prepare_update", { version });
export const installUpdate = (stage: string) => desktopCall<boolean>("install_update", { stage });

export interface UpdateInfo { installed: string; latest: string; newer: boolean; canInstall: boolean; }
export const startupUpdate = () => desktopCall<UpdateInfo | null>('startup_update');
export const setUpdatePreference = (automatic: boolean) => desktopCall<boolean>('update_preference', { automatic });

export interface PermanentMountPlan {
  source: string; target: string; account: string; readOnly: boolean; id: string;
}
export interface PermanentMountDefaults {
  supported: boolean; reason?: string; target?: string; account?: string;
  accounts?: { name: string; label: string }[]; toolsReady?: boolean; approvalAvailable?: boolean;
  existing?: (PermanentMountPlan & { connected: boolean }) | null;
}
export const permanentDefaults = (source: string) => desktopCall<PermanentMountDefaults>('permanent_defaults', { source });
export const permanentPreview = (source: string, target: string, account: string, readOnly: boolean) =>
  desktopCall<PermanentMountPlan>('permanent_preview', { source, target, account, readOnly });
export const permanentApply = (source: string, target: string, account: string, readOnly: boolean, credentials?: Credentials) =>
  desktopCall<{ ok: boolean; target: string; resources: ResourceItem[] }>('permanent_apply', { source, target, account, readOnly, credentials });
export const permanentRemove = (source: string) =>
  desktopCall<{ ok: boolean; removed: boolean; resources: ResourceItem[] }>('permanent_remove', { source });
