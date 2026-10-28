import React from 'react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
const api = vi.hoisted(() => ({ permanentDefaults: vi.fn(), permanentPreview: vi.fn(), permanentApply: vi.fn(), permanentRemove: vi.fn(), errorMessage: (e: unknown) => (e as Error).message }));
vi.mock('../src/services/api', () => api);
import { PermanentMountModal } from '../src/components/PermanentMountModal';
const item = { name:'Movies',kind:'Network share' as const,source:'smb://server/Movies',auto:false,status:'Disconnected' as const };
const plan = { source:'//server/Movies',target:'/mnt/sharescout/Movies',account:'plex',readOnly:true,id:'test' };
beforeEach(() => {
  vi.clearAllMocks();
  api.permanentDefaults.mockResolvedValue({supported:true,target:plan.target,account:'plex',accounts:[{name:'plex',label:'Plex media server'}],approvalAvailable:true});
  api.permanentPreview.mockResolvedValue(plan);
});
afterEach(cleanup);
it('requires preview and explicit storage consent before mounting', async () => {
  const updated = vi.fn().mockResolvedValue(undefined);
  api.permanentApply.mockResolvedValue({ok:true,target:plan.target,resources:[]});
  render(<PermanentMountModal item={item} onClose={vi.fn()} onUpdated={updated} onBusy={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button',{name:'Review Mount'}));
  const confirm = await screen.findByRole('button',{name:'Confirm & Mount'});
  expect(confirm.hasAttribute('disabled')).toBe(true);
  expect(api.permanentApply).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('checkbox',{name:/Save this share/}));
  fireEvent.click(confirm);
  await screen.findByRole('button',{name:'Done'});
  expect(api.permanentApply).toHaveBeenCalledWith(item.source,plan.target,'plex',true,undefined);
  expect(updated).toHaveBeenCalledWith([]);
  expect(screen.getByRole('status').textContent).toContain(plan.target);
});
it('keeps failed setup open and does not report a successful mount', async () => {
  api.permanentApply.mockRejectedValue(new Error('Network folder unavailable'));
  render(<PermanentMountModal item={item} onClose={vi.fn()} onUpdated={vi.fn()} onBusy={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button',{name:'Review Mount'}));
  fireEvent.click(await screen.findByRole('checkbox',{name:/Save this share/}));
  fireEvent.click(screen.getByRole('button',{name:'Confirm & Mount'}));
  await screen.findByText('Network folder unavailable');
  expect(screen.queryByRole('button',{name:'Done'})).toBeNull();
});
it('requires a second confirmation before removing a mount', async () => {
  api.permanentDefaults.mockResolvedValue({supported:true,existing:{...plan,connected:true}});
  api.permanentRemove.mockResolvedValue({ok:true,resources:[]});
  render(<PermanentMountModal item={item} onClose={vi.fn()} onUpdated={vi.fn()} onBusy={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button',{name:'Remove Permanent Mount'}));
  expect(api.permanentRemove).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Confirm Removal'}));
  await waitFor(() => expect(api.permanentRemove).toHaveBeenCalledWith(item.source));
});
it('explains unsupported systems without offering a fake mount action', async () => {
  api.permanentDefaults.mockResolvedValue({supported:false,reason:'Linux with systemd required'});
  render(<PermanentMountModal item={item} onClose={vi.fn()} onUpdated={vi.fn()} onBusy={vi.fn()} />);
  await screen.findByText('Linux with systemd required');
  expect(screen.queryByRole('button',{name:'Review Mount'})).toBeNull();
});
