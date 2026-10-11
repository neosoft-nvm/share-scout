import React, { useState, useEffect } from 'react';
import {
  Laptop,
  Folder,
  RotateCw,
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
  const [autoReconnect] = useState(true);
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
      {/* Header matching mockup */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs mb-6">
        <h1 className="text-xl font-black text-slate-900 tracking-tight mb-3">
          Find Network Folders
        </h1>

        {/* Progress telemetry bar */}
        <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden mb-3">
          <div
            className="bg-indigo-600 h-full transition-all duration-300 rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Telemetry row */}
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-600">
            {scanning
              ? 'Scanning local network (192.168.1.0/24)...'
              : `Scanning local network (192.168.1.0/24)... Found ${devices.length} devices`}
          </p>

          <button
            type="button"
            disabled={scanning}
            onClick={handleStartScan}
            className="flex items-center gap-1.5 py-1.5 px-3.5 rounded-full text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-all cursor-pointer disabled:opacity-50"
          >
            <RotateCw className={`w-3.5 h-3.5 ${scanning ? 'animate-spin' : ''}`} />
            <span>Rescan</span>
          </button>
        </div>
      </div>

      {/* Two-Column Split Workflow */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 flex-1 mb-6">
        {/* Left Column: Discovered Devices */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4">
            Discovered Devices
          </h2>

          <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[380px] pr-1">
            {devices.length === 0 ? (
              <div className="text-center py-12 text-slate-400 text-xs">
                {scanning ? 'Searching for devices on network...' : 'No devices found.'}
              </div>
            ) : (
              devices.map((device) => {
                const isSelected = selectedDevice === device.address;
                const cat = device.category || 'Desktop';
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
                      <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-600">
                        {cat === 'NAS' || cat === 'Server' ? (
                          <Server className="w-4 h-4" />
                        ) : (
                          <Laptop className="w-4 h-4" />
                        )}
                      </div>
                      <span className="text-xs font-bold text-slate-900">
                        {device.address} - {device.name || 'Device'}
                      </span>
                    </div>

                    <span className="px-2.5 py-1 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600">
                      {cat}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Shared Folders */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-xs flex flex-col">
          <h2 className="text-sm font-bold text-slate-900 mb-4">
            {selectedDevice
              ? `Shared Folders on ${devices.find(d => d.address === selectedDevice)?.name || selectedDevice}`
              : 'Shared Folders'}
          </h2>

          <div className="flex-1 overflow-y-auto space-y-2.5 max-h-[380px] pr-1">
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
                const perm = share.permission || 'Guest';
                const permColor =
                  perm === 'Read/Write'
                    ? 'text-emerald-600'
                    : perm === 'Password Protected'
                    ? 'text-amber-600'
                    : 'text-indigo-600';

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
                      <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600">
                        <Folder className="w-4 h-4" />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-900">{share.name}</p>
                        <p className={`text-[11px] font-semibold ${permColor}`}>
                          [{perm}]
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Bottom Action Dock matching mockup */}
      <footer className="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs flex items-center justify-between">
        <button
          type="button"
          onClick={() => setShowAuthModal(true)}
          className="text-xs font-medium text-slate-600 hover:text-indigo-600 cursor-pointer"
        >
          Need credentials? <span className="text-indigo-600 underline font-semibold">Sign In</span>
        </button>

        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={!selectedDevice || !selectedShare}
            onClick={handleConnect}
            className="py-2.5 px-5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 transition-all shadow-xs cursor-pointer disabled:cursor-not-allowed"
          >
            Connect Selected Folder
          </button>
          <button
            type="button"
            onClick={onBack}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              const ip = prompt('Enter manual IP address (e.g. 192.168.1.150):');
              if (ip) handleSelectDevice(ip.trim());
            }}
            className="py-2.5 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
          >
            Manual IP
          </button>
        </div>
      </footer>

      {/* Device Credentials Modal matching mockup */}
      <Modal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        title="Sign In to Device"
        subtitle={selectedDevice ? `Enter credentials for ${selectedDevice}` : 'Enter network device credentials'}
        maxWidth="max-w-md"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setShowAuthModal(false);
            if (selectedDevice) handleSelectDevice(selectedDevice);
          }}
          className="space-y-4 pt-2"
        >
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Username</label>
            <input
              type="text"
              required
              placeholder="e.g. smbuser or Administrator"
              className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Password</label>
            <input
              type="password"
              required
              placeholder="••••••••"
              className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">Domain / Workgroup (Optional)</label>
            <input
              type="text"
              placeholder="WORKGROUP"
              className="w-full text-xs py-2.5 px-3.5 rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none pt-1">
            <input
              type="checkbox"
              defaultChecked
              className="w-4 h-4 rounded text-indigo-600 border-slate-300 focus:ring-indigo-500"
            />
            <span className="text-xs font-medium text-slate-700">
              Remember credentials for this device
            </span>
          </label>

          <div className="flex justify-center gap-3 pt-3">
            <button
              type="submit"
              className="py-2.5 px-6 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs cursor-pointer transition-all"
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => setShowAuthModal(false)}
              className="py-2.5 px-5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 transition-colors cursor-pointer"
            >
              Cancel
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
