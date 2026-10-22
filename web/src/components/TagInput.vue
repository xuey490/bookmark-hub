<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  modelValue: string[]
  max?: number
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

const inputValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)
const maxTags = computed(() => props.max ?? 10)

function focusInput() {
  inputRef.value?.focus()
}

function commit() {
  const raw = inputValue.value.trim()
  if (!raw) return

  const pieces = raw
    .split(',')
    .map((item) => item.trim().replace(/^#+/, ''))
    .filter(Boolean)

  const next = [...props.modelValue]
  for (const piece of pieces) {
    if (next.length >= maxTags.value) break
    const value = piece.slice(0, 20)
    if (!next.some((tag) => tag.toLowerCase() === value.toLowerCase())) {
      next.push(value)
    }
  }
  emit('update:modelValue', next)
  inputValue.value = ''
}

function removeTag(tag: string) {
  emit(
    'update:modelValue',
    props.modelValue.filter((item) => item !== tag),
  )
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' || event.key === ',') {
    event.preventDefault()
    event.stopPropagation()
    commit()
  } else if (
    event.key === 'Backspace' &&
    !inputValue.value &&
    props.modelValue.length
  ) {
    removeTag(props.modelValue[props.modelValue.length - 1])
  }
}
</script>

<template>
  <div class="tag-input" @click="focusInput">
    <a-tag
      v-for="tag in modelValue"
      :key="tag"
      closable
      @close.prevent="removeTag(tag)"
    >
      {{ tag }}
    </a-tag>
    <input
      ref="inputRef"
      v-model="inputValue"
      class="tag-input__field"
      :placeholder="modelValue.length >= maxTags ? '最多 10 个标签' : placeholder ?? '输入标签，回车或逗号确认'"
      :disabled="modelValue.length >= maxTags"
      @keydown="onKeydown"
      @blur="commit"
    />
  </div>
</template>
