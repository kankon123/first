/**
 * 競馬診断ファネル — 共通型定義
 *
 * 診断ロジックと商品を直接ベタ結合しない設計。
 * すべての型はマスターデータのスキーマとして機能する。
 */

// ─── 特性軸 ───────────────────────────────────────────

export type TraitAxis =
  | 'jishu'        // 自力 ←→ 他力
  | 'antei'        // 安定 ←→ 高配当
  | 'shoutensu'    // 少点数 ←→ 広く構える
  | 'data'         // データ ←→ 直感
  | 'jitan'        // 短時間 ←→ 研究型
  | 'reisei';      // 冷静 ←→ 感情影響型

export type TraitScores = Record<TraitAxis, number>;

// ─── 出口タイプ ───────────────────────────────────────

export type ExitType =
  | 'free_only'          // 無料コンテンツで十分
  | 'free_affiliate'     // 無料登録型アフィリエイト
  | 'paid_affiliate'     // 有料アフィリエイト
  | 'own_product'        // 自社商品
  | 'nothing_now'        // 今は何も買わない
  | 'future_consider';   // 将来的に検討

// ─── CTA段階 ──────────────────────────────────────────

export type CtaLevel = 'L1' | 'L2' | 'L3' | 'L4' | 'L5';

export interface CtaDefinition {
  level: CtaLevel;
  label: string;
  description: string;
  requiresUserPull?: boolean; // Pull型: ユーザーが明示的に深掘りを選んだ場合のみ
}

// ─── 商品マスター ─────────────────────────────────────

export type ProductCategory =
  | 'completely_free'
  | 'free_registration'
  | 'paid_service'
  | 'own_product'
  | 'tool'
  | 'education';

export type BetType =
  | 'umaren'
  | 'wide'
  | 'tansho_fukusho'
  | 'sanrenpuku'
  | 'sanrentan'
  | 'data'
  | 'general';

export interface ProductMaster {
  productId: string;
  name: string;
  category: ProductCategory;
  price: number | null;           // null = 無料
  hasAffiliate: boolean;
  asp: string | null;             // A8.net, レジまぐ 等
  conversionCondition: string | null;
  conversionReward: number | null;
  suitableFor: string[];
  notSuitableFor: string[];
  betTypes: BetType[];
  traits: Partial<TraitScores>;  // 商品が向いている特性方向
  timeSavingLevel: number;        // 0-100
  requiredKnowledge: 'beginner' | 'intermediate' | 'advanced';
  isSubscription: boolean;
  merits: string[];
  demerits: string[];
  affiliateUrl: string | null;
  trackingUrl: string | null;
  prDisclosure: string;           // PR表示文言
  lastVerifiedAt: string;         // ISO 8601
  isActive: boolean;
  /** 適合タグ: 出口判定・商品マッチングで使用 */
  fitTags: string[];
  /** 優先度（tie-breaker用、収益要素） */
  revenuePriority: number;        // 0-100, 低いほど収益優先度低
}

// ─── 診断質問マスター ─────────────────────────────────

export interface QuestionOption {
  optionId: string;
  label: string;
  /** 各特性軸への加算値 */
  traitDeltas: Partial<TraitScores>;
  /** 内部スコア */
  paidToleranceDelta?: number;     // 有料許容度
  worryTags?: string[];            // 悩みタグ
}

export interface QuestionMaster {
  questionId: string;
  text: string;
  options: QuestionOption[];
  /** 表向きの診断意図 */
  surfaceIntent: string;
  /** 内部的なマーケティング意図 */
  internalIntent: string;
  /** 表示順 */
  displayOrder: number;
  /** 漫画分岐への影響タグ */
  comicBranchTags?: string[];
  isActive: boolean;
}

// ─── 診断結果マスター ─────────────────────────────────

