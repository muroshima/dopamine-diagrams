# dopamine-diagrams

[English](README.md) | **日本語**

ドパガキ向けの図を作るエージェントスキルです。Claude Code など、`SKILL.md` に対応したエージェントで使えます。

見出しには虹色のグラデーションが流れ、大事な言葉は金文字で光ります。いちばん見てほしい箱の周りは虹色の光が回り、クリックすると答えがハンコのようにドンと出ます。スクロールで読み飛ばされがちな図を、止まって見てもらうための見た目です。

HTML と CSS だけでできています。1つの JSON から、次の3通りに出力できます。

- **Zenn の `html-embed`** ブロック（JavaScript が使えない環境でもそのまま動きます）
- **単体の HTML** ページ
- **16:9 のスライド**（PDF に印刷できます）

検査スクリプトも付いています。出力を Chrome で開き、幅ごとに全部のボタンを押して、横のはみ出し、12px 未満の文字、Zenn の高さ上限500px、点滅とみなされる速さのアニメーションを見つけると FAIL にします。

<p>
<img src="docs/architecture.png" width="49%" alt="アーキテクチャ図。層ごとに箱が並び、接続線に光が流れる。API の箱に虹色の枠">
<img src="docs/explorer-dark.png" width="49%" alt="ダークモードの explorer。左に HTTP エラーの一覧、選んだものに取り消し線のNG例と、虹色の枠の答え">
</p>
<p>
<img src="docs/decompose.png" width="66%" alt="decompose。「システムを安全にする」が5つの具体的な要件に分かれ、金色の Testable! のスタンプ">
<img src="docs/architecture-phone-dark.png" width="32%" alt="同じアーキテクチャ図をスマホ向けに縦に並べたもの">
</p>

## ドパガキって？

ドーパミン中毒のガキ、の略です。短い刺激に慣れていて、長い文章を読む前に離脱してしまう読者のことを、自虐も込めてこう呼んでいます。

このスキルの図は、もともと「【ドパガキ向け】AI 時代の要求管理 ハンドブックを読もう」という Zenn 記事のために作りました。派手な見た目は効きました。ただ、効いたのは、派手さを1〜2か所の焦点だけに使ったからです。全部を光らせると、ただのノイズになります。このスキルも「**焦点は1か所、残りは静かに**」というルールで作っています。

## 図の種類

| 種類 | 見せるもの | 操作 |
|---|---|---|
| `architecture` | 層ごとのコンポーネントと、リクエストの流れ | 接続線に光が流れる。箱にマウスを乗せると、つながる線だけが光る |
| `explorer` | 「X のときは Y する（Z ではない）」を複数の状況で | 状況を選ぶと、答えがスタンプで出る |
| `decompose` | ふわっとした一文を、具体的な項目に分解する | クリックで分解。項目が順に現れ、金色のスタンプが押される |

派手さの強さは3段階です。`1` は控えめ（社内資料や堅めの場向け）、`2` は標準、`3` は全開です。

## 導入

```sh
git clone https://github.com/muroshima/dopamine-diagrams ~/.claude/skills/dopamine-diagrams
cd ~/.claude/skills/dopamine-diagrams && npm run setup   # 任意。検査用（インストール済みの Chrome を使います）
```

あとはエージェントに頼むだけです。例えば「オンコールのエスカレーションルールを、dopamine-diagrams の explorer で Zenn 用に作って」と頼むと、エージェントが `SKILL.md` の手順に沿って作ります。出力先と図の種類を決めて、JSON を書き、組み立てて、検査して、見た目を確認する流れです。

## スクリプトを直接使う

```sh
python3 scripts/build.py examples/explorer.json --target zenn -o out.md
python3 scripts/build.py examples/*.json --target slides -o deck.html
python3 scripts/build.py examples/*.json --target standalone -o page.html --intensity 3
node scripts/check.mjs out.md --shots .check/out
node scripts/check.mjs deck.html --pdf deck.pdf
```

`build.py` は Python 3 だけで動きます。`check.mjs` には、Node 18 以上と、`npm run setup`（playwright-core）、Google Chrome が必要です。そろっていない場合は静的な検査だけを行い、その旨を表示します。

## 演出のルール

- 点滅させません。0.5秒より速いループは使わず、光の強弱は1秒以上かけて変えます（Zenn は点滅する埋め込みを禁止しています。WCAG 2.3.1 の基準もあります）。
- 動きを減らす設定の閲覧者と印刷では、動きをすべて止めます。止めた状態でもすべて読めるように作っています。
- 表示される文字は12px 以上にします（縮小された SVG の文字も含みます）。色だけで区別しません。

## Zenn で使うときの注意

Zenn 公式は切り替えの境目を640px と案内しています。ただ、実測すると、画面幅1100px の PC で埋め込みの幅は591px でした。640px のままだと、PC の読者にもスマホ用のレイアウトが出てしまいます。このスキルは境目を560px にしています。詳しくは [references/targets/zenn.md](references/targets/zenn.md) を見てください。

## ライセンス

MIT
