import { useContext } from 'react';
import { SessionContext, type SessionContextValue } from './SessionProvider';

/** Access the session context. Throws if used outside the provider. */
export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return value;
}
