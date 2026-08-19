/**
 * Layer 5: 商品適合
 * 適合条件 → 商品マスター検索
 * 適合度 × 優先度（ユーザー適合 > 信頼 > 継続 > 収益）
 */

import type {
  ProductMaster,
  FreeContentMaster,
  ExitType,
  DiagnosisResultMaster,
} from '../../types/index.js';

function tagMatchScore(productTags: string[], userTags: string[]): number {
  if (productTags.length === 0) return 0;
  const matched = productTags.filter((tag) => userTags.includes(tag)).length;
  return matched / productTags.length;
}

function productFitScore(
  product: ProductMaster,
  worryTags: string[],
): number {
  const tagScore = tagMatchScore(product.fitTags, worryTags);
  // 収益要素は tie-breaker（最大10%）
  const revenueBonus = (product.revenuePriority / 100) * 0.1;
  return tagScore * 0.9 + revenueBonus;
}

export function matchProducts(
  exitType: ExitType,
  worryTags: string[],
  result: DiagnosisResultMaster,
  products: ProductMaster[],
): ProductMaster[] {
  const activeProducts = products.filter((p) => p.isActive);

  // 出口タイプに応じた商品カテゴリフィルタ
  const categoryFilter: Record<ExitType, ProductMaster['category'][]> = {
    free_only: ['completely_free', 'tool', 'education'],
    free_affiliate: ['free_registration'],
    paid_affiliate: ['paid_service'],
    own_product: ['own_product'],
    nothing_now: [],
    future_consider: ['completely_free', 'tool', 'education'],
  };

  const allowedCategories = categoryFilter[exitType];
  if (allowedCategories.length === 0) return [];

  // 結果マスターの推奨リストを優先
  const recommendedIds = [
    ...result.recommendedPaidAffiliate,
    ...result.recommendedFreeAffiliate,
  ];

  const candidates = activeProducts
    .filter((p) => allowedCategories.includes(p.category))
    .map((p) => ({
      product: p,
      score: productFitScore(p, worryTags) + (recommendedIds.includes(p.productId) ? 0.3 : 0),
    }))
    .sort((a, b) => b.score - a.score);

  return candidates.map((c) => c.product);
}

export function matchFreeContent(
  result: DiagnosisResultMaster,
  worryTags: string[],
  freeContent: FreeContentMaster[],
): FreeContentMaster[] {
  const active = freeContent.filter((c) => c.isActive);

  return active
    .filter((c) =>
      result.recommendedFreeContent.includes(c.contentId) ||
      c.targetWorryTags.some((tag) => worryTags.includes(tag)),
    )
    .slice(0, 5);
}
