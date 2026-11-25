---
name: dopamine-diagrams
description: 目を引くインタラクティブな解説図（アーキテクチャ図、フロー、循環、ビフォー/アフター、成熟度の段、状況別の判断表、分解、平均に埋もれる1件）を、HTML と CSS だけで作る。流れる虹色の見出し、金文字、注目の箱を回る虹色の枠、ネオンの脈動、ハンコのように出る答えといった派手な演出が付く。1つの JSON から Zenn の html-embed ブロック（JavaScript なし）、単体の HTML ページ、PDF に印刷できる16:9スライドを出力し、全幅で全部のボタンを押す表示検査も付く。ドパガキ向けの図、Zenn 記事やブログ、スライドで「止まって見てもらえる図」が欲しいときに使う。English keywords - architecture diagram, flow, cycle, before/after, maturity ladder, explorer, game-show effects, Zenn html-embed, slides.
license: MIT
---

# dopamine-diagrams

光っていないものは読み飛ばす読者のための図です。わざと派手にしていますが、派手さは1〜2か所の焦点にだけ使います。そうしないと図が何も伝えなくなります。

すべて HTML と CSS です。操作は隠したチェックボックスやラジオボタンと `:checked` で作るので、JavaScript が禁止の場所（Zenn の `html-embed`）でもスライドでも同じ出力が動きます。

英語版は `SKILL.en.md` と `references/en/` にあります。内容は同じです。ボタンなどの既定の文言は、spec の文字列にひらがなかカタカナがあれば日本語、なければ英語になります。spec に `"lang": "ja"` か `"lang": "en"` を書けば、そちらが優先されます。

## ファイルと読むタイミング

| ファイル | 読むとき |
|---|---|
| `references/targets/zenn.md` | Zenn の記事に載せる |
| `references/targets/slides.md` | スライドや PDF に載せる |
| `references/targets/standalone.md` | 単体の HTML ページにする（ドキュメント、ブログ、README のプレビュー） |
| `references/patterns/<pattern>.md` | 図の種類を決めたあと。spec の項目、上限、例 |
| `references/effects.md` | 演出を変える、または足す前（安全上の上限） |
| `references/interactions.md` | クリックで切り替わる状態を足す、または変える前 |
| `references/pitfalls.md` | 表示がおかしいとき。新しい CSS を書く前 |
| `references/citation.md` | 他人の文書を要約した図のとき |
| `templates/base.css`, `templates/parts/*.css` | 見た目を変えるとき |
| `scripts/build.py` | 毎回。JSON の spec から出力を作る |
| `scripts/check.mjs` | 毎回。組み立てるたびに表示を検査する |

## 手順（飛ばさない）

1. **出力先を決める**: `zenn`、`slides`、`standalone` のどれか。`references/targets/` の該当ファイルを読む。
2. **図にする価値があるか決める。** 3列の表で同じことが言えるなら表にする。
3. 下の表から**図の種類を選び**、`references/patterns/` の該当ファイルを読む。
4. **派手さの予算を配る**（次の節）。焦点にする要素を1〜2個と、強さのレベルを決める。
5. **spec を JSON で書く**（`examples/` から1つコピーする）。中身だけを書き、HTML は書かない。
6. **組み立てる**:
   ```sh
   python3 scripts/build.py spec.json --target zenn -o out.md
   python3 scripts/build.py a.json b.json --target slides -o deck.html
   python3 scripts/build.py spec.json --target standalone -o page.html --intensity 3
   ```
   必須の項目がない、または出力を壊す値が入っていると、build.py は `error: …` を出して止まります。スマホのレイアウトに収まらないラベルがあると `WARN: …` を出します。spec を直してください。警告を無視しないこと。
7. FAIL が0件になるまで**検査する**:
   ```sh
   npm run setup          # 最初の1回だけ。playwright-core 経由でインストール済みの Google Chrome を使う
   node scripts/check.mjs out.md --shots .check/out
   node scripts/check.mjs deck.html --pdf deck.pdf
   ```
   Node や Chrome がなくても静的な検査は走り、表示の検査を飛ばしたことを表示します。その場合はユーザーにそう伝え、レイアウトを確かめたとは言わないこと。
