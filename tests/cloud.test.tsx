import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react';
const api = vi.hoisted(() => ({cloudStart:vi.fn(),cloudStep:vi.fn(),cloudCancel:vi.fn(),cloudFinish:vi.fn(),cloudAccounts:vi.fn(),getDefaults:vi.fn(),errorMessage:(e:unknown) => (e as Error).message}));
vi.mock('../src/services/api', () => api);
import { CloudModal } from '../src/components/CloudModal';
beforeEach(() => {vi.clearAllMocks(); api.cloudAccounts.mockResolvedValue([]); api.getDefaults.mockResolvedValue({windows:false,mountRoot:'/home/test/ShareScout',drive:''}); api.cloudStart.mockResolvedValue({session:'unique',remote:'unique'});api.cloudFinish.mockResolvedValue(true); api.cloudCancel.mockResolvedValue(true);});
afterEach(cleanup);
describe('Cloud sign-in lifecycle', () => {
  it('does not create a connected item before OAuth finishes', async () => {
    const add=vi.fn(); api.cloudStep.mockResolvedValue({State:'choose',Option:{Name:'drive',Help:'Choose a drive',Default:'personal'}});
    render(<CloudModal isOpen onClose={vi.fn()} onAddCloudAccount={add} />);
    await waitFor(() => expect((screen.getByLabelText('Mount folder path') as HTMLInputElement).value).toContain('/home/test'));
    fireEvent.click(screen.getByRole('button',{name:'Connect Account'}));await screen.findByText('Choose a drive');expect(add).not.toHaveBeenCalled();
  });
  it('passes the actual remote and chosen mount path after sign-in', async () => {
    const add=vi.fn().mockResolvedValue(undefined);api.cloudStep.mockResolvedValue({State:''});
    render(<CloudModal isOpen onClose={vi.fn()} onAddCloudAccount={add} />);
    await waitFor(() => expect((screen.getByLabelText('Mount folder path') as HTMLInputElement).value).toContain('/home/test'));
    fireEvent.change(screen.getByLabelText('Mount folder path'),{target:{value:'/home/test/My Cloud'}});
    fireEvent.click(screen.getByRole('button',{name:'Connect Account'}));
    await waitFor(() => expect(add).toHaveBeenCalledWith(expect.objectContaining({source:'unique',target:'/home/test/My Cloud',status:'Disconnected'})));
  });
  it('cancels the owned OAuth session', async () => {
    api.cloudStep.mockResolvedValue({State:'choose',Option:{Help:'Choose a drive'}}); const close=vi.fn();
    render(<CloudModal isOpen onClose={close} onAddCloudAccount={vi.fn()} />);
    await waitFor(() => expect((screen.getByLabelText('Mount folder path') as HTMLInputElement).value).toContain('/home/test'));
    fireEvent.click(screen.getByRole('button',{name:'Connect Account'}));await screen.findByText('Choose a drive');
    fireEvent.click(screen.getByRole('button',{name:'Cancel'}));await waitFor(() => expect(api.cloudCancel).toHaveBeenCalledWith('unique'));await waitFor(() => expect(close).toHaveBeenCalled());
  });
  it('keeps the dialog open when mounting fails', async () => {
    api.cloudStep.mockResolvedValue({State:''});const close=vi.fn();const add=vi.fn().mockRejectedValue(new Error('FUSE unavailable'));
    render(<CloudModal isOpen onClose={close} onAddCloudAccount={add} />);
    await waitFor(() => expect((screen.getByLabelText('Mount folder path') as HTMLInputElement).value).toContain('/home/test'));
    fireEvent.click(screen.getByRole('button',{name:'Connect Account'}));await screen.findByText('FUSE unavailable');expect(close).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Retry connection'})).toBeTruthy();
  });
});
