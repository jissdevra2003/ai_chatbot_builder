import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [organization, setOrganization] = useState(null);
  const [role, setRole] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const fetchMe = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setIsLoading(false);
        return;
      }

      const response = await authAPI.getMe();
      const data = response.data;
      
      setUser(data.user);
      setOrganization(data.active_organization);
      setRole(data.role);
      setIsAuthenticated(true);
    } catch (error) {
      // Token invalid or expired
      localStorage.removeItem('access_token');
      setUser(null);
      setOrganization(null);
      setRole(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  const login = async (email, password) => {
    const response = await authAPI.login({ email, password });
    const { access_token } = response.data;
    localStorage.setItem('access_token', access_token);
    await fetchMe();
    return response.data;
  };

  const signup = async (full_name, email, password) => {
    const response = await authAPI.signup({ full_name, email, password });
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    setUser(null);
    setOrganization(null);
    setRole(null);
    setIsAuthenticated(false);
  };

  const value = {
    user,
    organization,
    role,
    isLoading,
    isAuthenticated,
    login,
    signup,
    logout,
    refreshUser: fetchMe,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
