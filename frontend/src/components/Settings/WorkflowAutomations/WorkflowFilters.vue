<template>
  <div class="space-y-2">
    <label v-if="label" class="block text-sm text-ink-gray-5">
      {{ label }}
    </label>
    <CFConditions
      :key="doctype"
      :conditions="conditions"
      :isChild="true"
      :doctype="doctype"
      :allowGrouping="!flat"
    />
    <p v-if="flat && leafCount > 1" class="text-xs text-ink-gray-5">
      {{ __('A trigger runs only when these filters match.') }}
    </p>
  </div>
</template>

<script setup>
import CFConditions from '@/components/ConditionsFilter/CFConditions.vue'
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Array], default: '' },
  doctype: { type: String, default: '' },
  label: { type: String, default: () => __('Filters') },
  flat: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const conditions = reactive(read(props.modelValue))
let mirrored = JSON.stringify(conditions)

watch(
  () => props.modelValue,
  (value) => {
    const parsed = read(value)
    const incoming = JSON.stringify(parsed)
    if (incoming === mirrored) return
    conditions.splice(0, conditions.length, ...parsed)
    mirrored = incoming
  },
)

watch(
  conditions,
  (value) => {
    mirrored = JSON.stringify(value)
    emit('update:modelValue', mirrored)
  },
  { deep: true },
)

const leafCount = computed(() => countLeaves(conditions))

function read(value) {
  if (Array.isArray(value)) return structuredClone(value)
  try {
    const parsed = JSON.parse(value || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function countLeaves(rows) {
  let count = 0
  for (const row of rows || []) {
    if (!Array.isArray(row)) continue
    if (Array.isArray(row[0])) count += countLeaves(row)
    else count += 1
  }
  return count
}
</script>
