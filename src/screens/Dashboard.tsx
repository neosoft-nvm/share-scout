import React from 'react';
import {
  Folder,
  Cloud,
  Radio,
  Share2,
  HardDrive,
  FolderOpen,
  Link,
  RotateCw,
  Wrench,
  Sparkles,
  ExternalLink,
} from 'lucide-react';
import { ResourceItem } from '../types';
import { ActionCard } from '../components/ActionCard';
import { StatusPill } from '../components/StatusPill';

interface DashboardProps {
  resources: ResourceItem[];
  selectedIndex: number | null;
  onSelectIndex: (index: number) => void;
  onOpen: (item: ResourceItem) => void;
  onConnect: (index: number) => void;
  onDisconnect: (index: number) => void;
  onRemove: (index: number) => void;
  onOpenDiscovery: () => void;
  onOpenCloud: () => void;
  onOpenShareFolder: () => void;
  onOpenManualAddress: () => void;
  onRefreshConnections: () => void;
  onCheckTools: () => void;
  onCheckUpdates: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  resources,
  selectedIndex,
  onSelectIndex,
  onOpen,
  onConnect,
  onDisconnect,
  onRemove,
  onOpenDiscovery,
  onOpenCloud,
  onOpenShareFolder,
  onOpenManualAddress,
  onRefreshConnections,
  onCheckTools,
  onCheckUpdates,
}) => {
  const connectedCount = resources.filter((r) => r.status === 'Connected').length;
  const selectedItem = selectedIndex !== null ? resources[selectedIndex] : null;

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 p-6 md:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-sm">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-black tracking-tight text-slate-900">
                ShareScout
              </h1>
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-700 border border-indigo-200">
                0.6.0
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Connect network shares, cloud storage, and local folders in seconds.
            </p>
          </div>
        </div>
      </header>

      {/* 3 Hero Action Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <ActionCard
          icon={<Radio className="w-6 h-6" />}
          title="Find Network Folders"
          description="Scan nearby PCs & NAS drives on your local Wi-Fi or LAN"
          buttonText="Scan Network"
          onAction={onOpenDiscovery}
          accent={true}
        />
        <ActionCard
          icon={<Cloud className="w-6 h-6" />}
          title="Connect Cloud Storage"
          description="Mount Google Drive & OneDrive directly to your desktop"
          buttonText="Add Cloud Drive"
          onAction={onOpenCloud}
        />
        <ActionCard
          icon={<Share2 className="w-6 h-6" />}
          title="Share Local Folder"
          description="Make folders on this PC accessible to your other devices"
          buttonText="Share Folder"
          onAction={onOpenShareFolder}
        />
      </section>

      {/* Connected & Saved Resources */}
      <section className="flex-1 flex flex-col mb-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-bold text-slate-900">
            Connected & Saved Resources
          </h2>
          <span className="text-xs text-slate-500 font-medium">
            {connectedCount} connected · {resources.length} saved
          </span>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden flex-1 min-h-[220px]">
          {resources.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center p-6">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
                <Folder className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-700">No folders connected yet</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Click <span className="font-semibold text-indigo-600">Scan Network</span> or{' '}
                <span className="font-semibold text-indigo-600">Add Cloud Drive</span> above to get started.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {resources.map((item, index) => {
                const isSelected = selectedIndex === index;
                return (
                  <div
                    key={index}
                    onClick={() => onSelectIndex(index)}
                    onDoubleClick={() => onOpen(item)}
                    className={`flex items-center justify-between px-5 py-3.5 transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 ring-1 ring-inset ring-indigo-500'
                        : 'hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                          item.kind === 'Network share'
                            ? 'bg-indigo-50 text-indigo-600'
                            : 'bg-sky-50 text-sky-600'
                        }`}
                      >
                        {item.kind === 'Network share' ? (
                          <Folder className="w-4 h-4" />
                        ) : (
                          <Cloud className="w-4 h-4" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-xs font-bold text-slate-900 truncate">
                            {item.name}
                          </p>
                          {item.auto && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600">
                              Auto
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-500 truncate font-mono mt-0.5">
                          {item.target || item.source}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 shrink-0">
                      <span className="hidden sm:inline-block text-xs font-medium text-slate-400">
                        {item.kind}
                      </span>
                      <StatusPill status={item.status} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Secondary Tools Card */}
      <section className="bg-white rounded-2xl border border-slate-200 p-4 mb-6 shadow-xs">
        <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
          More ways to connect & tools
        </h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2">
          <button
            type="button"
            onClick={onOpenManualAddress}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 transition-colors"
          >
            <Link className="w-3.5 h-3.5 text-slate-400" />
            <span>Add address</span>
          </button>
          <button
            type="button"
            onClick={onRefreshConnections}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5 text-slate-400" />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            onClick={onCheckTools}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 transition-colors"
          >
            <Wrench className="w-3.5 h-3.5 text-slate-400" />
            <span>Check tools</span>
          </button>
          <button
            type="button"
            onClick={onCheckUpdates}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-slate-400" />
            <span>Updates</span>
          </button>
          <button
            type="button"
            onClick={onOpenShareFolder}
            className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 hover:text-slate-900 border border-slate-200 transition-colors col-span-2 sm:col-span-1"
          >
            <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
            <span>Share PC</span>
          </button>
        </div>
      </section>

      {/* Persistent Bottom Action Dock */}
      <footer className="sticky bottom-0 bg-slate-50/90 backdrop-blur-md pt-2 pb-1 border-t border-slate-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={!selectedItem}
            onClick={() => selectedItem && onOpen(selectedItem)}
            className="flex items-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-all shadow-xs cursor-pointer disabled:cursor-not-allowed"
          >
            <FolderOpen className="w-4 h-4" />
            <span>Open in File Manager</span>
          </button>

          <button
            type="button"
            disabled={!selectedItem || selectedItem.status === 'Connected'}
            onClick={() => selectedIndex !== null && onConnect(selectedIndex)}
            className="py-2.5 px-3.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Connect
          </button>

          <button
            type="button"
            disabled={!selectedItem || selectedItem.status !== 'Connected'}
            onClick={() => selectedIndex !== null && onDisconnect(selectedIndex)}
            className="py-2.5 px-3.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Disconnect
          </button>

          <button
            type="button"
            disabled={!selectedItem}
            onClick={() => selectedIndex !== null && onRemove(selectedIndex)}
            className="py-2.5 px-3.5 rounded-xl text-xs font-semibold text-rose-600 bg-white hover:bg-rose-50 border border-slate-200 hover:border-rose-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Remove
          </button>
        </div>
      </footer>
    </div>
  );
};
