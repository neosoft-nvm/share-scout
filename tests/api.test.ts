import { describe, it, expect, vi, beforeEach } from 'vitest';
const invoke = vi.hoisted(() => vi.fn());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));
import { mountResource, loadResources, scanLocalNetwork, saveResources, ApiError } from '../src/services/api';
const item = { name:'Photos', kind:'Network share' as const, source:'smb://server/photos', target:'', auto:false, status:'Disconnected' as const };
beforeEach(() => { invoke.mockReset(); Object.defineProperty(window, '__TAURI_INTERNALS__', {value:{}, configurable:true}); });
describe('Desktop API results', () => {
  it('does not turn a failed mount into success', async () => { invoke.mockRejectedValue({message:'Mount failed',auth:false}); await expect(mountResource(item)).rejects.toThrow('Mount failed'); });
  it('preserves the authentication-needed flag', async () => { invoke.mockRejectedValue({message:'Sign in',auth:true}); await expect(mountResource(item)).rejects.toMatchObject({auth:true}); });
  it('does not substitute demo connections on settings failure', async () => { invoke.mockRejectedValue('Settings unreadable'); await expect(loadResources()).rejects.toThrow('Settings unreadable'); });
  it('keeps empty scan results empty', async () => { invoke.mockResolvedValue({devices:[],networks:[],cancelled:false}); expect((await scanLocalNetwork('test')).devices).toEqual([]); });
  it('propagates persistence failures', async () => { invoke.mockRejectedValue('Disk full'); await expect(saveResources([item])).rejects.toThrow('Disk full'); });
  it('browser preview cannot claim desktop operations succeeded', async () => { delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__; await expect(mountResource(item)).rejects.toBeInstanceOf(ApiError); expect(invoke).not.toHaveBeenCalled(); });
});
