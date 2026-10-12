import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import React from 'react';
const api = vi.hoisted(() => ({loadResources:vi.fn(),saveResources:vi.fn(),mountResource:vi.fn(),unmountResource:vi.fn(),openInFileManager:vi.fn(), isTauri:() => false, desktopCall:vi.fn(), errorMessage:(e: unknown) => (e as Error).message, ApiError:class extends Error { auth=false; }}));
vi.mock('../src/services/api', () => api);
vi.mock('../src/screens/Discovery', () => ({Discovery:() => null}));
vi.mock('../src/components/CloudModal', () => ({CloudModal:() => null}));
vi.mock('../src/components/DiagnosticsModal', () => ({DiagnosticsModal:() => null}));
vi.mock('../src/components/ShareFolderModal', () => ({ShareFolderModal:() => null}));
vi.mock('../src/components/ManualAddressModal', () => ({ManualAddressModal:() => null}));
import { App } from '../src/App';
const item = {name:'Photos',kind:'Network share',source:'smb://server/photos',target:'',auto:false,status:'Disconnected'};
beforeEach(() => { vi.clearAllMocks(); api.loadResources.mockResolvedValue([{...item}]); api.saveResources.mockResolvedValue(true); });
afterEach(cleanup);
describe('Connection lifecycle', () => {
  it('opens local network information from the dashboard', async () => {
    api.desktopCall.mockResolvedValue([{interface:'Ethernet',address:'10.2.3.4',subnet:'10.2.0.0/16',netmask:'255.255.0.0',gateways:['10.2.0.1']}]);
    render(<App />); await screen.findByText('Photos');
    await waitFor(() => expect(screen.getByRole('button', {name:'Local Network Info'}).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', {name:'Local Network Info'}));
    await screen.findByText('10.2.3.4');
    expect(screen.getByText('10.2.0.0/16')).toBeTruthy();
    expect(screen.getByText('255.255.0.0')).toBeTruthy();
    expect(screen.getByText('10.2.0.1')).toBeTruthy();
    expect(api.desktopCall).toHaveBeenCalledWith('network_info');
    fireEvent.click(screen.getByRole('button', {name:'Close',exact:true}));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
  it('shows a network query error', async () => {
    api.desktopCall.mockRejectedValue(new Error('Network query failed'));
    render(<App />); await screen.findByText('Photos');
    await waitFor(() => expect(screen.getByRole('button', {name:'Local Network Info'}).hasAttribute('disabled')).toBe(false));
    fireEvent.click(screen.getByRole('button', {name:'Local Network Info'}));
    await screen.findByRole('alert');
    expect(screen.getByText('Network query failed')).toBeTruthy();
  });
  it('does not open a file manager after failed connection', async () => {
    api.mountResource.mockRejectedValue(new Error('Server unavailable'));
    render(<App />); await screen.findByText('Photos');
    fireEvent.click(screen.getByRole('button',{name:'Open in File Manager'}));
    await screen.findByText('Server unavailable');
    expect(api.openInFileManager).not.toHaveBeenCalled(); expect(screen.getByText('Disconnected')).toBeTruthy();
  });
  it('shows connected only after backend confirmation', async () => {
    let finish!: (value:unknown) => void; api.mountResource.mockImplementation(() => new Promise(resolve => {finish=resolve;}));
    render(<App />); await screen.findByText('Photos');
    fireEvent.click(screen.getByRole('button',{name:'Connect',exact:true})); await screen.findByText('Connecting…');
    expect(screen.queryByText('Connected')).toBeNull();
    finish({...item,status:'Connected'}); await screen.findByText('Connected'); expect(api.saveResources).toHaveBeenCalled();
  });
  it('does not remove a live mount if disconnect fails', async () => {
    api.loadResources.mockResolvedValue([{...item,status:'Connected'}]); api.unmountResource.mockRejectedValue(new Error('Files are open'));
    render(<App />); await screen.findByText('Photos'); fireEvent.click(screen.getByRole('button',{name:'Remove'}));
    await screen.findByText('Files are open'); expect(screen.getByText('Photos')).toBeTruthy(); expect(api.saveResources).not.toHaveBeenCalled();
  });
  it('reconnects opted-in resources at launch', async () => {
    api.loadResources.mockResolvedValue([{...item,auto:true}]); api.mountResource.mockResolvedValue({...item,auto:true,status:'Connected'});
    render(<App />); await waitFor(() => expect(api.mountResource).toHaveBeenCalledTimes(1)); await screen.findByText('Connected');
  });
});

describe('Persistence after connection', () => {
  it('retains verified connected status when saving fails', async () => {
    api.mountResource.mockResolvedValue({...item,status:'Connected'}); api.saveResources.mockRejectedValue(new Error('Disk full'));
    render(<App />); await screen.findByText('Photos'); fireEvent.click(screen.getByRole('button',{name:'Connect',exact:true}));
    await screen.findByText('Disk full'); expect(screen.getByText('Connected')).toBeTruthy();
  });
});
