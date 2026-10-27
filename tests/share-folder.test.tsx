import React from 'react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
const api = vi.hoisted(() => ({ pickFolder: vi.fn(), configureFolderShare: vi.fn(), errorMessage: (e: unknown) => (e as Error).message }));
vi.mock('../src/services/api', () => api);
import { ShareFolderModal } from '../src/components/ShareFolderModal';
beforeEach(() => vi.clearAllMocks());
afterEach(cleanup);
function submit() {
  fireEvent.change(screen.getByLabelText('Folder to Share'), { target: { value: '/home/test/Photos' } });
  fireEvent.click(screen.getByRole('button', { name: 'Start Sharing' }));
}
it('offers Done after confirmed sharing and resets when reopened', async () => {
  api.configureFolderShare.mockResolvedValue({ ok: true, address: '192.168.1.2', name: 'Photos' });
  const close = vi.fn();
  const view = render(<ShareFolderModal isOpen onClose={close} />);
  submit();
  fireEvent.click(await screen.findByRole('button', { name: 'Done' }));
  expect(close).toHaveBeenCalledOnce();
  expect(api.configureFolderShare).toHaveBeenCalledExactlyOnceWith('/home/test/Photos', 'Photos', true);
  expect(screen.queryByRole('button', { name: 'Start Sharing' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
  view.rerender(<ShareFolderModal isOpen={false} onClose={close} />);
  view.rerender(<ShareFolderModal isOpen onClose={close} />);
  expect(screen.getByRole('button', { name: 'Start Sharing' })).toBeTruthy();
  expect(screen.queryByRole('status')).toBeNull();
});
it('keeps retry and cancel available on failure', async () => {
  api.configureFolderShare.mockRejectedValue(new Error('Sharing failed'));
  render(<ShareFolderModal isOpen onClose={vi.fn()} />);
  submit();
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Sharing failed');
  expect(screen.getByRole('button', { name: 'Start Sharing' }).hasAttribute('disabled')).toBe(false);
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Done' })).toBeNull();
});
it('does not report success just because the Windows wizard opened', async () => {
  api.configureFolderShare.mockResolvedValue({ wizard: true, message: 'Complete the Windows sharing wizard.' });
  render(<ShareFolderModal isOpen onClose={vi.fn()} />);
  submit();
  await screen.findByText('Complete the Windows sharing wizard.');
  expect(screen.queryByRole('button', { name: 'Done' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Cancel' })).toBeTruthy();
});
