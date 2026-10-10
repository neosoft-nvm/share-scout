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
      title="Add Network Address"
      subtitle="Connect directly to a known SMB folder address"
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Friendly Name
          </label>
          <input
            type="text"
            required
            placeholder="e.g. Office Share"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1.5">
            Folder Address
          </label>
          <input
            type="text"
            required
            placeholder="e.g. smb://192.168.1.50/photos or \\server\photos"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <label className="flex items-center gap-2 cursor-pointer select-none">
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
            className="py-2 px-4 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Connect & Save
          </button>
        </div>
      </form>
    </Modal>
  );
};
