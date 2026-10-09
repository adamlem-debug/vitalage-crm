<template>
  <Dialog v-model:open="show" :size="'xl'">
    <template #body>
      <div class="px-4 pt-5 pb-6 bg-surface-elevation-1 sm:px-6">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="text-3xl-semibold leading-6 text-ink-gray-9">
              {{ __('New Organization') }}
            </h3>
          </div>
          <div class="flex items-center gap-1">
            <Button
              v-if="isManager() && !isMobileView"
              variant="ghost"
              class="w-7"
              :tooltip="__('Edit Fields Layout')"
              :icon="EditIcon"
              @click="openQuickEntryModal"
            />
            <Button
              variant="ghost"
              class="w-7"
              icon="lucide-x"
              @click="show = false"
            />
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div>
            <label class="text-sm text-ink-gray-6">{{ __('IČO') }}</label>
            <div class="flex gap-2 mt-1">
              <FormControl
                v-model="organization.doc.custom_ico"
                type="text"
                placeholder="12345678"
                maxlength="8"
              />
              <Button
                :label="__('ARES')"
                variant="solid"
                :loading="aresLoading"
                :disabled="!organization.doc.custom_ico || aresLoading"
                @click="lookupAres"
              />
            </div>
          </div>
          <div>
            <label class="text-sm text-ink-gray-6">{{ __('DIČ') }}</label>
            <FormControl
              v-model="organization.doc.custom_dic"
              class="mt-1"
              type="text"
              placeholder="CZ12345678"
            />
          </div>
        </div>
        <div
          v-if="aresMessage"
          class="mb-4 rounded p-3 text-sm bg-surface-gray-2 text-ink-gray-9"
          role="status"
        >
          {{ aresMessage }}
          <Button
            v-if="aresStatus === 'unavailable'"
            class="ml-2"
            variant="solid"
            :label="__('Zkusit znovu')"
            @click="lookupAres"
          />
          <Button
            v-if="aresStatus === 'existing' && existingOrganization"
            class="ml-2"
            variant="solid"
            :label="__('Vybrat existující')"
            @click="chooseExistingOrganization"
          />
        </div>
        <div v-if="aresAddress !== null" class="mb-4">
          <label class="text-sm text-ink-gray-6">{{
            __('Adresa sídla (ARES)')
          }}</label>
          <FormControl v-model="aresAddress" class="mt-1" type="text" />
          <p class="text-xs text-ink-gray-5 mt-1">
            {{ __('Při uložení bude adresa vytvořena jako propojený záznam.') }}
          </p>
        </div>
        <FieldLayout
          v-if="tabs.data?.length"
          :tabs="tabs.data"
          :data="organization.doc"
          doctype="CRM Organization"
        />
        <ErrorMessage v-if="error" class="mt-8" :message="__(error)" />
      </div>
      <div class="px-4 pt-4 pb-7 sm:px-6">
        <div class="space-y-2">
          <Button
            class="w-full"
            variant="solid"
            :label="__('Create')"
            :loading="loading"
            @click="createOrganization"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import FieldLayout from '@/components/FieldLayout/FieldLayout.vue'
