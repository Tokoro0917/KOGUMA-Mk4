# KOGUMA-Mk4 の KiCad プロジェクト

KiCad 9.0 で開く(`KOGUMA-Mk4.kicad_pro`)。

| ファイル | 中身 |
|---|---|
| `KOGUMA-Mk4.kicad_sch` | 一番上のシート。下のシートを並べる |
| `power.kicad_sch` | 電源(電池 → 電源スイッチ → VBAT → 3.3V、電池の電圧の分圧) |
| `KOGUMA-Mk4.kicad_sym` | このプロジェクト用の記号: AO4407A、LXDC55FAAA-203、片方向のTVS(D_TVS_Uni)、電源記号 VBAT |
| `KOGUMA-Mk4.pretty/` | このプロジェクト用のフットプリント: LXDC55FAAA-203(村田のデータシートの「Reference Land Pattern」) |
| `sym-lib-table`・`fp-lib-table` | 上の2つをプロジェクトのライブラリとして登録する |

## ネットの名前

| ネット | 中身 |
|---|---|
| `BAT+` | 電池の+(電源スイッチの前。電源のシートの中だけ) |
| `VBAT` | 電源スイッチのあと。MP6551・LXDC55 の入力 |
| `+3V3` | LXDC55 の出力 |
| `BATT` | 電池の電圧の分圧(MCU の PB1、ADC2_INP5 へ)。グローバルラベル |

## まだ決めていないこと

- SW1(SSSS810701)と J1(BT2.0 のケーブルをはんだ付けするパッド)のフットプリント。J1 は仮に `Connector_Wire:SolderWire-0.5sqmm_1x02_P4.8mm_D0.9mm_OD2.3mm`
- C4(ポリマー 47µF 25V)の品番と大きさ。仮に 7343
- LXDC55 のフットプリントは、データシートのランドパターンの寸法から作った。基板を注文する前に、実物か村田の最新の資料で確かめる

## 確かめたこと(2026-10-29、kicad-cli 9.0.9)

- ERC: エラー 0。警告は、確かめた環境に KiCad の標準ライブラリ(Device など)が登録されていないことによるものだけ
- ネットリストで、全部のピンが意図したネットにつながっていることを確かめた(つないでいないのは SW1 の3番、LXDC55 の NC と PG だけ)
