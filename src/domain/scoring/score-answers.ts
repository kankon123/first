/**
 * Layer 2: スコアリング
 * 回答 → 特性スコア + 悩みタグ + 有料許容度
 * 商品名を参照しない。
 */

import type {
  TraitAxis,
  TraitScores,
  QuestionMaster,
  DiagnosisSession,
} from '../../types/index.js';

const INITIAL_SCORE = 50; // 各軸の初期値（中央）

const ALL_AXES: TraitAxis[] = [
  'jishu', 'antei', 'shoutensu', 'data', 'jitan', 'reisei',
];

export function createInitialTraitScores(): TraitScores {
  return Object.fromEntries(ALL_AXES.map((axis) => [axis, INITIAL_SCORE])) as TraitScores;
}

export function scoreAnswers(
  answers: Record<string, string>,
  questions: QuestionMaster[],
): Pick<DiagnosisSession, 'traitScores' | 'worryTags' | 'paidTolerance'> {
  const traitScores = createInitialTraitScores();
  const worryTagSet = new Set<string>();
  let paidTolerance = 0;

  for (const question of questions) {
    const selectedOptionId = answers[question.questionId];
    if (!selectedOptionId) continue;

    const option = question.options.find((o) => o.optionId === selectedOptionId);
    if (!option) continue;

    if (option.traitDeltas) {
      for (const [axis, delta] of Object.entries(option.traitDeltas)) {
        traitScores[axis as TraitAxis] += delta;
      }
    }

    if (option.worryTags) {
      option.worryTags.forEach((tag) => worryTagSet.add(tag));
    }

    if (option.paidToleranceDelta) {
      paidTolerance += option.paidToleranceDelta;
    }
  }

  return {
    traitScores,
    worryTags: Array.from(worryTagSet),
    paidTolerance,
  };
}
