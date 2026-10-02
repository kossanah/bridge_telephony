<template>
  <div class="h-[294px] text-base">
    <FormControl
      v-model="task.title"
      type="text"
      variant="ghost"
      class="mb-2 title"
      :placeholder="__('Schedule a task...')"
    />
    <TextEditor
      ref="content"
      variant="ghost"
      editor-class="prose-sm h-[140px] text-ink-gray-9 overflow-auto p-2 bg-surface-gray-2 rounded-lg border border-outline-gray-2"
      :bubbleMenu="true"
      :content="task.description"
      :placeholder="__('Add description...')"
      @change="(val) => (task.description = val)"
    />
    <div class="flex flex-col gap-2">
      <div class="flex gap-2">
        <Dropdown :options="taskStatusOptions(updateTaskStatus)">
          <Button
            :label="task.status"
            variant="subtle"
            class="text-ink-gray-8 hover:text-ink-gray-9 cursor-pointer"
          >
            <template #prefix>
              <TaskStatusIcon :status="task.status" />
            </template>
          </Button>
        </Dropdown>
        <Dropdown :options="taskPriorityOptions(updateTaskPriority)">
          <Button
            :label="task.priority"
            variant="subtle"
            class="text-ink-gray-8 hover:text-ink-gray-9 cursor-pointer"
          >
            <template #prefix>
              <TaskPriorityIcon :priority="task.priority" />
            </template>
          </Button>
        </Dropdown>
      </div>
      <Link
        class="user"
        :value="getUser(task.assigned_to).full_name"
        doctype="User"
        :placeholder="__('John Doe')"
        :filters="{
          name: ['in', users.data?.crmUsers?.map((user) => user.name)],
          ignore_user_type: 1,
        }"
        :hideMe="true"
        @change="(option) => (task.assigned_to = option)"
      >
        <template #prefix>
          <UserAvatar class="mr-2 !h-4 !w-4" :user="task.assigned_to" />
        </template>
        <template #item-prefix="{ option }">
          <UserAvatar class="mr-2" :user="option.value" size="sm" />
        </template>
        <template #item-label="{ option }">
          <Tooltip :text="option.value">
            <div class="cursor-pointer text-ink-gray-9">
              {{ getUser(option.value).full_name }}
            </div>
          </Tooltip>
        </template>
      </Link>
      <DateTimePicker
        v-model="task.due_date"
        class="datepicker w-36"
        :placeholder="__('01/04/2024 11:30 PM')"
        :formatter="(date) => getFormat(date, '', true, true)"
        input-class="border-none"
      />
    </div>
  </div>
</template>
<script setup>
import TaskStatusIcon from '@/components/Icons/TaskStatusIcon.vue'
import TaskPriorityIcon from '@/components/Icons/TaskPriorityIcon.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import Link from '@/components/Controls/Link.vue'
import { usersStore } from '@/stores/users'
import { taskStatusOptions, taskPriorityOptions, getFormat } from '@/utils'
import { TextEditor, Dropdown, Tooltip, DateTimePicker } from 'frappe-ui'
import { reactive } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    default: () => ({
      title: '',
      description: '',
      assigned_to: '',
      due_date: '',
      status: 'Backlog',
      priority: 'Low',
    }),
  },
})

const task = reactive(props.task)

const { users, getUser } = usersStore()

function updateTaskStatus(status) {
  task.status = status
}

function updateTaskPriority(priority) {
  task.priority = priority
}
</script>
<style scoped>
:deep(.title input) {
  background-color: transparent;
  caret-color: var(--text-ink-gray-9, currentColor);
  color: var(--text-ink-gray-9, currentColor);
  outline: none;
  border: none;
  padding: 0;
}
:deep(.datepicker input) {
  background-color: var(--surface-gray-2);
  caret-color: var(--text-ink-gray-9, currentColor);
  color: var(--text-ink-gray-9, currentColor);
  outline: none;
  border: 1px solid var(--outline-gray-2);
  border-radius: 6px;
}

:deep(.title input:focus) {
  border: none;
  outline: none;
  box-shadow: none;
}
:deep(.datepicker input:focus) {
  border-color: var(--outline-gray-3);
  outline: none;
  box-shadow: none;
}

:deep(.user button) {
  background-color: var(--surface-gray-2);
  border: 1px solid var(--outline-gray-2);
  color: var(--text-ink-gray-8);
  border-radius: 6px;
}
:deep(.user button:hover) {
  background-color: var(--surface-gray-3);
  color: var(--text-ink-gray-9);
}
:deep(.user button:focus) {
  box-shadow: none;
  outline: none;
}
</style>