8. **スクリーンショットを見る**（`--shots`。zenn は状態ごとに700px と340px、ライトとダーク。ほかの出力先は最後のクリック後のページ全体）。検査では、はみ出し、切れた文字（SVG の箱より長いラベルを含む）、高さ、文字サイズ、折り返し、ループの速さ、architecture の層名が帯からはみ出していないか、線のラベルが箱や層名に重なっていないか、線が関係のない箱の下を通っていないかを測ります。空きすぎた余白と、線どうしの交差は検査では見つけられません。
9. 元になる文書を要約した図なら、`note` に `references/citation.md` を当てる。

## 図の種類

| 見せたいもの | 種類 | 操作 |
|---|---|---|
| コンポーネントと、リクエストの流れ | `architecture` | 線に沿って光が流れる。箱にマウスを乗せると、つながる線だけが光る |
| 「X のときは Y する（Z ではない）」を複数の状況で | `explorer` | 状況を選ぶと、虹色の枠の中に答えがスタンプで出る |
| 具体的な項目に分けるべき、ふわっとした一文 | `decompose` | クリックで分解。項目が1つずつ現れ、金色の「完了」スタンプが押される |
| いつものやり方と、よりよいやり方 | `compare` | クリックでビフォーが虹色の枠のアフターに切り替わる |
| 繰り返す循環（と、目的から戻り直すタイミング） | `loop` | 円に沿って光が回り、手順が順に光る |
| 一直線の手順 | `flow` | 線に沿って光が流れる。手順を選ぶと説明が出る。焦点の手順は虹色の枠 |
| 段階、成熟度、段階的な計画 | `ladder` | 自分の段を選ぶと、「いま」と金文字の「次の一手」が出る |
| 平均に埋もれる、まれだけど大事な1件 | `proportion` | 100個の点。クリックで多数派が薄れ、大事な1個が光る |

どれも合わなければ `base.css` の部品から組み、検査を通してください。

## 派手さの予算

図の大部分が静かなときだけ、演出が効きます。

- **焦点は1つの図に1〜2個。** 金文字、虹色の枠、ネオンはそこにだけ使います。`architecture` では `focal` に並べ、`flow` では `focal` に手順を1つ指定します。ほかの種類では、答えの欄（または最上段、または光る1個）が最初から焦点です。
- **強さ**（`--intensity` か spec の `"intensity"`）:
  - `1` 控えめ: 普通の見出し、アクセント色の枠、やわらかい登場。社内資料や堅めのスライド向け。
  - `2` 標準（既定）: 虹色の見出し、金文字、ネオン、スタンプ、虹色の枠。
  - `3` 全開: 枠の回転と脈動が速く、線も光る。看板の図やトークの最初の1枚向け。
- 虹色の枠を2つ並べない。全部の箱を焦点にしない。
- 重要度を段階で見せるときは `importance`（1〜4）を使う。パチンコの保留の色やガチャのレアリティと同じく、虹色（4）は最上位に1つだけ。

## 守ること

- **点滅させない。** 0.5秒より短いアニメーションのループは使わず、速さにかかわらず点いたり消えたりさせない。光の強弱は1秒以上かけて変える。Zenn は点滅する埋め込みを禁止していて、WCAG 2.3.1 は点滅を1秒に3回までとしています。検査は0.5秒未満のループを FAIL にします。
- **動きを止めても全部読める。** どの要素も基本のスタイルが最後の状態で、アニメーションは登場の動きを足すだけ。`prefers-reduced-motion` と `@media print` ではアニメーションをすべて止める。
- **表示される文字は12px 以上。** 縮小された SVG の文字も含みます。`build.py` は architecture の文字をいちばん狭い幅に合わせて決め、検査がそれを確かめます。
- **色だけで区別しない。** 状態が変わるときは文字も変える（ボタンの文言、取り消し線、タグ）。
- **zenn では JavaScript を使わない。** ほかの出力先でも使わないので、1つの spec がどこでも動きます。
- **出力を手で直さない。** spec かテンプレートを直して組み立て直す。

## 拡張

新しい種類を足すときは、`scripts/build.py` の描画関数（`RENDER` に登録）、`templates/parts/` の CSS、`references/patterns/` と `references/en/patterns/` の説明、`examples/` と `examples/en/` のサンプル spec を用意します。状態のセレクタは図ごとの一意な id で作り（`render_explorer` を参照）、CSS のクラス名は種類ごとの接頭辞を付け、3つの出力先すべてで検査を通してください。
