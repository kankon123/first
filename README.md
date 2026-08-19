# 競馬診断ファネル

> 競馬商品を売る診断ではなく、その人に合う「馬券との付き合い方」を見つける診断。

## コンセプト

```
YouTube → LINE → 馬券診断 → 診断結果 → 漫画・無料コンテンツ・商品紹介
```

**「売るための診断」ではなく、「適切な出口を選ぶための診断」**

- 無料コンテンツだけで十分な人 → 無料で案内
- 有料商品が合う人 → 条件を満たす場合のみ紹介
- 今は何も買わない方がいい人 → 正直にそう伝える

## 設計思想

詳細は [`docs/design-philosophy.md`](docs/design-philosophy.md) を参照。

## アーキテクチャ

```
回答 → 特性スコア → 診断タイプ → ニーズ・悩みタグ → 適合条件
  → 候補コンテンツ/候補商品 → 優先順位付け → 表示
```

**診断ロジックと商品を直接ベタ結合しない。**

詳細は [`docs/architecture.md`](docs/architecture.md) を参照。

## ディレクトリ構成

```
docs/                  設計ドキュメント
schemas/               JSON Schema（マスター定義）
data/masters/          マスターデータ（JSON）
src/
  types/               TypeScript型定義
  domain/
    scoring/           Layer 2: 回答→スコア
    typing/            Layer 3: スコア→タイプ
    exit/              Layer 4: 出口判定
    matching/          Layer 5: 商品適合
  application/         パイプライン全体
```

## マスターデータ

| マスター | ファイル | 用途 |
|---------|---------|------|
| 商品 | `data/masters/products.json` | 商品・サービス情報 |
| 質問 | `data/masters/questions.json` | 診断質問と内部スコア |
| 結果 | `data/masters/results.json` | 診断タイプ定義 |
| 漫画 | `data/masters/comics.json` | 悩み別漫画 |
| 無料コンテンツ | `data/masters/free-content.json` | 無料教材・動画等 |
| 出口ルール | `data/masters/exit-rules.json` | 出口判定条件 |

## 出口タイプ

| 出口 | 説明 | 収益 |
|------|------|------|
| `free_only` | 無料コンテンツで十分 | 0円 |
| `free_affiliate` | 無料登録型アフィリエイト | 成果報酬 |
| `paid_affiliate` | 有料アフィリエイト | 成果報酬 |
| `own_product` | 自社商品 | 直接収益 |
| `nothing_now` | 今は何も買わない | LINE継続 |
| `future_consider` | 将来的に検討 | 見込み客 |

## Cursorへの依頼事項

今後の実装では常に以下を優先:

1. ユーザーの自己理解
2. 悩みの分類
3. タイプ判定
4. 無料を含めた複数出口
5. 商品適合判定
6. 漫画分岐
7. CTA分岐
8. 行動計測
9. 後から商品を追加できる構造
10. 特定商品に依存しない設計

## 絶対に避けること

- 全員同じ商品を出す
- 診断結果＝商品名
- 漫画がただの商品広告
- 報酬額だけで商品を優先
- 「今のあなたには何も買わなくていい」を出さない
