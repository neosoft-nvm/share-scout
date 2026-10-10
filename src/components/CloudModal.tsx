import React, { useState } from 'react';
import { Cloud, ExternalLink } from 'lucide-react';
import { Modal } from './Modal';

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
  const [accountName, setAccountName] = useState('Personal Drive');
  const [connecting, setConnecting] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setConnecting(true);
    setTimeout(() => {
      onAddCloudAccount(provider, accountName);
      setConnecting(false);
      onClose();
    }, 800);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Connect Cloud Storage"
      subtitle="Sign in securely via your web browser"
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Provider selection */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => {
              setProvider('Google Drive');
              setAccountName('Google Drive');
            }}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              provider === 'Google Drive'
                ? 'bg-indigo-50/60 border-indigo-500 ring-1 ring-indigo-500 text-indigo-900'
                : 'border-slate-200 hover:border-slate-300 text-slate-700'
            }`}
          >
            <Cloud className="w-6 h-6 text-indigo-600" />
            <span className="text-xs font-bold">Google Drive</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setProvider('OneDrive');
              setAccountName('OneDrive');
            }}
            className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all ${
              provider === 'OneDrive'
                ? 'bg-indigo-50/60 border-indigo-500 ring-1 ring-indigo-500 text-indigo-900'
                : 'border-slate-200 hover:border-slate-300 text-slate-700'
            }`}
          >
            <Cloud className="w-6 h-6 text-sky-600" />
            <span className="text-xs font-bold">Microsoft OneDrive</span>
          </button>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Drive Friendly Name
          </label>
          <input
            type="text"
            required
            value={accountName}
            onChange={(e) => setAccountName(e.target.value)}
            className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-[11px] text-slate-500 leading-relaxed flex items-start gap-2">
          <ExternalLink className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
          <span>
            Clicking connect will launch your browser for direct OAuth authorization. No passwords are stored.
          </span>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="py-2 px-3.5 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={connecting}
            className="py-2 px-4 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
          >
            {connecting ? 'Launching browser...' : 'Connect in Browser'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