export interface DiagnosisResultMaster {
  resultId: string;
  typeName: string;               // 例: 「自力予想×少点数セカンドオピニオン型」
  catchCopy: string;
  characteristics: string[];
  strengths: string[];
  weaknesses: string[];
  commonFailures: string[];
  whatTheySeek: string[];
  recommendedApproach: string[];
  /** 出口別おすすめ（productId / contentId の参照） */
  recommendedFreeContent: string[];
  recommendedFreeAffiliate: string[];
  recommendedPaidAffiliate: string[];
  /** 紹介しない条件 */
  doNotRecommendWhen: string[];
  comicId: string | null;
  ctaDefinitions: CtaDefinition[];
  lineScenarioId: string | null;
  /** タイプ判定条件（特性スコアの閾値） */
  typeConditions: Partial<Record<TraitAxis, { min?: number; max?: number }>>;
  requiredWorryTags?: string[];
  isActive: boolean;
}

// ─── 漫画マスター ─────────────────────────────────────

export interface ComicPanel {
  panelId: string;
  order: number;
  narration?: string;
  dialogue?: { speaker: string; text: string }[];
  imagePath?: string;
}

export interface ComicMaster {
  comicId: string;
  title: string;
  /** 対象タイプ / 悩みタグ（商品別ではなく悩み別） */
  targetTypes: string[];
  targetWorryTags: string[];
  protagonistWorry: string;
  failure: string;
  cause: string;
  realization: string;
  solutionConditions: string[];
  showProduct: boolean;           // 漫画内で商品を出すか
  panels: ComicPanel[];
  ctaDefinitions: CtaDefinition[];
  nextPageOptions: {
    label: string;
    targetExit?: ExitType;
    targetContentId?: string;
  }[];
  isActive: boolean;
}

// ─── 出口判定ルール ───────────────────────────────────

export interface ExitRule {
  ruleId: string;
  exitType: ExitType;
  conditions: {
    traitRanges?: Partial<Record<TraitAxis, { min?: number; max?: number }>>;
    requiredTags?: string[];
    excludedTags?: string[];
    paidTolerance?: { min?: number; max?: number };
  };
  priority: number;
  isActive: boolean;
}

// ─── 無料コンテンツマスター ───────────────────────────

export interface FreeContentMaster {
  contentId: string;
  title: string;
  type: 'youtube' | 'pdf' | 'checksheet' | 'spreadsheet' | 'article';
  url: string;
  description: string;
  targetTypes: string[];
  targetWorryTags: string[];
  isActive: boolean;
}

// ─── 行動ログ ─────────────────────────────────────────

export interface ActionLog {
  sessionId: string;
  timestamp: string;
  event:
    | 'youtube_referral'
    | 'line_entry'
    | 'diagnosis_start'
    | 'question_answer'
    | 'diagnosis_complete'
    | 'comic_view'
    | 'comic_dropoff'
    | 'cta_click'
    | 'product_click'
    | 'asp_transition'
    | 'conversion';
  metadata: Record<string, unknown>;
}

// ─── 診断セッション（実行時） ─────────────────────────

export interface DiagnosisSession {
  sessionId: string;
  answers: Record<string, string>; // questionId → optionId
  traitScores: TraitScores;
  worryTags: string[];
  paidTolerance: number;
  resultType: string | null;       // resultId
  exitType: ExitType | null;
  matchedProducts: string[];       // productId[]
  comicId: string | null;
}

// ─── 表示用出力 ───────────────────────────────────────

export interface DiagnosisDisplay {
  result: DiagnosisResultMaster;
  personalizedSummary: string;    // 本人の回答を引用した説明
  solutionConditions: string[];     // 「あなたに必要な3条件」
  exit: {
    type: ExitType;
    primaryRecommendations: ProductMaster[];
    secondaryRecommendations: (ProductMaster | FreeContentMaster)[];
    freeContent: FreeContentMaster[];
  };
  comic: ComicMaster | null;
  ctas: CtaDefinition[];
}
