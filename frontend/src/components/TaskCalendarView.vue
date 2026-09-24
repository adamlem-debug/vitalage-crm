<template>
  <div class="task-calendar flex min-h-0 flex-1 overflow-hidden px-5 pb-5">
    <Calendar
      ref="calendar"
      class="h-full flex-1 overflow-hidden"
      :config="{
        defaultMode: 'Week',
        isEditMode: true,
        eventIcons: {},
        allowCustomClickEvents: true,
        enableShortcuts: false,
        noBorder: true,
        timeFormat: '24h',
      }"
      :events="taskEvents.data || []"
      :onClick="openTask"
      :onDblClick="openTask"
      :onCellClick="createTaskFromCell"
      @update="rescheduleTask"
      @rangeChange="handleRangeChange"
    >
      <template
        #header="{
          currentMonthYear,
          activeView,
          selectedMonthDate,
          decrement,
          increment,
          updateActiveView,
          onMonthYearChange,
          setCalendarDate,
        }"
      >
        <div class="my-4 flex w-full items-center justify-between">
          <DatePicker
            :modelValue="selectedMonthDate"
            :clearable="false"
            @update:modelValue="(value) => onMonthYearChange(value)"
          >
            <template #target="{ togglePopover }">
              <Button
                variant="ghost"
                class="text-lg-medium text-ink-gray-7"
                :label="currentMonthYear"
                iconRight="chevron-down"
                @click="togglePopover"
              />
            </template>
          </DatePicker>

          <div class="flex items-center gap-1">
            <Button
              variant="ghost"
              icon="lucide-chevron-left"
              @click="decrement"
            />
            <Button
              variant="ghost"
              :label="__('Today')"
              @click="setCalendarDate()"
            />
            <Button
              variant="ghost"
              icon="lucide-chevron-right"
              @click="increment"
            />
            <FormControl
              type="select"
              class="ml-1 w-24"
              :modelValue="activeView"
              :options="[
                { label: __('Day'), value: 'Day' },
                { label: __('Week'), value: 'Week' },
                { label: __('Month'), value: 'Month' },
              ]"
              @update:modelValue="updateActiveView($event)"
            />
          </div>
        </div>
      </template>
    </Calendar>
  </div>
</template>

<script setup>
import { sessionStore } from '@/stores/session'
import {
  Calendar,
  DatePicker,
  FormControl,
  call,
  createListResource,
  dayjs,
  toast,
} from 'frappe-ui'
import { ref, watch } from 'vue'

const props = defineProps({
  filters: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['showTask', 'createTask'])

const { user } = sessionStore()

const calendar = ref(null)
const activeRange = ref({
  startDate: dayjs().startOf('month').format('YYYY-MM-DD'),
  endDate: dayjs().endOf('month').format('YYYY-MM-DD'),
})

const statusColors = {
  Todo: 'blue',
  Backlog: 'violet',
  'In Progress': 'amber',
  Done: 'green',
  Canceled: 'orange',
  'Removed from Calendar': 'pink',
}

function resolveFilterValue(value) {
  if (value === '@me') return user

  if (Array.isArray(value)) {
    return value.map((item) => {
      if (item === '@me') return user
      if (item === '%@me%') return `%${user}%`
      return item
    })
  }

  return value
}

function buildFilters() {
  const filters = []

  Object.entries(props.filters || {}).forEach(([field, rawValue]) => {
    const value = resolveFilterValue(rawValue)

    if (
      Array.isArray(value) &&
      value.length >= 2 &&
      typeof value[0] === 'string'
    ) {
      filters.push([field, value[0], value[1]])
    } else {
      filters.push([field, '=', value])
    }
  })

  filters.push([
    'due_date',
    'between',
    [
      `${activeRange.value.startDate} 00:00:00`,
      `${activeRange.value.endDate} 23:59:59`,
    ],
  ])

  return filters
}

function parseDuration(value) {
  const duration = Number.parseInt(value, 10)
  return [30, 60, 90, 120].includes(duration) ? duration : 60
}

function taskToCalendarEvent(task) {
  if (!task.due_date) return null

  const start = dayjs(task.due_date)
  if (!start.isValid()) return null

  const end = start.add(parseDuration(task.custom_duration), 'minute')

  return {
    id: String(task.name),
    title: task.title || __('Untitled Task'),
    fromDate: start.format('YYYY-MM-DD'),
    toDate: end.format('YYYY-MM-DD'),
    fromTime: start.format('HH:mm'),
    toTime: end.format('HH:mm'),
    isFullDay: false,
    color: statusColors[task.status] || 'blue',
    task,
  }
}

const taskEvents = createListResource({
  doctype: 'CRM Task',
  fields: [
    'name',
    'title',
    'due_date',
    'custom_duration',
    'status',
    'priority',
    'assigned_to',
    'custom_task_type',
    'reference_doctype',
    'reference_docname',
  ],
  filters: buildFilters(),
  orderBy: 'due_date asc',
  pageLength: 9999,
  auto: true,
  transform: (tasks) =>
    (tasks || [])
      .map(taskToCalendarEvent)
      .filter(Boolean),
})

function reload() {
  taskEvents.update({ filters: buildFilters() })
  return taskEvents.reload()
}

watch(
  () => props.filters,
  () => reload(),
  { deep: true },
)

function normalizeCalendarEvent(payload) {
  return payload?.calendarEvent || payload || {}
}

function openTask(payload) {
  const event = normalizeCalendarEvent(payload)
  if (!event.id) return
  emit('showTask', event.id)
}

function normalizeCellTime(time) {
  if (!time) return '09:00'

  const raw = String(time).trim().toLowerCase()

  if (/^\d{1,2}:\d{2}/.test(raw)) {
    const [hour, minute] = raw.split(':')
    return `${String(Number(hour)).padStart(2, '0')}:${minute.slice(0, 2)}`
  }

  const match = raw.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$/)
  if (!match) return '09:00'

  let hour = Number(match[1])
  const minute = match[2] || '00'
  const period = match[3]

  if (period === 'pm' && hour < 12) hour += 12
  if (period === 'am' && hour === 12) hour = 0

  return `${String(hour).padStart(2, '0')}:${minute}`
}

function createTaskFromCell(payload = {}) {
  const date = dayjs(payload.date || new Date()).format('YYYY-MM-DD')
  const time = normalizeCellTime(payload.time)

  emit('createTask', {
    due_date: `${date} ${time}:00`,
    custom_duration: '60',
  })
}

async function rescheduleTask(payload) {
  const event = normalizeCalendarEvent(payload)
  if (!event.id || !event.fromDate || !event.fromTime) {
    await reload()
    return
  }

  const dueDate = `${event.fromDate} ${String(event.fromTime).slice(0, 5)}:00`

  try {
    await call('frappe.client.set_value', {
      doctype: 'CRM Task',
      name: event.id,
      fieldname: 'due_date',
      value: dueDate,
    })
    toast.success(__('Task rescheduled'))
  } catch (error) {
    toast.error(
      error?.messages?.[0] || __('Failed to reschedule task'),
    )
  } finally {
    await reload()
  }
}

async function handleRangeChange(range) {
  if (!range?.startDate || !range?.endDate) return

  activeRange.value = {
    startDate: range.startDate,
    endDate: range.endDate,
  }

  await reload()
}

defineExpose({ reload })
</script>

<style scoped>
/*
 * Phase 1 supports drag-to-reschedule only.
 * Frappe UI uses the bottom resize handle for changing event duration;
 * hide it until CRM Task custom_duration snapping is implemented.
 */
.task-calendar :deep(.cursor-ns-resize) {
  display: none;
}
</style>
