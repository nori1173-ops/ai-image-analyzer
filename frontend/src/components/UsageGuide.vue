<script setup lang="ts">
</script>

<template>
  <v-card>
    <v-card-title class="text-h6">
      <v-icon icon="mdi-help-circle" class="mr-2" />
      使い方ガイド
    </v-card-title>

    <v-card-text>
      <v-expansion-panels variant="accordion">
        <v-expansion-panel title="1. 画像をアップロード">
          <v-expansion-panel-text>
            <p>ドラッグ&ドロップまたはクリックして画像を選択します。</p>
            <ul class="ml-4 mt-2">
              <li>対応形式: JPG, PNG</li>
              <li>最大サイズ: 20MB</li>
            </ul>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="2. 検出対象を入力">
          <v-expansion-panel-text>
            <p>画像から見つけたいものをテキストで入力します。</p>
            <p class="mt-1 text-medium-emphasis">例: ひび割れ、人物、テキスト、特定の物体など</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="3. モデルを選択">
          <v-expansion-panel-text>
            <ul class="ml-4">
              <li><strong>Claude Haiku 4.5</strong> - 推奨・低コスト</li>
              <li><strong>Claude Sonnet 5</strong> - 高精度</li>
              <li><strong>Claude Sonnet 4.6</strong> - 高精度</li>
            </ul>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="4. 結果の見方">
          <v-expansion-panel-text>
            <ul class="ml-4">
              <li><strong>発見/未検出</strong> - 対象が見つかったかどうか</li>
              <li><strong>確信度</strong> - AIの確信度 (0-100%)</li>
              <li><strong>解析ログ</strong> - 過去の解析結果を時系列で表示</li>
            </ul>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="5. 画像比較（災害差分監視）">
          <v-expansion-panel-text>
            <p>「画像比較」タブでは、前回・今回の2枚の画像から災害危険度を判定します。</p>
            <ol class="ml-4 mt-2">
              <li>「前回の画像」「今回の画像」を2枚アップロード</li>
              <li>監視観点を入力（例: 土砂崩れ、河川水位の上昇）</li>
              <li>「比較実行」で判定を開始</li>
            </ol>
            <p class="mt-2">
              危険度（なし/低/中/高）と判定理由・変化点を表示します。
              「危険検知時にメール通知する」を有効にすると、危険判定時のみサーバー側で設定された宛先へ通知メールが送信されます。
            </p>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>
