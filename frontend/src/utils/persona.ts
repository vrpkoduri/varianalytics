import { PersonaType, type NarrativeLevel } from '@/types/index';

/**
 * Get the default narrative level for a given persona.
 */
export function getNarrativeLevelForPersona(persona: PersonaType): NarrativeLevel {
  switch (persona) {
    case PersonaType.ANALYST:
      return 'detail';
    case PersonaType.BU_LEADER:
      return 'detail';
    case PersonaType.HR_FINANCE:
      return 'detail';
    case PersonaType.CFO:
      return 'summary';
    case PersonaType.BOARD_VIEWER:
      return 'board';
    default:
      return 'detail';
  }
}

/**
 * Check if a persona can access cross-BU data.
 */
export function canAccessCrossBU(persona: PersonaType): boolean {
  return persona === PersonaType.CFO || persona === PersonaType.BOARD_VIEWER;
}

/**
 * Check if a persona can see a given review status.
 * BU Leaders see REVIEWED/APPROVED only. CFO sees APPROVED only.
 */
export function canSeeReviewStatus(
  persona: PersonaType,
  status: string,
): boolean {
  switch (persona) {
    case PersonaType.CFO:
      return status === 'APPROVED';
    case PersonaType.BU_LEADER:
      return status === 'ANALYST_REVIEWED' || status === 'APPROVED';
    case PersonaType.BOARD_VIEWER:
      return status === 'APPROVED';
    default:
      return true;
  }
}

/**
 * Check if a persona can perform review actions.
 */
export function canReview(persona: PersonaType): boolean {
  return persona === PersonaType.ANALYST;
}

/**
 * Check if a persona can approve variances.
 */
export function canApprove(persona: PersonaType): boolean {
  return persona === PersonaType.BU_LEADER || persona === PersonaType.CFO;
}

/**
 * Get the allowed narrative levels for a persona.
 */
export function getAllowedNarrativeLevels(persona: PersonaType): NarrativeLevel[] {
  switch (persona) {
    case PersonaType.BOARD_VIEWER:
      return ['board', 'summary'];
    case PersonaType.CFO:
      return ['summary', 'oneliner', 'midlevel'];
    case PersonaType.BU_LEADER:
      return ['detail', 'midlevel', 'summary'];
    default:
      return ['detail', 'midlevel', 'summary', 'oneliner'];
  }
}
