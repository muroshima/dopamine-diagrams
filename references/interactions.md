# JavaScript なしの操作

クリックで変わる状態は、すべて隠した `<input type="radio|checkbox" class="h">` と、ボタン役の `<label for>` の組で作ります。CSS は `#id:checked ~ …` で反応します。

| やりたいこと | input | 例 |
|---|---|---|
| N 個のうち1つを表示（タブ、ケース） | `radio`。`name` をそろえ、先頭を `checked` にする | `explorer` |
| ビフォーとアフター、表示と非表示 | `checkbox` | `decompose` |
| 押した数を数える、全部そろった・残り1つを判定する | `checkbox` を N 個。数は `counter-increment` を input より後ろの要素で表示。判定は `#c0:checked~#c1:not(:checked)~…` の兄弟の連鎖 | `combo` |
| マウスを乗せた要素のつながりをたどる | なし。`svg:has(.n-x:hover) .edge:not(.x-x)` | `architecture` |

## ルール

1. **input は先頭に置きます。** `.dd` の中で、操作対象のどれよりも前に置きます。`~` は後ろの兄弟要素にしか届きません。そのため input は、操作対象（またはその祖先）の兄弟にします。input をパネルの中に入れると、セレクタが全部効かなくなります。
2. **id は図ごとに一意にします。** スライドやページには図が複数入ります。build.py は id の頭に図の id を付けます（`dd3f2a1c-m0`）。`tab1` のような id を手で書かないでください。
3. **色だけでなく、ラベルの文言も変えます**（例: 「分解する ▶」が「戻る」に変わる。英語の spec では "Break it down ▶" が "Back" に変わる）。
4. **キーボード**: 隠した input もフォーカスできます。対応するラベルに `:focus-visible` の枠線を付けます（build.py は生成するすべての状態にこれを付けます）。
5. **タッチ**: `:hover` の効果はおまけです。大事なことを hover だけに頼らないでください。
6. **印刷**: PDF でどの状態を見せるかを決め、`@media print` のルールを足します（`decompose` がそうしています）。
7. **Zenn**: 表示される input は checkbox と radio だけです。`<button>` やテキスト入力は隠されます。
