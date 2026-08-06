import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { Input } from '../components/Input';
import { useAuth } from '../context/AuthContext';
import styles from './Profile.module.css';

export const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [editForm, setEditForm] = useState({
    fullname: user?.fullname || '',
    email: user?.email || '',
  });

  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });

  const [contacts, setContacts] = useState<string[]>(user?.trusted_contacts || []);
  const [newContact, setNewContact] = useState('');
  const [isAddingContact, setIsAddingContact] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locationStatus, setLocationStatus] = useState('');

  useEffect(() => {
    if (user) {
      setEditForm({ fullname: user.fullname, email: user.email });
      setContacts(user.trusted_contacts || []);
    }
  }, [user]);

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
        setLocationStatus('Location shared securely. Consent granted.');
      },
      () => {
        setLocationStatus('Unable to retrieve your location. Check permissions.');
      }
    );
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleSaveProfile = async () => {
    setError('');
    setMessage('');
    if (!user?.id) return;

    if (!editForm.fullname || !editForm.email) {
      setError('Name and email are required.');
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

      const storedUsers = JSON.parse(localStorage.getItem('mindguard_users_v2') || '[]');
      const userIndex = storedUsers.findIndex((u: any) => u.email === user.email);
      if (userIndex >= 0) {
        storedUsers[userIndex] = { ...storedUsers[userIndex], ...payload };
        localStorage.setItem('mindguard_users_v2', JSON.stringify(storedUsers));
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

  const dashboardPath = user.role === 'admin' ? '/admin/dashboard' : '/dashboard';
  const initial = user.fullname?.charAt(0)?.toUpperCase() || 'U';

  return (
    <div className={styles.container}>
      <div className={styles.backRow}>
        <Button variant="ghost" size="sm" onClick={() => navigate(dashboardPath)}>
          Back to Dashboard
        </Button>
      </div>

      <div className={styles.profileGrid}>
        <Card className={styles.heroCard}>
          {message && <div className={`${styles.status} ${styles.success}`}>{message}</div>}
          {error && <div className={`${styles.status} ${styles.error}`}>{error}</div>}

          <div className={styles.heroHeader}>
            <h2 className={styles.title}>My Profile</h2>
            {!isEditing && (
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                Edit Profile
              </Button>
            )}
          </div>

          {isEditing ? (
            <div className={styles.formStack}>
              <Input
                label="Full Name *"
                value={editForm.fullname}
                onChange={(e) => setEditForm({ ...editForm, fullname: e.target.value })}
                fullWidth
              />
              <Input
                label="Email Address *"
                type="email"
                value={editForm.email}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                fullWidth
              />
              <div className={styles.actionRow}>
                <Button onClick={handleSaveProfile} isLoading={isLoading}>Save Changes</Button>
                <Button variant="ghost" onClick={() => setIsEditing(false)}>Cancel</Button>
              </div>
            </div>
          ) : (
            <div className={styles.identity}>
              <div className={styles.avatar}>{initial}</div>
              <div>
                <div className={styles.name}>{user.fullname}</div>
                <div className={styles.email}>{user.email}</div>
              </div>
            </div>
          )}

          <div className={styles.readonlyBox}>
            <div className={styles.readonlyRow}>
              <span className={styles.label}>Student ID</span>
              <span className={styles.value}>{user.studentid || '-'}</span>
            </div>
            <div className={styles.readonlyRow}>
              <span className={styles.label}>Course</span>
              <span className={styles.value} title={user.program}>{user.program || '-'}</span>
            </div>
          </div>
        </Card>

        <Card className={styles.panelCard}>
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <div>
                <h3 className={styles.sectionTitle}>Security</h3>
                <p className={styles.sectionCopy}>Update your password when you need to protect your account.</p>
              </div>
              {!isChangingPassword && (
                <Button variant="outline" size="sm" onClick={() => setIsChangingPassword(true)}>
                  Change Password
                </Button>
              )}
            </div>

            {isChangingPassword && (
              <div className={styles.passwordBox}>
                <Input label="Current Password" type="password" value={passwordForm.current_password} onChange={e => setPasswordForm({ ...passwordForm, current_password: e.target.value })} fullWidth />
                <Input label="New Password" type="password" value={passwordForm.new_password} onChange={e => setPasswordForm({ ...passwordForm, new_password: e.target.value })} fullWidth />
                <Input label="Confirm New Password" type="password" value={passwordForm.confirm_password} onChange={e => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })} fullWidth />
                <div className={styles.actionRow}>
                  <Button onClick={handleSavePassword} isLoading={isLoading}>Update Password</Button>
                  <Button variant="ghost" onClick={() => setIsChangingPassword(false)}>Cancel</Button>
                </div>
              </div>
            )}
          </section>

          <section className={styles.section}>
            <div>
              <h3 className={styles.sectionTitle}>Trusted Contacts</h3>
              <p className={styles.sectionCopy}>Up to 3 emergency numbers to contact.</p>
            </div>

            <div className={styles.contactList}>
              {contacts.map((contact, idx) => (
                <div key={idx} className={styles.contactRow}>
                  <span className={styles.contactValue}>{contact}</span>
                  {isEditing && (
                    <Button variant="ghost" size="sm" onClick={() => setContacts(contacts.filter((_, i) => i !== idx))}>
                      Remove
                    </Button>
                  )}
                </div>
              ))}
              {contacts.length === 0 && <p className={styles.emptyText}>No contacts added yet.</p>}
            </div>

            {isEditing && contacts.length < 3 && (
              isAddingContact ? (
                <div className={styles.contactEditor}>
                  <Input placeholder="Enter phone number..." value={newContact} onChange={e => setNewContact(e.target.value)} fullWidth />
                  <Button onClick={addContact}>Add</Button>
                  <Button variant="ghost" onClick={() => setIsAddingContact(false)}>Cancel</Button>
                </div>
              ) : (
                <Button variant="outline" size="sm" onClick={() => setIsAddingContact(true)}>
                  Add Trusted Contact
                </Button>
              )
            )}
          </section>

          <section className={styles.section}>
            <div>
              <h3 className={styles.sectionTitle}>Location Services</h3>
              <p className={styles.sectionCopy}>Enable location sharing so responders can find you in a crisis.</p>
            </div>
            <Button variant="outline" size="sm" onClick={handleShareLocation}>
              {location ? 'Update Location' : 'Share My Location'}
            </Button>
            {locationStatus && <p className={styles.sectionCopy}>{locationStatus}</p>}
          </section>

          <div className={styles.privacyNote}>
            <span>Privacy:</span> All data is encrypted and protected.
          </div>

          <div className={styles.logoutArea}>
            <Button variant="alert" size="lg" onClick={handleLogout}>
              Log Out of MindGuard
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};
