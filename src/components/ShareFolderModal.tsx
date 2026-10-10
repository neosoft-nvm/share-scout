import React, { useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import { Modal } from './Modal';

interface ShareFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShareFolderModal: React.FC<ShareFolderModalProps> = ({ isOpen, onClose }) => {
  const [folderPath, setFolderPath] = useState('/home/user/Public');
  const [shareName, setShareName] = useState('Public');
  const [readOnly, setReadOnly] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSharing(true);
    setTimeout(() => {
      setSharing(false);
      setDone(true);
    }, 900);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Share a Local Folder"
      subtitle="Allow other computers on your network to access this folder"
      maxWidth="max-w-md"
    >
      {done ? (
        <div className="text-center py-6">
          <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-bold text-slate-900">Folder is ready to share!</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
            Other devices on your Wi-Fi/LAN can now discover and connect to{' '}
            <span className="font-semibold text-slate-700 font-mono">{shareName}</span>.
          </p>
          <button
            type="button"
            onClick={() => {
              setDone(false);
              onClose();
            }}
            className="mt-5 py-2 px-4 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Done
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Folder Path
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                required
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                className="flex-1 text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Network Share Name
            </label>
            <input
              type="text"
              required
              value={shareName}
              onChange={(e) => setShareName(e.target.value)}
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={readOnly}
              onChange={(e) => setReadOnly(e.target.checked)}
              className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
            />
            <span className="text-xs font-medium text-slate-700">
              Read only (prevent other devices from modifying files)
            </span>
          </label>

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
              disabled={sharing}
              className="py-2 px-4 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50"
            >
              {sharing ? 'Configuring sharing...' : 'Start Sharing'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};
