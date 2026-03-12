<script setup lang="ts">
</script>

<template>
  <v-card elevation="1" rounded="lg">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-book-open-variant" class="mr-2" color="primary" />
      Quick Start Guide
    </v-card-title>

    <v-card-text>
      <v-expansion-panels variant="accordion" rounded="lg">
        <v-expansion-panel title="Step 1 - Upload an Image">
          <v-expansion-panel-text>
            <p>画像をドラッグ&ドロップ、またはクリックして選択します。</p>
            <ul class="ml-4 mt-2">
              <li>対応形式: JPG, PNG</li>
              <li>最大サイズ: 20MB</li>
            </ul>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Step 2 - Set Detection Target">
          <v-expansion-panel-text>
            <p>検出したいオブジェクトをテキストで入力します。</p>
            <p class="mt-1 text-medium-emphasis">例: cracks, vehicles, people, text etc.</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Step 3 - Choose Model & Resolution">
          <v-expansion-panel-text>
            <ul class="ml-4">
              <li><strong>GPT-4.1 Mini</strong> - Fast & cost-effective</li>
              <li><strong>GPT-4.1</strong> - Balanced</li>
              <li><strong>GPT-4.1 Nano</strong> - Lightweight</li>
            </ul>
            <p class="mt-2">解像度は Auto を推奨します。</p>
          </v-expansion-panel-text>
        </v-expansion-panel>

        <v-expansion-panel title="Step 4 - Read the Results">
          <v-expansion-panel-text>
            <ul class="ml-4">
              <li><strong>Detected / Not Found</strong> - 対象の検出有無</li>
              <li><strong>Confidence</strong> - AIの確信度 (0-100%)</li>
              <li><strong>History</strong> - 過去の解析結果を時系列で確認</li>
            </ul>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>
