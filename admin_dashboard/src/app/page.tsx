'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Users, Activity, FileText, Database, Settings, LogOut } from 'lucide-react';

interface UserItem {
  id: string;
  email: string;
  roles: string[];
  status: string;
  createdAt: string;
}

interface AuditLog {
  actorId: string;
  action: string;
  resourceType: string;
  resourceId: string;
  createdAt: string;
}

export default function AdminDashboard() {
  const [users, setUsers] = useState<UserItem[]>([
    { id: '1', email: 'john.doe@example.com', roles: ['User'], status: 'active', createdAt: '2026-06-25' },
    { id: '2', email: 'sarah.smith@example.com', roles: ['User'], status: 'active', createdAt: '2026-06-28' },
    { id: '3', email: 'pranav.ns@example.com', roles: ['Admin'], status: 'active', createdAt: '2026-06-01' },
  ]);

  const [audits, setAudits] = useState<AuditLog[]>([
    { actorId: 'usr-123', action: 'report_upload', resourceType: 'health_report', resourceId: 'rep-456', createdAt: '2026-06-30 14:12' },
    { actorId: 'usr-456', action: 'goal_create', resourceType: 'goal', resourceId: 'goal-789', createdAt: '2026-06-30 14:02' },
    { actorId: 'usr-123', action: 'user_register', resourceType: 'user', resourceId: 'usr-123', createdAt: '2026-06-30 13:50' },
  ]);

  const [ocrStatus, setOcrStatus] = useState("Idle");

  // Attempt to fetch operational logs from local FastAPI instance if online
  useEffect(() => {
    // 1. Fetch Users List
    fetch('http://localhost:8000/api/v1/admin/users', {
      headers: { 'Authorization': 'Bearer mock_admin_token' }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setUsers(data.map((u: any) => ({
            id: u.firebaseUid || u._id || 'unknown',
            email: u.email,
            roles: u.roles || ['User'],
            status: u.status || 'active',
            createdAt: u.createdAt || 'Just Now'
          })));
        }
      })
      .catch(() => console.log("FastAPI backend offline or users fetch failed."));

    // 2. Fetch Security Audit Stream
    fetch('http://localhost:8000/api/v1/admin/audit-logs', {
      headers: { 'Authorization': 'Bearer mock_admin_token' }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setAudits(data.map((a: any) => ({
            actorId: a.actorId || 'system',
            action: a.action || 'event',
            resourceType: a.resourceType || 'unknown',
            resourceId: a.resourceId || 'unknown',
            createdAt: a.createdAt ? new Date(a.createdAt).toLocaleString() : 'Just Now'
          })));
          setOcrStatus("Active");
        }
      })
      .catch(() => console.log("FastAPI backend offline or audit logs fetch failed."));
  }, []);

  return (
    <div className="dashboard-container">
      {/* Sidebar navigation */}
      <aside className="sidebar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Shield color="#4ead73" size={28} />
          <h2 style={{ fontSize: '1.25rem', letterSpacing: '0.05em' }}>BLUMETARA</h2>
        </div>
        
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '2rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#4ead73', cursor: 'pointer' }}>
            <Activity size={20} />
            <span>Overview</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#a0a5a0', cursor: 'pointer' }}>
            <Users size={20} />
            <span>Users Directory</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#a0a5a0', cursor: 'pointer' }}>
            <FileText size={20} />
            <span>Reports Queue</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#a0a5a0', cursor: 'pointer' }}>
            <Database size={20} />
            <span>RAG Vector Indices</span>
          </div>
        </nav>

        <div style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#cf6679', cursor: 'pointer' }}>
          <LogOut size={20} />
          <span>Exit Session</span>
        </div>
      </aside>

      {/* Main Stats panel */}
      <main className="main-content">
        <header style={{ marginBottom: '2.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 'bold' }}>Admin Console</h1>
            <p style={{ color: '#a0a5a0', marginTop: '0.5rem' }}>Operational monitoring panel for Blumetara AI.</p>
          </div>
          <button onClick={() => alert("Simulating database backup...")}>Trigger System Backup</button>
        </header>

        {/* Stats Grid */}
        <section className="grid">
          <div className="card">
            <h3>Registered Profiles</h3>
            <div className="value">{users.length}</div>
          </div>
          <div className="card">
            <h3>Security Audit Logs</h3>
            <div className="value">{audits.length}</div>
          </div>
          <div className="card">
            <h3>Active Accounts</h3>
            <div className="value">{users.filter(u => u.status === 'active').length}</div>
          </div>
          <div className="card">
            <h3>OCR Pipeline State</h3>
            <div className="value" style={{ color: '#4ead73' }}>{ocrStatus}</div>
          </div>
        </section>

        {/* Tables section */}
        <section style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
          {/* User Management */}
          <div className="card">
            <h3 style={{ marginBottom: '1rem', color: '#f4f6f4' }}>Active Accounts Directory</h3>
            <table>
              <thead>
                <tr>
                  <th>User ID</th>
                  <th>Email</th>
                  <th>Roles</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td style={{ fontSize: '0.875rem', fontFamily: 'monospace' }}>{user.id.substring(0, 8)}...</td>
                    <td>{user.email}</td>
                    <td>{user.roles.join(', ')}</td>
                    <td>
                      <span className="status-badge status-completed">
                        {user.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Audit Logs */}
          <div className="card">
            <h3 style={{ marginBottom: '1rem', color: '#f4f6f4' }}>Security Audit Stream</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {audits.map((log, idx) => (
                <div key={idx} style={{ borderBottom: '1px solid rgba(78, 173, 115, 0.1)', paddingBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#4ead73' }}>
                    {log.action.toUpperCase().replaceAll('_', ' ')}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#a0a5a0', marginTop: '0.25rem' }}>
                    Actor: {log.actorId} • {log.createdAt}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
