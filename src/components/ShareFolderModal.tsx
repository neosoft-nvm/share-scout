import React, { useState } from 'react';
import { Modal } from './Modal';
import { pickFolder, configureFolderShare } from '../services/api';

interface ShareFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShareFolderModal: React.FC<ShareFolderModalProps> = ({ isOpen, onClose }) => {
  const [folderPath, setFolderPath] = useState('');
  const [shareName, setShareName] = useState('');
  const [permission, setPermission] = useState<'Read Only' | 'Read & Write'>('Read & Write');
  const [guestAccess, setGuestAccess] = useState(false);
  const [sharing, setSharing] = useState(false);

  const handleBrowse = async () => {
    const picked = await pickFolder();
    if (picked) {
      setFolderPath(picked);
      const name = picked.split(/[\\/]/).filter(Boolean).pop() || 'SharedFolder';
      setShareName(name);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderPath.trim() || !shareName.trim()) return;

    setSharing(true);
    const readOnly = permission === 'Read Only';
    await configureFolderShare(folderPath.trim(), shareName.trim(), readOnly);
    setSharing(false);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Share a Local Folder"
      subtitle="Make a folder on this PC accessible to other devices on your network"
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {/* Folder picker matching mockup */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Folder to Share
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              required
              placeholder="/home/username/Documents or select folder..."
              value={folderPath}
              onChange={(e) => {
                setFolderPath(e.target.value);
                if (!shareName) {
                  const name = e.target.value.split(/[\\/]/).filter(Boolean).pop() || '';
                  setShareName(name);
                }
              }}
              className="flex-1 text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={handleBrowse}
              className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
            >
              Browse...
            </button>
          </div>
        </div>

        {/* Share name matching mockup */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Share Name
          </label>
          <input
            type="text"
            required
            value={shareName}
            onChange={(e) => setShareName(e.target.value)}
            className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Segmented Permission Toggle matching mockup */}
        <div className="pt-1">
          <div className="grid grid-cols-2 rounded-xl border border-slate-200 overflow-hidden p-1 bg-slate-50">
            <button
              type="button"
              onClick={() => setPermission('Read Only')}
              className={`py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                permission === 'Read Only'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              [Read Only]
            </button>
            <button
              type="button"
              onClick={() => setPermission('Read & Write')}
              className={`py-2 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                permission === 'Read & Write'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              [Read & Write]
            </button>
          </div>
        </div>

        {/* Checkbox matching mockup */}
        <label className="flex items-center gap-2 cursor-pointer select-none pt-1">
          <input
            type="checkbox"
            checked={guestAccess}
            onChange={(e) => setGuestAccess(e.target.checked)}
            className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
          />
          <span className="text-xs font-medium text-slate-700">
            Allow Guest Access without password
          </span>
        </label>

        {/* Footer dock matching mockup */}
        <div className="flex justify-center gap-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="py-2.5 px-5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={sharing}
            className="py-2.5 px-6 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs cursor-pointer"
          >
            {sharing ? 'Configuring...' : 'Start Sharing'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