import EditIcon from '@/components/Icons/EditIcon.vue'
import { usersStore } from '@/stores/users'
import { isMobileView } from '@/composables/settings'
import { showQuickEntryModal, quickEntryProps } from '@/composables/modals'
import { useDocument } from '@/data/document'
import { useDoctypeModal } from '@/composables/doctypeModal'
import { useTelemetry } from 'frappe-ui/frappe'
import { call, createResource, FormControl } from 'frappe-ui'
import { ref, nextTick, onMounted, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { useRouter } from 'vue-router'

const props = defineProps({
  data: { type: Object, default: () => ({}) },
  options: {
    type: Object,
    default: () => ({ redirect: true, afterInsert: () => {} }),
  },
})

const { isManager } = usersStore()
const { capture } = useTelemetry()

const router = useRouter()
const show = defineModel({ type: Boolean })

const loading = ref(false)
const error = ref(null)
const aresLoading = ref(false)
const aresStatus = ref('')
const aresMessage = ref('')
const aresAddress = ref(null)
const aresAddressDetails = ref(null)
const existingOrganization = ref(null)

function clearAresState() {
  aresStatus.value = ''
  aresMessage.value = ''
  existingOrganization.value = null
}

const lookupAresDebounced = useDebounceFn(() => {
  if (/^\d{8}$/.test(organization.doc.custom_ico || '')) lookupAres()
}, 500)

watch(
  () => organization.doc.custom_ico,
  (ico) => {
    clearAresState()
    aresAddressDetails.value = null
    if (/^\d{8}$/.test(ico || '')) lookupAresDebounced()
  },
)

async function lookupAres() {
  const requestedIco = organization.doc.custom_ico
  aresLoading.value = true
  clearAresState()
  try {
    const result = await call('crm.api.vitalage_ares.lookup_organization', {
      ico: requestedIco,
    })
    if (organization.doc.custom_ico !== requestedIco) return
    aresStatus.value = result.status
    const messages = {
      invalid_ico: 'Neplatné IČO. Zkontrolujte prosím zadané číslo.',
      not_found:
        'Subjekt nebyl nalezen v ARES. Zkontrolujte IČO nebo vyplňte údaje ručně.',
      unavailable:
        'ARES je momentálně nedostupný. Zkuste to prosím znovu nebo vyplňte údaje ručně.',
      incomplete:
        'Údaje z ARES nejsou kompletní. Zkontrolujte a doplňte chybějící informace.',
      existing: 'Organizace s tímto IČO již existuje.',
      ok: 'Údaje byly načteny z ARES. Před uložením je prosím zkontrolujte.',
    }
    aresMessage.value = messages[result.status] || messages.unavailable
    if (result.status === 'existing')
      existingOrganization.value = result.organization
    if (result.data) {
      organization.doc.organization_name =
        result.data.organization_name || organization.doc.organization_name
      organization.doc.custom_dic =
        result.data.custom_dic || organization.doc.custom_dic
      aresAddress.value = result.data.address_display || ''
      aresAddressDetails.value = result.data.address || null
    }
  } catch {
    if (organization.doc.custom_ico !== requestedIco) return
    aresStatus.value = 'unavailable'
    aresMessage.value =
      'ARES je momentálně nedostupný. Zkuste to prosím znovu nebo vyplňte údaje ručně.'
  } finally {
    aresLoading.value = false
  }
}

function chooseExistingOrganization() {
  if (!existingOrganization.value) return
  handleOrganizationUpdate({ name: existingOrganization.value })
}

const { document: organization, triggerOnBeforeCreate } =
  useDocument('CRM Organization')

const allowedOrganizationFields = [
  'organization_name',
  'custom_ico',
  'custom_dic',
  'no_of_employees',
  'currency',
  'exchange_rate',
  'annual_revenue',
  'website',
  'territory',
  'industry',
  'address',
  'organization_logo',
]

async function createOrganization() {
  if (loading.value) return
  loading.value = true
  error.value = null

  try {
    if (aresStatus.value === 'existing') {
      error.value = 'Organizace s tímto IČO již existuje.'
      return
    }
    await triggerOnBeforeCreate?.()
    const payload = Object.fromEntries(
      allowedOrganizationFields
        .filter((field) => organization.doc[field] !== undefined)
        .map((field) => [field, organization.doc[field]]),
    )
    const doc = await call(
      'crm.api.vitalage_organization.create_organization',
      {
        organization: payload,
        address_text: organization.doc.address ? null : aresAddress.value,
        address_details: aresAddressDetails.value,
      },
    )
    if (doc?.name) {
      capture('organization_created')
      handleOrganizationUpdate(doc)
      organization.doc = {}
    }
  } catch (err) {
    error.value =
      err?.error?.messages?.[0] ||
      err?.message ||
      'Organizaci se nepodařilo vytvořit.'
  } finally {
    loading.value = false
  }
}

function handleOrganizationUpdate(doc) {
  if (doc.name && props.options.redirect) {
    router.push({
      name: 'Organization',
      params: { organizationId: doc.name },
    })
  }
  show.value = false
  props.options.afterInsert?.(doc)
}

const tabs = createResource({
  url: 'crm.fcrm.doctype.crm_fields_layout.crm_fields_layout.get_fields_layout',
  cache: ['QuickEntry', 'CRM Organization'],
  params: { doctype: 'CRM Organization', type: 'Quick Entry' },
  auto: true,
  transform: (_tabs) => {
    return _tabs.forEach((tab) => {
      tab.sections.forEach((section) => {
        section.columns.forEach((column) => {
          column.fields.forEach((field) => {
            if (field.fieldname == 'address') {
              field.create = (value, close) => {
                organization.doc.address = value
                showAddressModal()
                close()
              }
              field.edit = (address) => showAddressModal(address)
            } else if (field.fieldtype === 'Table') {
              organization.doc[field.fieldname] = []
            }
          })
        })
      })
    })
  },
})

onMounted(() => {
  if (!props.data?.no_of_employees) {
    organization.doc.no_of_employees = '1-10'
  }
  Object.assign(organization.doc, props.data)
})

function openQuickEntryModal() {
  showQuickEntryModal.value = true
  quickEntryProps.value = { doctype: 'CRM Organization' }
  nextTick(() => (show.value = false))
}

const { showModal } = useDoctypeModal()

function showAddressModal(_address) {
  showModal({
    name: _address || null,
    doctype: 'Address',
    callbacks: {
      afterInsert: (d) => {
        capture('address_created')
        organization.doc.address = d.name
      },
    },
  })
}
</script>
