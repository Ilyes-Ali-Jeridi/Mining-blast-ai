import { useState, useEffect } from 'react';

// Mock user interface for now
interface User {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: 'engineer' | 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  is_verified: boolean;
  can_sign_off: boolean;
}

// Mock auth hook - in a real implementation this would connect to your auth service
export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Mock authentication check
    // In a real implementation, this would check for stored tokens, validate them, etc.
    const mockUser: User = {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      full_name: 'System Administrator',
      role: 'admin',
      is_active: true,
      is_verified: true,
      can_sign_off: false
    };

    // Simulate async auth check
    setTimeout(() => {
      setUser(mockUser);
      setLoading(false);
    }, 100);
  }, []);

  const login = async (username: string, password: string) => {
    // Mock login implementation
    setLoading(true);
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const mockUser: User = {
      id: 1,
      username,
      email: `${username}@example.com`,
      full_name: 'System Administrator',
      role: 'admin',
      is_active: true,
      is_verified: true,
      can_sign_off: false
    };
    
    setUser(mockUser);
    setLoading(false);
    
    return mockUser;
  };

  const logout = async () => {
    setUser(null);
  };

  return {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isEngineer: user?.role === 'engineer'
  };
};