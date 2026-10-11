import React, { useState } from 'react';
import { Modal } from './Modal';
import { GoogleDriveSmallIcon, OneDriveSmallIcon } from './BrandIcons';
import { launchCloudSignIn } from '../services/api';

interface CloudModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddCloudAccount: (provider: 'Google Drive' | 'OneDrive', accountName: string) => void;
}

export const CloudModal: React.FC<CloudModalProps> = ({
  isOpen,
  onClose,
  onAddCloudAccount,
}) => {
  const [provider, setProvider] = useState<'Google Drive' | 'OneDrive'>('Google Drive');
  const [mountPath, setMountPath] = useState('~/ShareScout/Google Drive');
  const [driveName, setDriveName] = useState('Google Drive');
  const [connecting, setConnecting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    await launchCloudSignIn(provider);
    onAddCloudAccount(provider, driveName);
    setConnecting(false);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Connect Cloud Storage"
      subtitle="Mount Google Drive or Microsoft OneDrive directly to your desktop"
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-5 pt-2">
        {/* Two large selectable provider cards matching mockup */}
        <div className="grid grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => {
              setProvider('Google Drive');
              setDriveName('Google Drive');
              setMountPath('~/ShareScout/Google Drive');
            }}
            className={`p-6 rounded-2xl border flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
              provider === 'Google Drive'
                ? 'bg-indigo-50/50 border-indigo-400 ring-2 ring-indigo-400'
                : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="w-12 h-12 flex items-center justify-center">
              <GoogleDriveSmallIcon className="w-10 h-10" />
            </div>
            <span className="text-sm font-bold text-slate-900">Google Drive</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setProvider('OneDrive');
              setDriveName('OneDrive');
              setMountPath('~/ShareScout/OneDrive');
            }}
            className={`p-6 rounded-2xl border flex flex-col items-center justify-center gap-3 transition-all cursor-pointer ${
              provider === 'OneDrive'
                ? 'bg-indigo-50/50 border-indigo-400 ring-2 ring-indigo-400'
                : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="w-12 h-12 flex items-center justify-center">
              <OneDriveSmallIcon className="w-10 h-10" />
            </div>
            <span className="text-sm font-bold text-slate-900">Microsoft OneDrive</span>
          </button>
        </div>

        {/* Inputs matching mockup */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Mount folder path
          </label>
          <input
            type="text"
            required
            value={mountPath}
            onChange={(e) => setMountPath(e.target.value)}
            className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Drive Letter / Folder name
          </label>
          <input
            type="text"
            required
            value={driveName}
            onChange={(e) => setDriveName(e.target.value)}
            className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Footer dock matching mockup */}
        <div className="flex justify-center gap-3 pt-3">
          <button
            type="submit"
            disabled={connecting}
            className="py-2.5 px-6 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs cursor-pointer"
          >
            {connecting ? 'Connecting...' : 'Connect Account'}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="py-2.5 px-5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  );
};
