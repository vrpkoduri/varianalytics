/**
 * Hook to extract persona and BU scope for API calls.
 *
 * All data-fetching hooks should use this to include persona
 * in API requests so the backend can apply RBAC filtering.
 */
import { useUser } from '@/context/UserContext'

export function usePersonaParams() {
  const { persona, user } = useUser()
  return {
    persona,
    buScope: user?.buScope ?? ['ALL'],
  }
}
