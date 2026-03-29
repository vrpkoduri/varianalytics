import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from 'react';
import { PersonaType, type User } from '@/types/index';

interface UserContextValue {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

// Default mock user for development
const DEFAULT_USER: User = {
  id: 'dev-user-1',
  name: 'Dev Analyst',
  email: 'analyst@variance-agent.dev',
  persona: PersonaType.ANALYST,
  buScope: ['ALL'],
};

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEFAULT_USER);
  const [isLoading] = useState(false);

  return (
    <UserContext.Provider value={{ user, isLoading, setUser }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
