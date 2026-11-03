<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

const budget = ref(20000)
const recommendation = ref({ budget: 0, spent: 0, remaining: 0, items: [] })
const loading = ref(true)
const error = ref(null)

const submitting = ref(false)
const orderError = ref(null)
const confirmation = ref(null)

const items = computed(() => recommendation.value.items)
const canSubmit = computed(() => items.value.length > 0 && !submitting.value && !loading.value)

const money = (amount) => formatCurrency(amount, currentCurrency.value)
const moneyExact = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

// Guards against out-of-order responses: only the latest request may update state.
let requestId = 0

const loadRecommendations = async () => {
  const id = ++requestId
  loading.value = true
  error.value = null
  try {
    const data = await api.getRestockRecommendations(budget.value)
    if (id !== requestId) return
    recommendation.value = data
  } catch (err) {
    if (id !== requestId) return
    error.value = t('restocking.loadError')
    console.error('Failed to load recommendations:', err)
  } finally {
    if (id === requestId) loading.value = false
  }
}

// Debounce: a range input fires on every step while dragging, so wait until the
// user pauses (300ms) before hitting the API.
let debounceTimer = null
watch(budget, () => {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(loadRecommendations, 300)
})

const formatDate = (dateString) => {
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return '-'
  return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

const placeOrder = async () => {
  if (!canSubmit.value) return
  submitting.value = true
  orderError.value = null
  confirmation.value = null
  try {
    // The server only needs SKU and quantity; it re-derives names and prices itself,
    // so we don't send client-computed costs.
    const payload = items.value.map(({ sku, quantity }) => ({ sku, quantity }))
    const order = await api.placeRestockOrder(payload)
    confirmation.value = {
      orderNumber: order.order_number,
      expectedDelivery: formatDate(order.expected_delivery)
    }
    // Stock/demand context changed, so refresh the recommendation view.
    await loadRecommendations()
  } catch (err) {
    orderError.value = t('restocking.orderError')
    console.error('Failed to place order:', err)
  } finally {
    submitting.value = false
  }
}

onMounted(loadRecommendations)
onBeforeUnmount(() => clearTimeout(debounceTimer))
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <label for="budget-slider" class="budget-label">{{ t('restocking.budget') }}</label>
      <div class="budget-value">{{ money(budget) }}</div>
      <input
        id="budget-slider"
        v-model.number="budget"
        type="range"
        min="0"
        max="50000"
        step="500"
        class="budget-slider"
      />
    </div>

    <div v-if="confirmation" class="success-message" role="status">
      {{ t('restocking.orderSuccess', { orderNumber: confirmation.orderNumber, date: confirmation.expectedDelivery }) }}
    </div>
    <div v-if="orderError" class="error">{{ orderError }}</div>

    <div v-if="loading && items.length === 0 && !error" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(recommendation.budget) }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.spent') }}</div>
          <div class="stat-value">{{ money(recommendation.spent) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ money(recommendation.remaining) }}</div>
        </div>
      </div>

      <div class="card" :class="{ stale: loading }">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ items.length }})</h3>
          <button class="place-order-btn" :disabled="!canSubmit" @click="placeOrder">
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="items.length === 0" class="empty-state">{{ t('restocking.noItems') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.forecastedDemand') }}</th>
                <th class="num">{{ t('restocking.table.onHand') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in items" :key="item.sku">
                <td><strong>{{ item.sku }}</strong></td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td class="num">{{ item.forecasted_demand.toLocaleString() }}</td>
                <td class="num">{{ item.on_hand.toLocaleString() }}</td>
                <td class="num"><strong>{{ item.quantity.toLocaleString() }}</strong></td>
                <td class="num">{{ moneyExact(item.unit_cost) }}</td>
                <td class="num"><strong>{{ moneyExact(item.cost) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-card {
  max-width: 640px;
}

.budget-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
}

.budget-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
  margin: var(--space-1) 0 var(--space-3);
}

.budget-slider {
  width: 100%;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: none;
  border-radius: 8px;
  padding: var(--space-2) var(--space-4);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  cursor: not-allowed;
}

.success-message {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  padding: var(--space-4);
  border-radius: 8px;
  margin: var(--space-4) 0;
  font-size: 0.938rem;
}

.empty-state {
  padding: var(--space-5);
  text-align: center;
  color: #64748b;
}

.stale {
  opacity: 0.6;
}

.num {
  text-align: right;
}
</style>
