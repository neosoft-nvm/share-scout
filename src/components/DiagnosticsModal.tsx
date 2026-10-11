import React from 'react';
import { Modal } from './Modal';
import { CheckCircle2, AlertCircle } from 'lucide-react';

interface DiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({ isOpen, onClose }) => {
  const diagnosticItems = [
    { name: 'Samba Client (smbclient)', status: 'OK', desc: 'Installed & functional', ok: true },
    { name: 'GIO VFS / GVfs Tools', status: 'OK', desc: 'Installed & functional', ok: true },
    { name: 'Rclone Cloud Engine', status: 'OK', desc: 'Ready for Google & OneDrive', ok: true },
    { name: 'FUSE Filesystem Support', status: 'OK', desc: 'Kernel driver active', ok: true },
    { name: 'Local Network Interface', status: 'Active', desc: 'IPv4 192.168.1.0/24 detected', ok: true },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Sharing Diagnostics"
      subtitle="Verify system dependencies and network sharing components"
      maxWidth="max-w-lg"
    >
      <div className="space-y-4 pt-2">
        <div className="rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden bg-slate-50/50">
          {diagnosticItems.map((item, idx) => (
            <div key={idx} className="p-3.5 flex items-center justify-between bg-white">
              <div className="flex items-center gap-3">
                {item.ok ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-amber-500 shrink-0" />
                )}
                <div>
                  <p className="text-xs font-bold text-slate-900">{item.name}</p>
                  <p className="text-[11px] text-slate-500">{item.desc}</p>
                </div>
              </div>
              <span className="py-1 px-2.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                {item.status}
              </span>
            </div>
          ))}
        </div>

        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={onClose}
            className="py-2.5 px-6 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs cursor-pointer transition-all"
          >
            Close Diagnostics
          </button>
        </div>
      </div>
    </Modal>
  );
};
