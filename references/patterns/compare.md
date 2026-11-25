# パターン: compare

「ビフォー」のパネル（赤いバッジ、赤い縁の項目、困りごと）が、ボタンを押すと虹色の枠に入った「アフター」のパネル（緑のバッジ、緑の項目、金色の見出し）に切り替わります。

「いつものやり方とよりよいやり方」に使います。前例をなぞった承認フロー、手作業と自動化、旧構成と新構成の言葉での説明などです。2つの*図*を並べたいときは、spec を2つ使ってください。

## Spec

```json
{
  "pattern": "compare",
  "title": "その申請、全部に承認が要る？",
  "button": "慣習を疑う ▶",
  "back": "戻る",
  "before": {"label": "ビフォー", "title": "全部が課長待ち",
             "items": ["定例の更新", "少額の備品購入"], "message": "何がつらいか"},
  "after":  {"label": "アフター", "title": "リスクで振り分ける",
             "items": [{"text": "定例の更新 → 自動承認", "tone": "good"},
                       {"text": "新規の取引先 → 課長", "tone": "neutral"}],
             "headline": "待ち行列が半分に", "message": "何が変わったか"}
}
```

| フィールド | 補足 |
|---|---|
| `before`, `after` | `label`（バッジ）、`title`、`items`、`message`。`after.headline` は金色で表示 |
| `items[]` | 文字列か、`{"text", "tone"}`。tone は `bad`、`good`、`neutral`。既定は before が `bad`、after が `good` |
| `metric` | 任意。`{"label", "before", "after", "unit"}`。before と after は0以上の整数。ビフォー側に before の値、アフター側に after の値を出し、アフターに切り替えた瞬間に before から after へ数字が数え上がる（下がる）。焦点の数字は1つだけにする |
| `metric.goal`, `metric.better` | 任意。goal を書くと、両側に目標の線が入ったゲージが出て、「到達 ✓」か「未達」を言葉と枠で示す。better は `lower`（小さいほどよい）か `higher`。省略すると before から after への向きで決める（before と after が同じ値ならエラーになるので書く）。目標の文字（「目標 15件」）は短く |
| `before.cutin`, `after.cutin` | 任意。パネルが出たときに斜めの帯で割り込む一言。ふつうは `after` にだけ書く |
| `hush` | 任意。`true` にすると、アフターを開いたときに見出しとボタンの動きが止まり、ボタンを横切る光が薄くなる（文字は薄くしない） |

## 上限

- 各側の項目は2〜6個。スマホで1行に2つ並ぶよう、1項目はおよそ30文字未満にします。
- 印刷と PDF では、ボタンなしで両方のパネルを縦に並べて表示します。
