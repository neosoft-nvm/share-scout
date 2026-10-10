import React, { useState, useEffect } from 'react';
import { ResourceItem } from './types';
import {
  loadResources,
  saveResources,
  mountResource,
  unmountResource,
  openInFileManager,
} from './services/api';
import { Dashboard } from './screens/Dashboard';
import { Discovery } from './screens/Discovery';
import { CloudModal } from './components/CloudModal';
import { ManualAddressModal } from './components/ManualAddressModal';
import { ShareFolderModal } from './components/ShareFolderModal';

export const App: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<'dashboard' | 'discovery'>('dashboard');
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(0);

  // Modals
  const [isCloudOpen, setIsCloudOpen] = useState(false);
  const [isManualOpen, setIsManualOpen] = useState(false);
  const [isShareFolderOpen, setIsShareFolderOpen] = useState(false);

  useEffect(() => {
    loadResources().then((items) => {
      setResources(items);
      if (items.length > 0 && selectedIndex === null) {
        setSelectedIndex(0);
      }
    });
  }, []);

  const updateResources = (newItems: ResourceItem[]) => {
    setResources(newItems);
    saveResources(newItems);
  };

  const handleOpen = async (item: ResourceItem) => {
    if (item.status !== 'Connected') {
      const idx = resources.findIndex((r) => r === item);
      if (idx !== -1) {
        await handleConnect(idx);
      }
    }
    await openInFileManager(item);
  };

  const handleConnect = async (index: number) => {
    const updated = [...resources];
    updated[index] = { ...updated[index], status: 'Connecting…' };
    setResources(updated);

    const success = await mountResource(updated[index]);
    if (success) {
      updated[index] = { ...updated[index], status: 'Connected' };
    } else {
      updated[index] = { ...updated[index], status: 'Disconnected' };
    }
    updateResources(updated);
  };

  const handleDisconnect = async (index: number) => {
    const updated = [...resources];
    updated[index] = { ...updated[index], status: 'Connecting…' };
    setResources(updated);

    const success = await unmountResource(updated[index]);
    if (success) {
      updated[index] = { ...updated[index], status: 'Disconnected' };
    }
    updateResources(updated);
  };

  const handleRemove = (index: number) => {
    const updated = resources.filter((_, i) => i !== index);
    updateResources(updated);
    if (selectedIndex === index) {
      setSelectedIndex(updated.length > 0 ? 0 : null);
    } else if (selectedIndex !== null && selectedIndex > index) {
      setSelectedIndex(selectedIndex - 1);
    }
  };

  const handleConnectDiscoveredShare = (
    deviceAddress: string,
    shareName: string,
    autoReconnect: boolean
  ) => {
    const source = `smb://${deviceAddress}/${shareName}`;
    const existingIndex = resources.findIndex((r) => r.source === source);

    if (existingIndex !== -1) {
      setSelectedIndex(existingIndex);
      handleConnect(existingIndex);
      return;
    }

    const newItem: ResourceItem = {
      name: `${shareName} · ${deviceAddress}`,
      kind: 'Network share',
      source,
      target: '',
      auto: autoReconnect,
      status: 'Connected',
    };

    const updated = [...resources, newItem];
    updateResources(updated);
    const newIdx = updated.length - 1;
    setSelectedIndex(newIdx);
    mountResource(newItem);
  };

  const handleAddManualAddress = (name: string, address: string, auto: boolean) => {
    const newItem: ResourceItem = {
      name,
      kind: 'Network share',
      source: address,
      target: '',
      auto,
      status: 'Connected',
    };
    const updated = [...resources, newItem];
    updateResources(updated);
    setSelectedIndex(updated.length - 1);
    mountResource(newItem);
  };

  const handleAddCloudAccount = (
    provider: 'Google Drive' | 'OneDrive',
    accountName: string
  ) => {
    const newItem: ResourceItem = {
      name: accountName,
      kind: provider,
      source: accountName,
      target: `~/ShareScout/${accountName}`,
      auto: true,
      status: 'Connected',
    };
    const updated = [...resources, newItem];
    updateResources(updated);
    setSelectedIndex(updated.length - 1);
    mountResource(newItem);
  };

  return (
    <>
      {currentScreen === 'dashboard' ? (
        <Dashboard
          resources={resources}
          selectedIndex={selectedIndex}
          onSelectIndex={setSelectedIndex}
          onOpen={handleOpen}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onRemove={handleRemove}
          onOpenDiscovery={() => setCurrentScreen('discovery')}
          onOpenCloud={() => setIsCloudOpen(true)}
          onOpenShareFolder={() => setIsShareFolderOpen(true)}
          onOpenManualAddress={() => setIsManualOpen(true)}
          onRefreshConnections={() => loadResources().then(setResources)}
          onCheckTools={() => alert('All required tools (smbclient, gio, rclone, FUSE) are installed and ready.')}
          onCheckUpdates={() => alert('ShareScout v0.6.0 is up to date.')}
        />
      ) : (
        <Discovery
          onBack={() => setCurrentScreen('dashboard')}
          onConnectShare={handleConnectDiscoveredShare}
        />
      )}

      {/* Dialog Modals */}
      <CloudModal
        isOpen={isCloudOpen}
        onClose={() => setIsCloudOpen(false)}
        onAddCloudAccount={handleAddCloudAccount}
      />

      <ManualAddressModal
        isOpen={isManualOpen}
        onClose={() => setIsManualOpen(false)}
        onAddAddress={handleAddManualAddress}
      />

      <ShareFolderModal
        isOpen={isShareFolderOpen}
        onClose={() => setIsShareFolderOpen(false)}
      />
    </>
  );
};

export default App;
