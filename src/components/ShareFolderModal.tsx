import React, { useState } from 'react';
import { Modal } from './Modal';
import { pickFolder, configureFolderShare, errorMessage } from '../services/api';

interface ShareFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ShareFolderModal: React.FC<ShareFolderModalProps> = ({ isOpen, onClose }) => {
  const [folderPath, setFolderPath] = useState('');
  const [shareName, setShareName] = useState('');
  const [permission, setPermission] = useState<'Read Only' | 'Read & Write'>('Read Only');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [sharing, setSharing] = useState(false);

  const handleBrowse = async () => {
    let picked: string | null;
    try { picked = await pickFolder(); } catch (err) { setError(errorMessage(err)); return; }
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
    setError(''); setMessage('Complete the administrator prompts in the setup window.');
    try {
      const result = await configureFolderShare(folderPath.trim(), shareName.trim(), readOnly);
      if (result.wizard) setMessage(result.message || 'Complete the Windows sharing wizard.');
      else if (result.ok) setMessage(`Sharing is ready: ${result.address || ''}/${result.name || shareName}`);
      else throw new Error('Sharing did not finish.');
    } catch (err) { setError(errorMessage(err)); setMessage(''); }
    finally { setSharing(false); }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => { if (!sharing) onClose(); }}
      title="Share a Local Folder"
      subtitle="Make a folder on this PC accessible to other devices on your network"
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        {/* Folder picker matching mockup */}
        <div>
          <label htmlFor="share-folder" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Folder to Share
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              required
              id="share-folder" placeholder="/home/username/Documents or select folder..."
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
              onClick={handleBrowse} disabled={sharing}
              className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
            >
              Browse...
            </button>
          </div>
        </div>

        {/* Share name matching mockup */}
        <div>
          <label htmlFor="share-name" className="block text-xs font-semibold text-slate-700 mb-1.5">
            Share Name
          </label>
          <input
            type="text"
            required
            id="share-name" value={shareName}
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

        <p className="text-sm text-slate-600">Password-protected sharing. Sign in from other devices with this computer’s sharing account.</p>
        {error && <p role="alert" className="error-message">{error}</p>}
        {message && <p role="status" className="text-sm text-slate-600">{message}</p>}

        {/* Footer dock matching mockup */}
        <div className="dialog-actions">
          <button
            type="button"
            onClick={onClose} disabled={sharing}
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
