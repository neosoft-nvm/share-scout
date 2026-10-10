import React, { useState, useEffect } from 'react';
import {
  Laptop,
  Folder,
  ArrowLeft,
  KeyRound,
  RotateCw,
  Check,
  Server,
} from 'lucide-react';
import { DiscoveredDevice, DiscoveredShare } from '../types';
import { scanLocalNetwork, listDeviceShares } from '../services/api';
import { Modal } from '../components/Modal';

interface DiscoveryProps {
  onBack: () => void;
  onConnectShare: (deviceAddress: string, shareName: string, autoReconnect: boolean) => void;
}

export const Discovery: React.FC<DiscoveryProps> = ({ onBack, onConnectShare }) => {
  const [scanning, setScanning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [devices, setDevices] = useState<DiscoveredDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [shares, setShares] = useState<DiscoveredShare[]>([]);
  const [selectedShare, setSelectedShare] = useState<string | null>(null);
  const [loadingShares, setLoadingShares] = useState(false);
  const [autoReconnect, setAutoReconnect] = useState(true);
  const [manualIp, setManualIp] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Auto scan on mount
  useEffect(() => {
    handleStartScan();
  }, []);

  const handleStartScan = async () => {
    setScanning(true);
    setProgress(20);
    const progressTimer = setInterval(() => {
      setProgress((p) => (p >= 90 ? p : p + 15));
    }, 200);

    try {
      const results = await scanLocalNetwork();
      setDevices(results);
      setProgress(100);
      if (results.length > 0 && !selectedDevice) {
        handleSelectDevice(results[0].address);
      }
    } finally {
      clearInterval(progressTimer);
      setScanning(false);
    }
  };

  const handleSelectDevice = async (address: string) => {
    setSelectedDevice(address);
    setSelectedShare(null);
    setLoadingShares(true);
    try {
      const shareResults = await listDeviceShares(address);
      setShares(shareResults);
      if (shareResults.length > 0) {
        setSelectedShare(shareResults[0].name);
      }
    } finally {
      setLoadingShares(false);
    }
  };

  const handleConnect = () => {
    if (!selectedDevice || !selectedShare) return;
    onConnectShare(selectedDevice, selectedShare, autoReconnect);
    onBack();
  };

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 p-6 md:p-8 max-w-6xl mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-200/60 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className="text-xl font-black text-slate-900 tracking-tight">
              Network Folder Discovery
            </h1>
            <p className="text-xs text-slate-500">
              {scanning
                ? 'Scanning local network (192.168.1.0/24)...'
                : `Scan complete · Found ${devices.length} devices`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={scanning}
            onClick={handleStartScan}
            className="flex items-center gap-2 py-2 px-3.5 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs"
          >
            <RotateCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            <span>{scanning ? 'Scanning...' : 'Rescan'}</span>
          </button>
        </div>
      </header>

      {/* Telemetry Progress Bar */}
      <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mb-6">
        <div
          className="bg-indigo-600 h-full transition-all duration-300 rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Two-Column Split Workflow */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 mb-8">
        {/* Left Column: Discovered Devices */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              Discovered Devices
            </h2>
            <span className="text-xs text-slate-400 font-medium">{devices.length} total</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 max-h-[360px] pr-1">
            {devices.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                {scanning ? 'Searching for devices on network...' : 'No devices found.'}
              </div>
            ) : (
              devices.map((device) => {
                const isSelected = selectedDevice === device.address;
                return (
                  <div
                    key={device.address}
                    onClick={() => handleSelectDevice(device.address)}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 border-indigo-400 ring-1 ring-indigo-400'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                          isSelected ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {device.category === 'NAS' || device.category === 'Server' ? (
                          <Server className="w-4 h-4" />
                        ) : (
                          <Laptop className="w-4 h-4" />
                        )}
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">{device.address}</p>
                        <p className="text-[11px] text-slate-500">{device.name || 'Local Device'}</p>
                      </div>
                    </div>
                    {isSelected && (
                      <span className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center">
                        <Check className="w-3.5 h-3.5" />
                      </span>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Direct IP input */}
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center gap-2">
            <input
              type="text"
              placeholder="Or enter device IP..."
              value={manualIp}
              onChange={(e) => setManualIp(e.target.value)}
              className="flex-1 text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              disabled={!manualIp.trim()}
              onClick={() => handleSelectDevice(manualIp.trim())}
              className="py-2 px-3 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-50"
            >
              Browse
            </button>
          </div>
        </div>

        {/* Right Column: Shared Folders */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {selectedDevice ? `Shared Folders on ${selectedDevice}` : 'Shared Folders'}
            </h2>
            <button
              type="button"
              onClick={() => setShowAuthModal(true)}
              className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              <KeyRound className="w-3 h-3" />
              <span>Need credentials?</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 max-h-[360px] pr-1">
            {loadingShares ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                Querying accessible shares...
              </div>
            ) : shares.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                {selectedDevice
                  ? 'No visible shares or authentication required.'
                  : 'Select a device from the left to view shares.'}
              </div>
            ) : (
              shares.map((share) => {
                const isSelected = selectedShare === share.name;
                return (
                  <div
                    key={share.name}
                    onClick={() => setSelectedShare(share.name)}
                    className={`flex items-center justify-between p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-50/70 border-indigo-400 ring-1 ring-indigo-400'
                        : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-9 h-9 rounded-lg flex items-center justify-center ${
                          isSelected ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        <Folder className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">{share.name}</p>
                        <p className="text-[11px] text-slate-500">{share.comment || 'Shared directory'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          share.permission === 'Read/Write'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-slate-100 text-slate-600 border border-slate-200'
                        }`}
                      >
                        {share.permission || 'Guest'}
                      </span>
                      {isSelected && (
                        <span className="w-6 h-6 rounded-full bg-indigo-600 text-white flex items-center justify-center">
                          <Check className="w-3.5 h-3.5" />
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Bottom Action Dock */}
      <footer className="sticky bottom-0 bg-slate-50/90 backdrop-blur-md pt-3 pb-1 border-t border-slate-200 flex items-center justify-between">
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={autoReconnect}
            onChange={(e) => setAutoReconnect(e.target.checked)}
            className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
          />
          <span className="text-xs font-medium text-slate-700">
            Reconnect automatically when ShareScout opens
          </span>
        </label>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!selectedDevice || !selectedShare}
            onClick={handleConnect}
            className="py-2.5 px-5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs"
          >
            Connect Selected Folder
          </button>
        </div>
      </footer>

      {/* Device Credentials Modal */}
      <Modal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        title="Sign In to Device"
        subtitle={selectedDevice ? `Enter credentials for ${selectedDevice}` : 'Enter device credentials'}
        maxWidth="max-w-sm"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setShowAuthModal(false);
            if (selectedDevice) handleSelectDevice(selectedDevice);
          }}
          className="space-y-3"
        >
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Username</label>
            <input
              type="text"
              required
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Password</label>
            <input
              type="password"
              required
              className="w-full text-xs py-2 px-3 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowAuthModal(false)}
              className="py-1.5 px-3 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="py-1.5 px-3.5 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Sign In
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
