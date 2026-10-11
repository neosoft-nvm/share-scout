import React, { useState } from 'react';
import { Modal } from './Modal';

interface ManualAddressModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddAddress: (name: string, address: string, auto: boolean) => void;
}

export const ManualAddressModal: React.FC<ManualAddressModalProps> = ({
  isOpen,
  onClose,
  onAddAddress,
}) => {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [auto, setAuto] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !address.trim()) return;
    onAddAddress(name.trim(), address.trim(), auto);
    setName('');
    setAddress('');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Connect Manual Address"
      subtitle="Enter an SMB or network file share location directly"
      maxWidth="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-2">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Folder Name
          </label>
          <input
            type="text"
            required
            placeholder="e.g. Office Share"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Network Address
          </label>
          <input
            type="text"
            required
            placeholder="e.g. smb://192.168.1.50/photos or \\server\photos"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500 font-mono"
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none pt-1">
          <input
            type="checkbox"
            checked={auto}
            onChange={(e) => setAuto(e.target.checked)}
            className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
          />
          <span className="text-xs font-medium text-slate-700">
            Reconnect automatically when ShareScout opens
          </span>
        </label>

        <div className="flex justify-center gap-3 pt-3">
          <button
            type="submit"
            className="py-2.5 px-6 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs cursor-pointer transition-all"
          >
            Connect Folder
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
