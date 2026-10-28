import React from 'react';
import {
  Folder,
  FolderOpen,
} from 'lucide-react';
import { ResourceItem } from '../types';
import { ActionCard } from '../components/ActionCard';
import { StatusPill } from '../components/StatusPill';
import {
  RadarIcon,
  CloudDualIcon,
  ShareFolderIcon,
  SmbIcon,
  GoogleDriveSmallIcon,
  OneDriveSmallIcon,
} from '../components/BrandIcons';

interface DashboardProps {
  resources: ResourceItem[];
  busy?: boolean;
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
  onRefreshConnections?: () => void;
  onCheckTools?: () => void;
  onNetworkInfo?: () => void;
  onPermanentMount?: (item: ResourceItem) => void;
  onToggleAuto?: (index: number, auto: boolean) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  resources,
  busy = false,
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
  onCheckTools,
  onNetworkInfo,
  onPermanentMount,
  onToggleAuto,
  onRefreshConnections,
}) => {
  const selectedItem = selectedIndex !== null ? resources[selectedIndex] : null;

  return (
    <div className="app-screen dashboard">
      {/* Header matching mockup */}
      <header className="dashboard-header flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm">
            {/* ShareScout Node Brand Icon from mockup */}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5">
              <circle cx="18" cy="5" r="3" fill="currentColor"/>
              <circle cx="6" cy="12" r="3" fill="currentColor"/>
              <circle cx="18" cy="19" r="3" fill="currentColor"/>
              <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
              <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
            </svg>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            ShareScout
          </h1>
        </div>
      </header>

      {/* 3 Hero Action Cards matching mockup */}
      <section className="hero-cards">
        <ActionCard
          icon={<RadarIcon className="w-14 h-14" />}
          title="Find Network Folders"
          disabled={busy}
          onAction={onOpenDiscovery}
          accent={true}
        />
        <ActionCard
          icon={<CloudDualIcon className="h-14" />}
          title="Connect Cloud Storage"
          disabled={busy}
          onAction={onOpenCloud}
        />
        <ActionCard
          icon={<ShareFolderIcon className="w-14 h-14" />}
          title="Share a Local Folder"
          disabled={busy}
          onAction={onOpenShareFolder}
        />
      </section>

      {/* Saved & Connected Folders Section matching mockup */}
      <section className="folder-section">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-base font-bold text-slate-900">
            Connections to Network & Cloud Folders
          </h2>
          <label className="flex items-center gap-2 text-xs text-slate-600">
            <input type="checkbox" checked={!!selectedItem?.auto} disabled={busy || !selectedItem || selectedItem.mountMode === 'system' || !onToggleAuto}
              onChange={event => selectedIndex !== null && onToggleAuto?.(selectedIndex, event.target.checked)} />
            Reconnect selected folder when app opens
          </label>
          <button className="text-xs underline text-slate-600" disabled={busy} onClick={onRefreshConnections}>Refresh</button>
        </div>

        <div className="folder-table">
          {/* Mockup Table Header */}
          <div className="grid grid-cols-12 gap-4 px-6 py-3 bg-slate-50/70 border-b border-slate-200 text-xs font-semibold text-slate-700">
            <div className="col-span-3">Folder Name</div>
            <div className="col-span-2">Type</div>
            <div className="col-span-4">Network Location or Path</div>
            <div className="col-span-2 text-center">Status</div>
            <div className="col-span-1 text-center">Reconnect</div>
          </div>

          {resources.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center p-6 my-auto">
              <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
                <Folder className="w-6 h-6" />
              </div>
              <p className="text-sm font-semibold text-slate-700">No folders connected yet</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Click <span className="font-semibold text-indigo-600">Find Network Folders</span> or{' '}
                <span className="font-semibold text-indigo-600">Connect Cloud Storage</span> above to get started.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-slate-100 flex-1 overflow-y-auto">
              {resources.map((item, index) => {
                const isSelected = selectedIndex === index;
                const isGoogle = item.kind === 'Google Drive';
                const isOneDrive = item.kind === 'OneDrive';

                return (
                  <div
                    key={item.kind + item.source}
                    role="button" tabIndex={0} aria-pressed={isSelected}
                    onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelectIndex(index); } }}
                    onClick={() => onSelectIndex(index)}
                    onDoubleClick={() => { if (!busy) onOpen(item); }}
                    className={`grid grid-cols-12 gap-4 px-6 py-3.5 items-center transition-colors cursor-pointer text-xs ${
                      isSelected
                        ? 'bg-indigo-50/70 ring-1 ring-inset ring-indigo-500'
                        : 'hover:bg-slate-50/80'
                    }`}
                  >
                    {/* Folder Name */}
                    <div className="col-span-3 font-semibold text-slate-900 truncate">
                      {item.name}
                    </div>

                    {/* Type with authentic brand icon */}
                    <div className="col-span-2 flex items-center gap-2 text-slate-700 font-medium truncate">
                      {isOneDrive ? (
                        <OneDriveSmallIcon className="w-4 h-4 shrink-0" />
                      ) : isGoogle ? (
                        <GoogleDriveSmallIcon className="w-4 h-4 shrink-0" />
                      ) : (
                        <SmbIcon className="w-4 h-4 text-slate-600 shrink-0" />
                      )}
                      <span>
                        {isOneDrive
                          ? 'OneDrive'
                          : isGoogle
                          ? 'Google Drive'
                          : item.mountMode === 'system' ? 'SMB · Permanent' : 'SMB'}
                      </span>
                    </div>

                    {/* Network Location or Path */}
                    <div className="col-span-4 text-slate-500 font-mono text-[11px] truncate">
                      {item.target || item.source}
                    </div>

                    {/* Status Pill Badge */}
                    <div className="col-span-2 flex justify-center">
                      <StatusPill status={item.status} />
                    </div>

                    {/* On-Launch */}
                    <div className="col-span-1 text-center font-medium text-slate-700">
                      {item.mountMode === 'system' ? 'At boot' : item.auto ? 'On' : 'Off'}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </section>

      {/* Persistent Bottom Action Dock matching mockup */}
      <footer className="dashboard-footer">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={busy || !selectedItem || selectedItem.status === 'Connecting…'}
            onClick={() => selectedItem && onOpen(selectedItem)}
            className="flex items-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs cursor-pointer disabled:cursor-not-allowed"
          >
            <FolderOpen className="w-4 h-4" />
            <span>Open in File Manager</span>
          </button>

          <button
            type="button"
            disabled={busy || !selectedItem || selectedItem.status !== 'Disconnected'}
            onClick={() => selectedIndex !== null && onConnect(selectedIndex)}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Connect
          </button>

          <button
            type="button"
            disabled={busy || !selectedItem || selectedItem.mountMode === 'system' || selectedItem.status !== 'Connected'}
            onClick={() => selectedIndex !== null && onDisconnect(selectedIndex)}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Disconnect
          </button>

          <button
            type="button"
            disabled={busy || !selectedItem || selectedItem.mountMode === 'system' || selectedItem.status === 'Connecting…'}
            onClick={() => selectedIndex !== null && onRemove(selectedIndex)}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-rose-600 bg-white hover:bg-rose-50 border border-slate-200 hover:border-rose-200 disabled:opacity-50 transition-all cursor-pointer disabled:cursor-not-allowed"
          >
            Remove
          </button>
        </div>

        <button type="button" className="secondary" disabled={busy || !selectedItem || selectedItem.kind !== 'Network share'} onClick={() => selectedItem && onPermanentMount?.(selectedItem)}>
          {selectedItem?.mountMode === 'system' ? 'Manage Permanent Mount' : 'Permanent Mount…'}
        </button>

        {/* Right-aligned links from mockup */}
        <div className="flex items-center gap-5 text-xs">
          <button type="button" disabled={busy} onClick={onNetworkInfo}
            className="text-slate-600 hover:text-indigo-600 underline font-medium cursor-pointer transition-colors">
            Local Network Info
          </button>
          <button
            type="button"
            disabled={busy} onClick={onOpenManualAddress}
            className="text-slate-600 hover:text-indigo-600 underline font-medium cursor-pointer transition-colors"
          >
            Manual Network Address
          </button>
          <button
            type="button"
            disabled={busy} onClick={onCheckTools}
            className="text-slate-600 hover:text-indigo-600 underline font-medium cursor-pointer transition-colors"
          >
            Sharing Diagnostics
          </button>
        </div>
      </footer>
    </div>
  );
};
