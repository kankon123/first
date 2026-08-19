/**
 * 診断パイプライン — 全体オーケストレーション
 *
 * 回答 → 特性スコア → 診断タイプ → 出口 → 商品適合 → 表示生成
 * 診断ロジックと商品を直接ベタ結合しない。
 */

import type {
  QuestionMaster,
  DiagnosisResultMaster,
  ProductMaster,
  FreeContentMaster,
  ComicMaster,
  ExitRule,
  DiagnosisSession,
  DiagnosisDisplay,
  CtaDefinition,
} from '../types/index.js';
import { scoreAnswers } from '../domain/scoring/score-answers.js';
import { determineType } from '../domain/typing/determine-type.js';
import { determineExit } from '../domain/exit/determine-exit.js';
import { matchProducts, matchFreeContent } from '../domain/matching/match-products.js';

export interface MasterData {
  questions: QuestionMaster[];
  results: DiagnosisResultMaster[];
  products: ProductMaster[];
  freeContent: FreeContentMaster[];
  comics: ComicMaster[];
  exitRules: ExitRule[];
}

export interface PipelineInput {
  sessionId: string;
  answers: Record<string, string>;
}

const DEFAULT_CTAS: CtaDefinition[] = [
  { level: 'L1', label: '無料で続きを見る', description: '無料コンテンツを見る' },
  { level: 'L2', label: 'このタイプの攻略法を見る', description: 'タイプ別の考え方' },
  { level: 'L3', label: '自分に合う選択肢を見る', description: '条件に合う候補を確認' },
];

function buildPersonalizedSummary(
  result: DiagnosisResultMaster,
  answers: Record<string, string>,
  questions: QuestionMaster[],
): string {
  const selectedLabels: string[] = [];

  for (const question of questions) {
    const optionId = answers[question.questionId];
    if (!optionId) continue;
    const option = question.options.find((o) => o.optionId === optionId);
    if (option) selectedLabels.push(`「${option.label}」`);
  }

  if (selectedLabels.length === 0) {
    return `あなたは${result.typeName}です。`;
  }

  return [
    'あなたの回答を見ると、',
    selectedLabels.slice(0, 3).join('、'),
    'という傾向があります。',
    `これは${result.typeName}の特徴と一致しています。`,
  ].join('');
}

function buildSolutionConditions(result: DiagnosisResultMaster): string[] {
  return result.whatTheySeek.slice(0, 3);
}

export function runDiagnosisPipeline(
  input: PipelineInput,
  masters: MasterData,
): { session: DiagnosisSession; display: DiagnosisDisplay } {
  const activeQuestions = masters.questions
    .filter((q) => q.isActive)
    .sort((a, b) => a.displayOrder - b.displayOrder);

  // Layer 2: スコアリング
  const { traitScores, worryTags, paidTolerance } = scoreAnswers(
    input.answers,
    activeQuestions,
  );

  // Layer 3: タイプ判定
  const result = determineType(traitScores, worryTags, masters.results);
  if (!result) {
    throw new Error('No matching diagnosis result found');
  }

  // Layer 4: 出口判定
  const exitType = determineExit(traitScores, worryTags, paidTolerance, masters.exitRules);

  // Layer 5: 商品適合
  const matchedProducts = matchProducts(exitType, worryTags, result, masters.products);
  const freeContent = matchFreeContent(result, worryTags, masters.freeContent);

  // 漫画
  const comic = result.comicId
    ? masters.comics.find((c) => c.comicId === result.comicId && c.isActive) ?? null
    : null;

  const session: DiagnosisSession = {
    sessionId: input.sessionId,
    answers: input.answers,
    traitScores,
    worryTags,
    paidTolerance,
    resultType: result.resultId,
    exitType,
    matchedProducts: matchedProducts.map((p) => p.productId),
    comicId: comic?.comicId ?? null,
  };

  const display: DiagnosisDisplay = {
    result,
    personalizedSummary: buildPersonalizedSummary(result, input.answers, activeQuestions),
    solutionConditions: buildSolutionConditions(result),
    exit: {
      type: exitType,
      primaryRecommendations: matchedProducts.slice(0, 2),
      secondaryRecommendations: matchedProducts.slice(2),
      freeContent,
    },
    comic,
    ctas: comic?.ctaDefinitions ?? DEFAULT_CTAS,
  };

  return { session, display };
}
