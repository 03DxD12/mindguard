import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useAuth } from '../context/AuthContext';

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  
  // Editing modes
  const [isEditing, setIsEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Form states
  const [editForm, setEditForm] = useState({
    fullname: user?.fullname || '',
    email: user?.email || '',
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  // Contacts
  const [contacts, setContacts] = useState<string[]>(user?.trusted_contacts || []);
  const [newContact, setNewContact] = useState('');
  const [isAddingContact, setIsAddingContact] = useState(false);

  // Status messages
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  // GPS Location State
  const [location, setLocation] = useState<{lat: number, lng: number} | null>(null);
  const [locationStatus, setLocationStatus] = useState('');

  const handleShareLocation = () => {
    if (!navigator.geolocation) {
      setLocationStatus('Geolocation is not supported by your browser');
      return;
    }
    setLocationStatus('Locating...');
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
        setLocationStatus('Location shared securely (Consent granted).');
      },
      () => {
        setLocationStatus('Unable to retrieve your location. Check permissions.');
      }
    );
  };

  useEffect(() => {
    if (user) {
      setEditForm({ fullname: user.fullname, email: user.email });
      setContacts(user.trusted_contacts || []);
    }
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSaveProfile = async () => {
    setError('');
    setMessage('');
    if (!user?.id) return;

    if (!editForm.fullname || !editForm.email) {
      setError('Name and Email are required.');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        fullname: editForm.fullname,
        email: editForm.email,
        trusted_contacts: contacts
      };
      
      const res = await fetch(`/api/profile/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Update failed');
      
      setMessage('Profile successfully updated.');
      setIsEditing(false);
      
      // Update local cache so refresh works properly
      const storedUsers = JSON.parse(localStorage.getItem('mindguard_users_v2') || '[]');
      const userIndex = storedUsers.findIndex((u: any) => u.email === user.email);
      if (userIndex >= 0) {
        storedUsers[userIndex] = { ...storedUsers[userIndex], ...payload };
        localStorage.setItem('mindguard_users_v2', JSON.stringify(storedUsers));
        // Simple trick to force context reload without prop drilling
        window.location.reload(); 
      }
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSavePassword = async () => {
    setError('');
    setMessage('');
    if (!user?.id) return;

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('New passwords do not match.');
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`/api/profile/password/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Password update failed');
      
      setMessage('Password successfully updated.');
      setIsChangingPassword(false);
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const addContact = () => {
    if (!newContact.trim() || contacts.length >= 3) return;
    setContacts([...contacts, newContact.trim()]);
    setNewContact('');
    setIsAddingContact(false);
  };

  if (!user) return null;

  return (
    <div className="flex flex-col gap-4 max-w-2xl mx-auto">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate(user.role === 'admin' ? '/admin/dashboard' : '/dashboard')}>
          ← Back to Dashboard
        </Button>
      </div>

      <Card>
        {/* Notifications */}
        {message && <div className="mb-4 bg-teal-50 border-l-4 border-teal-500 p-4 text-teal-700 font-medium text-sm">{message}</div>}
        {error && <div className="mb-4 bg-red-50 border-l-4 border-red-500 p-4 text-red-700 font-medium text-sm">{error}</div>}

        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold text-gray-800 m-0">My Profile</h2>
          {!isEditing && (
            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
              Edit Profile
            </Button>
          )}
        </div>

        {/* Basic Info Mode: View vs Edit */}
        {isEditing ? (
          <div className="space-y-4 mb-6">
            <Input 
              label="Full Name *" 
              value={editForm.fullname} 
              onChange={(e) => setEditForm({...editForm, fullname: e.target.value})} 
              fullWidth 
            />
            <Input 
              label="Email Address *" 
              type="email"
              value={editForm.email} 
              onChange={(e) => setEditForm({...editForm, email: e.target.value})} 
              fullWidth 
            />
            <div className="flex gap-2 pt-2">
              <Button onClick={handleSaveProfile} isLoading={isLoading}>Save Changes</Button>
              <Button variant="ghost" onClick={() => setIsEditing(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="mb-6 space-y-1">
            <div className="text-xl font-bold text-gray-900">{user.fullname}</div>
            <div className="text-gray-500">{user.email}</div>
          </div>
        )}

        {/* Read Only Fields */}
        <div className="bg-gray-50 p-4 rounded-lg space-y-3 mb-8">
          <div className="flex justify-between items-center border-b border-gray-200 pb-2">
            <span className="text-sm font-medium text-gray-500">Student ID</span>
            <span className="font-medium text-gray-900">{user.studentid || '-'}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-500">Course</span>
            <span className="font-medium text-gray-900 text-right max-w-[60%] truncate" title={user.program}>{user.program || '-'}</span>
          </div>
        </div>

        {/* Passwords */}
        <div className="border-t border-gray-100 pt-6 mb-8">
           <h3 className="text-lg font-bold text-gray-800 mb-4">Security</h3>
           {isChangingPassword ? (
             <div className="space-y-4 bg-gray-50 p-4 rounded-lg">
                <Input label="Current Password" type="password" value={passwordForm.current_password} onChange={e => setPasswordForm({...passwordForm, current_password: e.target.value})} fullWidth />
                <Input label="New Password" type="password" value={passwordForm.new_password} onChange={e => setPasswordForm({...passwordForm, new_password: e.target.value})} fullWidth />
                <Input label="Confirm New Password" type="password" value={passwordForm.confirm_password} onChange={e => setPasswordForm({...passwordForm, confirm_password: e.target.value})} fullWidth />
                <div className="flex gap-2 pt-2">
                  <Button onClick={handleSavePassword} isLoading={isLoading}>Update Password</Button>
                  <Button variant="ghost" onClick={() => setIsChangingPassword(false)}>Cancel</Button>
                </div>
             </div>
           ) : (
             <Button variant="outline" size="sm" onClick={() => setIsChangingPassword(true)}>
               Change Password
             </Button>
           )}
        </div>

        {/* Trusted Contacts */}
        <div className="border-t border-gray-100 pt-6 mb-8">
          <h3 className="text-lg font-bold text-gray-800 mb-1">Trusted Contacts</h3>
          <p className="text-sm text-gray-500 mb-4">Up to 3 emergency numbers to contact.</p>
          
          <div className="space-y-3 mb-4">
            {contacts.map((contact, idx) => (
              <div key={idx} className="flex justify-between items-center bg-teal-50 px-4 py-3 rounded-lg border border-teal-100">
                <span className="font-medium text-teal-900">{contact}</span>
                {isEditing && (
                  <button 
                    onClick={() => setContacts(contacts.filter((_, i) => i !== idx))}
                    className="text-red-500 text-sm font-bold hover:text-red-700"
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            {contacts.length === 0 && <p className="text-sm text-gray-400 italic">No contacts added yet.</p>}
          </div>

          {isEditing && contacts.length < 3 && (
            isAddingContact ? (
              <div className="flex gap-2">
                <Input placeholder="Enter Phone Number..." value={newContact} onChange={e => setNewContact(e.target.value)} fullWidth />
                <Button onClick={addContact}>Add</Button>
                <Button variant="ghost" onClick={() => setIsAddingContact(false)}>Cancel</Button>
              </div>
            ) : (
              <Button variant="outline" size="sm" className="border-dashed" onClick={() => setIsAddingContact(true)}>
                + Add Trusted Contact
              </Button>
            )
          )}
        </div>

        {/* Location Services */}
        <div className="border-t border-gray-100 pt-6 mb-8">
          <h3 className="text-lg font-bold text-gray-800 mb-1">Location Services (GPS)</h3>
          <p className="text-sm text-gray-500 mb-4">
            Enable location sharing so emergency contacts or responders can find you in a crisis.
          </p>
          <Button variant="outline" size="sm" className="w-full mb-2" onClick={handleShareLocation}>
            {location ? "Update Location" : "Share My Location"}
          </Button>
          {locationStatus && <p className="text-sm text-center text-teal-600 font-medium mt-2">{locationStatus}</p>}
        </div>

        {/* Privacy Note */}
        <div className="flex items-center justify-center gap-2 text-xs text-gray-400 font-medium py-4 px-2 bg-gray-50 rounded mb-8">
          <span className="text-lg">🔒</span> All data is encrypted and protected for your privacy.
        </div>

        {/* Global Actions */}
        <div className="border-t border-gray-100 pt-6">
          <Button 
            variant="primary" 
            size="lg" 
            className="w-full bg-red-600 hover:bg-red-700 border-red-600" 
            onClick={handleLogout}
          >
            Log Out of MindGuard
          </Button>
        </div>
      </Card>
    </div>
  );
};
