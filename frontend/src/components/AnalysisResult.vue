<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  found: boolean
  confidence: number
}>()

const animatedConfidence = ref(0)

function animateConfidence(target: number) {
  animatedConfidence.value = 0
  const duration = 1000
  const start = performance.now()

  function step(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedConfidence.value = Math.round(target * eased)
    if (progress < 1) {
      requestAnimationFrame(step)
    }
  }
  requestAnimationFrame(step)
}

onMounted(() => animateConfidence(props.confidence))
watch(() => props.confidence, (val) => animateConfidence(val))

const circumference = 2 * Math.PI * 45
</script>

<template>
  <v-card elevation="1" rounded="lg" :color="found ? '#f0fdf4' : '#fef2f2'">
    <v-card-title class="text-h6">
      <v-icon icon="mdi-poll" class="mr-2" color="primary" />
      判定結果
    </v-card-title>

    <v-card-text class="text-center">
      <v-row align="center" justify="center">
        <v-col cols="auto">
          <v-icon
            :icon="found ? 'mdi-check-decagram' : 'mdi-close-octagon'"
            :color="found ? 'success' : 'error'"
            size="72"
          />
          <p class="text-h5 mt-2 font-weight-bold">{{ found ? 'Detected' : 'Not Found' }}</p>
        </v-col>

        <v-col cols="auto">
          <div class="confidence-chart">
            <svg viewBox="0 0 100 100" width="140" height="140">
              <circle
                cx="50" cy="50" r="45"
                fill="none"
                stroke="rgba(0,0,0,0.08)"
                stroke-width="8"
              />
              <circle
                cx="50" cy="50" r="45"
                fill="none"
                :stroke="found ? '#059669' : '#dc2626'"
                stroke-width="8"
                stroke-linecap="round"
                :stroke-dasharray="circumference"
                :stroke-dashoffset="circumference - (circumference * animatedConfidence) / 100"
                transform="rotate(-90 50 50)"
                class="confidence-ring"
              />
              <text
                x="50" y="50"
                text-anchor="middle"
                dominant-baseline="central"
                fill="#1e293b"
                font-size="20"
                font-weight="bold"
              >
                {{ animatedConfidence }}%
              </text>
            </svg>
          </div>
          <p class="text-body-2 text-medium-emphasis mt-1">Confidence</p>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<style scoped>
.confidence-ring {
  transition: stroke-dashoffset 0.1s ease;
}

.confidence-chart {
  display: inline-block;
}
</style>
