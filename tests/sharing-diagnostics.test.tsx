import React from 'react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
const api=vi.hoisted(()=>({runDiagnostics:vi.fn(),repairSharing:vi.fn(),checkUpdates:vi.fn(),prepareUpdate:vi.fn(),installUpdate:vi.fn(),repairFusePermission:vi.fn(),errorMessage:(e:Error)=>e.message}));
vi.mock('../src/services/api',()=>api);
import {DiagnosticsModal} from '../src/components/DiagnosticsModal';
const initial={windows:false,version:'0.7.2',checks:[],fusePermission:{applicable:true,enabled:false,paths:['/mnt/games']}};
beforeEach(()=>{vi.clearAllMocks();api.runDiagnostics.mockResolvedValue(initial);});
afterEach(cleanup);
it('requires explicit permission before invoking the system-wide repair',async()=>{
 api.repairFusePermission.mockResolvedValue({ok:true,message:'Permission enabled',diagnostics:{...initial,fusePermission:{...initial.fusePermission,enabled:true}}});
 render(<DiagnosticsModal isOpen onClose={vi.fn()}/>);
 const button=await screen.findByRole('button',{name:'Approve & Repair NTFS/FUSE Sharing'});
 expect(button.hasAttribute('disabled')).toBe(true);expect(api.repairFusePermission).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('checkbox',{name:/Allow Samba access/}));fireEvent.click(button);
 await screen.findByText('Permission enabled');
 expect(api.repairFusePermission).toHaveBeenCalledOnce();
 expect(screen.queryByRole('button',{name:'Approve & Repair NTFS/FUSE Sharing'})).toBeNull();
});
it('does not offer the SELinux repair on a system that does not need it',async()=>{
 api.runDiagnostics.mockResolvedValue({...initial,fusePermission:{applicable:false,enabled:true,paths:[]}});
 render(<DiagnosticsModal isOpen onClose={vi.fn()}/>);
 await waitFor(()=>expect(api.runDiagnostics).toHaveBeenCalled());
 expect(screen.queryByRole('button',{name:'Approve & Repair NTFS/FUSE Sharing'})).toBeNull();
});
