/**
 * Layer 4: 出口判定
 * タイプ + 悩みタグ + 許容度 → 出口カテゴリ
 * 具体的な商品はまだ選ばない。
 */

import type {
  ExitRule,
  ExitType,
  TraitScores,
} from '../../types/index.js';

function matchesExitRule(
  rule: ExitRule,
  traitScores: TraitScores,
  worryTags: string[],
  paidTolerance: number,
): boolean {
  const { conditions } = rule;

  if (conditions.traitRanges) {
    for (const [axis, range] of Object.entries(conditions.traitRanges)) {
      const score = traitScores[axis as keyof TraitScores];
      if (range.min !== undefined && score < range.min) return false;
      if (range.max !== undefined && score > range.max) return false;
    }
  }

  if (conditions.requiredTags) {
    const hasRequired = conditions.requiredTags.some((tag) => worryTags.includes(tag));
    if (!hasRequired) return false;
  }

  if (conditions.excludedTags) {
    const hasExcluded = conditions.excludedTags.some((tag) => worryTags.includes(tag));
    if (hasExcluded) return false;
  }

  if (conditions.paidTolerance) {
    if (conditions.paidTolerance.min !== undefined && paidTolerance < conditions.paidTolerance.min) return false;
    if (conditions.paidTolerance.max !== undefined && paidTolerance > conditions.paidTolerance.max) return false;
  }

  return true;
}

export function determineExit(
  traitScores: TraitScores,
  worryTags: string[],
  paidTolerance: number,
  exitRules: ExitRule[],
): ExitType {
  const activeRules = exitRules.filter((r) => r.isActive);

  const matches = activeRules
    .filter((rule) => matchesExitRule(rule, traitScores, worryTags, paidTolerance))
    .sort((a, b) => b.priority - a.priority);

  if (matches.length > 0) return matches[0].exitType;

  // デフォルト: 今は何も買わない
  return 'nothing_now';
}
