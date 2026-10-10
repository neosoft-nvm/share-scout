import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { Dashboard } from '../src/screens/Dashboard';
import { ResourceItem } from '../src/types';

const mockResources: ResourceItem[] = [
  {
    name: 'Family Photos',
    kind: 'Network share',
    source: 'smb://192.168.1.120/Family Photos',
    target: '',
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

describe('Dashboard Component', () => {
  it('renders branding and version badge', () => {
    render(
      <Dashboard
        resources={mockResources}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onOpen={vi.fn()}
        onConnect={vi.fn()}
        onDisconnect={vi.fn()}
        onRemove={vi.fn()}
        onOpenDiscovery={vi.fn()}
        onOpenCloud={vi.fn()}
        onOpenShareFolder={vi.fn()}
        onOpenManualAddress={vi.fn()}
        onRefreshConnections={vi.fn()}
        onCheckTools={vi.fn()}
        onCheckUpdates={vi.fn()}
      />
    );

    expect(screen.getByText('ShareScout')).toBeTruthy();
    expect(screen.getByText('0.6.0')).toBeTruthy();
  });

  it('renders all three action cards', () => {
    render(
      <Dashboard
        resources={mockResources}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onOpen={vi.fn()}
        onConnect={vi.fn()}
        onDisconnect={vi.fn()}
        onRemove={vi.fn()}
        onOpenDiscovery={vi.fn()}
        onOpenCloud={vi.fn()}
        onOpenShareFolder={vi.fn()}
        onOpenManualAddress={vi.fn()}
        onRefreshConnections={vi.fn()}
        onCheckTools={vi.fn()}
        onCheckUpdates={vi.fn()}
      />
    );

    expect(screen.getByText('Find Network Folders')).toBeTruthy();
    expect(screen.getByText('Connect Cloud Storage')).toBeTruthy();
    expect(screen.getByText('Share Local Folder')).toBeTruthy();
  });

  it('allows clicking an action card', () => {
    const handleDiscovery = vi.fn();
    render(
      <Dashboard
        resources={mockResources}
        selectedIndex={0}
        onSelectIndex={vi.fn()}
        onOpen={vi.fn()}
        onConnect={vi.fn()}
        onDisconnect={vi.fn()}
        onRemove={vi.fn()}
        onOpenDiscovery={handleDiscovery}
        onOpenCloud={vi.fn()}
        onOpenShareFolder={vi.fn()}
        onOpenManualAddress={vi.fn()}
        onRefreshConnections={vi.fn()}
        onCheckTools={vi.fn()}
        onCheckUpdates={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Scan Network'));
    expect(handleDiscovery).toHaveBeenCalledTimes(1);
  });
});
