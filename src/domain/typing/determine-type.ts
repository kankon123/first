/**
 * Layer 3: タイプ判定
 * 特性スコア + 悩みタグ → 診断タイプ
 * 商品とは独立。
 */

import type {
  TraitAxis,
  DiagnosisResultMaster,
  TraitScores,
} from '../../types/index.js';

function matchesTraitConditions(
  scores: TraitScores,
  conditions: Partial<Record<TraitAxis, { min?: number; max?: number }>>,
): boolean {
  for (const [axis, range] of Object.entries(conditions)) {
    const score = scores[axis as TraitAxis];
    if (range.min !== undefined && score < range.min) return false;
    if (range.max !== undefined && score > range.max) return false;
  }
  return true;
}

function matchesWorryTags(
  userTags: string[],
  requiredTags?: string[],
): boolean {
  if (!requiredTags || requiredTags.length === 0) return true;
  return requiredTags.some((tag) => userTags.includes(tag));
}

export function determineType(
  traitScores: TraitScores,
  worryTags: string[],
  results: DiagnosisResultMaster[],
): DiagnosisResultMaster | null {
  const activeResults = results.filter((r) => r.isActive);

  // 条件に最も合致するタイプを選択（requiredWorryTags + typeConditions）
  const matches = activeResults
    .filter((result) => {
      const traitMatch = matchesTraitConditions(traitScores, result.typeConditions);
      const tagMatch = matchesWorryTags(worryTags, result.requiredWorryTags);
      return traitMatch && tagMatch;
    })
    .sort((a, b) => {
      // requiredWorryTags が多いほど具体的 → 優先
      const aTags = a.requiredWorryTags?.length ?? 0;
      const bTags = b.requiredWorryTags?.length ?? 0;
      return bTags - aTags;
    });

  if (matches.length > 0) return matches[0];

  // フォールバック: 条件なしのデフォルトタイプ（R004: 今は様子見型）
  return activeResults.find((r) => r.resultId === 'R004') ?? null;
}
