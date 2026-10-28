import React from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
const api = vi.hoisted(() => ({ listLocalShares: vi.fn(), errorMessage: (e: unknown) => (e as Error).message }));
vi.mock('../src/services/api', () => api);
import { LocalSharesModal } from '../src/components/LocalSharesModal';
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
it('lists local shares before offering setup and refreshes after returning', async () => {
  api.listLocalShares.mockResolvedValueOnce({ shares: [{ name: 'Movies', path: '/mnt/games', access: 'Read only', available: true, hidden: true }], warnings: [] })
    .mockResolvedValue({ shares: [{ name: 'Photos', path: '/home/test/Photos', access: 'Read & write', available: true, hidden: false }], warnings: [] });
  const setup = vi.fn();
  const view = render(<LocalSharesModal isOpen onClose={vi.fn()} onSetup={setup} />);
  await screen.findByText('Movies');
  expect(screen.getByText('/mnt/games')).toBeTruthy();
  expect(screen.queryByText('Start Sharing')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Set Up a Share' }));
  expect(setup).toHaveBeenCalledOnce();
  view.rerender(<LocalSharesModal isOpen={false} onClose={vi.fn()} onSetup={setup} />);
  view.rerender(<LocalSharesModal isOpen onClose={vi.fn()} onSetup={setup} />);
  await screen.findByText('Photos');
  expect(screen.queryByText('Movies')).toBeNull();
});
it('shows read failures with retry instead of claiming there are no shares', async () => {
  api.listLocalShares.mockRejectedValueOnce(new Error('Cannot read shares')).mockResolvedValue({ shares: [], warnings: ['File-manager shares unavailable'] });
  render(<LocalSharesModal isOpen onClose={vi.fn()} onSetup={vi.fn()} />);
  await screen.findByRole('alert');
  expect(screen.queryByText('No local folder shares found.')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'Refresh' }));
  await screen.findByText('File-manager shares unavailable');
  expect(screen.getByText('No local folder shares found.')).toBeTruthy();
});
