<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">{{ t('nav.skipToContent') }}</a>

    <div
      v-if="drawerOpen"
      class="drawer-backdrop"
      aria-hidden="true"
      @click="closeDrawer"
    ></div>

    <aside
      id="app-sidebar"
      ref="sidebarRef"
      class="sidebar"
      :class="{ open: drawerOpen, 'icon-only': iconOnly }"
    >
      <div class="brand">
        <!-- Monogram stands in for the brand text in icon-only mode (CSS swaps them). -->
        <div class="brand-mark" aria-hidden="true">{{ brandMonogram }}</div>
        <div class="brand-text">
          <div class="brand-name">{{ t('nav.companyName') }}</div>
          <div class="brand-subtitle">{{ t('nav.subtitle') }}</div>
        </div>
        <button
          ref="toggleRef"
          type="button"
          class="sidebar-toggle"
          aria-controls="app-sidebar"
          :aria-expanded="iconOnly ? 'false' : 'true'"
          :aria-label="t('nav.openMenu')"
          :title="t('nav.openMenu')"
          @click="toggleSidebar"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 4h16v16H4zM9 4v16" />
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav" aria-label="Main">
        <div v-for="group in navGroups" :key="group.id" class="nav-group">
          <div class="nav-group-label">{{ t(group.labelKey) }}</div>
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            :class="{ active: $route.path === item.to }"
            :aria-label="t(item.labelKey)"
            :title="iconOnly ? t(item.labelKey) : null"
          >
            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path :d="item.icon" />
            </svg>
            <span>{{ t(item.labelKey) }}</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div class="shell-body">
      <header class="page-bar">
        <h1 class="page-bar-title">{{ pageTitle }}</h1>
      </header>
      <FilterBar />
      <main id="main-content" ref="mainRef" class="main-content" tabindex="-1">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const route = useRoute()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    // Sidebar groups. Only routes that exist in main.js are listed (Backlog has no route).
    // Icon values are single SVG path strings so the nav stays a plain v-for.
    const navGroups = [
      {
        id: 'overview',
        labelKey: 'nav.groupOverview',
        items: [
          { to: '/', labelKey: 'nav.overview', icon: 'M3 12l9-9 9 9M5 10v10h5v-6h4v6h5V10' }
        ]
      },
      {
        id: 'operations',
        labelKey: 'nav.groupOperations',
        items: [
          { to: '/inventory', labelKey: 'nav.inventory', icon: 'M21 8l-9-5-9 5v8l9 5 9-5V8zM3 8l9 5 9-5M12 13v8' },
          { to: '/orders', labelKey: 'nav.orders', icon: 'M6 2l-2 4v14a2 2 0 002 2h12a2 2 0 002-2V6l-2-4H6zM4 6h16M9 10a3 3 0 006 0' },
          { to: '/restocking', labelKey: 'nav.restocking', icon: 'M21 12a9 9 0 11-3-6.7M21 4v5h-5' }
        ]
      },
      {
        id: 'planning',
        labelKey: 'nav.groupPlanning',
        items: [
          { to: '/demand', labelKey: 'nav.demandForecast', icon: 'M3 17l6-6 4 4 8-8M15 7h6v6' }
        ]
      },
      {
        id: 'finance',
        labelKey: 'nav.groupFinance',
        items: [
          { to: '/spending', labelKey: 'nav.finance', icon: 'M12 2v20M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6' },
          { to: '/reports', labelKey: 'nav.reports', icon: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zM14 2v6h6M8 13h8M8 17h8' }
        ]
      }
    ]

    const pageTitle = computed(() => {
      const match = navGroups.flatMap(g => g.items).find(i => i.to === route.path)
      return t(match ? match.labelKey : 'nav.companyName')
    })

    // Sidebar state. Below 1024px the sidebar is a permanent 64px icon rail that expands to
    // full width as an overlay (`drawerOpen`); the breakpoint is where sidebar (248px) + a wide
    // table no longer fit side by side, not a device size.
    // Keep this query in sync with the @media rule in the style block below.
    const SMALL_QUERY = '(max-width: 1023px)'
    // Desktop collapsed preference. Persisted because it is a layout preference the user set
    // deliberately; without it the sidebar would spring back to full width on every reload.
    const COLLAPSED_STORAGE_KEY = 'inventory.sidebar.collapsed'

    const readCollapsed = () => {
      try {
        return window.localStorage.getItem(COLLAPSED_STORAGE_KEY) === '1'
      } catch (e) {
        // Storage can throw (privacy mode, blocked cookies); fall back to expanded.
        return false
      }
    }

    const mediaQuery = window.matchMedia(SMALL_QUERY)
    // Read synchronously in setup so the first paint already has the right layout (no flash).
    const isSmall = ref(mediaQuery.matches)
    const collapsed = ref(readCollapsed())
    const drawerOpen = ref(false)
    const toggleRef = ref(null)
    const sidebarRef = ref(null)
    const mainRef = ref(null)

    // Small screens ignore the persisted desktop preference: the rail is the default and only
    // the transient overlay state expands it.
    const iconOnly = computed(() => (isSmall.value ? !drawerOpen.value : collapsed.value))

    // Initials of the company name; derived from the translated name so it follows the locale.
    const brandMonogram = computed(() =>
      t('nav.companyName').split(/\s+/).filter(Boolean).slice(0, 2).map(w => Array.from(w)[0]).join('').toUpperCase()
    )

    const openDrawer = async () => {
      drawerOpen.value = true
      await nextTick()
      // Move focus into the overlay so keyboard users land on the nav, not behind the backdrop.
      const first = sidebarRef.value && sidebarRef.value.querySelector('.nav-link')
      if (first) first.focus()
    }

    const closeDrawer = () => {
      if (!drawerOpen.value) return
      drawerOpen.value = false
      if (toggleRef.value) toggleRef.value.focus()
    }

    const toggleSidebar = () => {
      if (isSmall.value) {
        if (drawerOpen.value) closeDrawer()
        else openDrawer()
        return
      }
      collapsed.value = !collapsed.value
      try {
        window.localStorage.setItem(COLLAPSED_STORAGE_KEY, collapsed.value ? '1' : '0')
      } catch (e) {
        // Preference just won't persist; the toggle still works for this session.
      }
    }

    const onKeydown = (event) => {
      if (event.key === 'Escape') closeDrawer()
    }

    const onMediaChange = (event) => {
      isSmall.value = event.matches
      // Crossing the breakpoint: reset the overlay without stealing focus.
      drawerOpen.value = false
    }

    // The skip link is a plain anchor; intercept it so history-mode routing keeps the URL clean.
    const focusMain = () => {
      if (mainRef.value) mainRef.value.focus()
    }

    watch(() => route.path, () => closeDrawer())

    onMounted(() => {
      loadTasks()
      window.addEventListener('keydown', onKeydown)
      mediaQuery.addEventListener('change', onMediaChange)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('keydown', onKeydown)
      mediaQuery.removeEventListener('change', onMediaChange)
    })

    return {
      t,
      navGroups,
      pageTitle,
      drawerOpen,
      collapsed,
      iconOnly,
      brandMonogram,
      toggleRef,
      sidebarRef,
      mainRef,
      toggleSidebar,
      closeDrawer,
      focusMain,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>


<style>
:root {
  /* Spacing scale (4px base). Use only these in views. */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;
  --space-6: 32px;
  --space-7: 48px;

  /* Layout */
  --sidebar-width: 248px;
  --sidebar-collapsed: 64px;
  /* Width the grid actually reserves for the sidebar; overridden by .sidebar-collapsed and the small-screen rule. */
  --sidebar-current: var(--sidebar-width);
  --content-max: 1280px;
  --page-bar-height: 56px;
  --radius: 8px;

  /* Color: existing slate palette plus blue accent */
  --surface: #ffffff;
  --surface-muted: #f8fafc;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-muted: #64748b;
  --accent: #2563eb;
  --accent-tint: #eff6ff;

  /* Elevation: one soft shadow for cards and the drawer */
  --shadow: 0 1px 2px rgba(15, 23, 42, 0.06);

  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.5;
  background: var(--surface-muted);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3 {
  letter-spacing: -0.02em;
}

/* ---------- Shell ---------- */

/* minmax(0, 1fr): without the 0 minimum, wide tables push the content column off screen. */
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-current) minmax(0, 1fr);
  min-height: 100vh;
  transition: grid-template-columns 0.2s ease;
}

.app-shell.sidebar-collapsed {
  --sidebar-current: var(--sidebar-collapsed);
}

.skip-link {
  position: fixed;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 300;
  padding: var(--space-2) var(--space-4);
  background: var(--surface);
  color: var(--accent);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-weight: 600;
  text-decoration: none;
  transform: translateY(-200%);
}

.skip-link:focus {
  transform: translateY(0);
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  width: var(--sidebar-current);
  /* Above the sticky page bar (100) so footer dropdowns that extend past the rail are not hidden under it.
     The backdrop (150) only exists while the overlay is open, and .open raises the sidebar to 200. */
  z-index: 160;
  background: var(--surface);
  border-right: 1px solid var(--border);
  transition: width 0.2s ease;
}

/* Explicit column placement: on small screens the open sidebar is position: fixed and leaves the grid,
   which would otherwise let auto-placement slide .shell-body into the 64px rail column. */
.sidebar {
  grid-column: 1;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-5) var(--space-4) var(--space-4);
  white-space: nowrap;
}

.brand-mark {
  display: none;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  background: var(--accent);
  color: #ffffff;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.brand-text {
  min-width: 0;
  overflow: hidden;
}

/* The expanded sidebar can be narrower than the subtitle plus toggle; ellipsis beats a hard clip. */
.brand-name,
.brand-subtitle {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-toggle {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-muted);
  cursor: pointer;
}

.sidebar-toggle:hover {
  background: var(--surface-muted);
  color: var(--text);
}

.brand-name {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}

.brand-subtitle {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

/* Only the nav scrolls; the footer stays pinned so its dropdowns have room to open upward. */
.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-2) var(--space-3) var(--space-4);
  /* Labels are nowrap; clip them instead of scrolling sideways while the width animates. */
  overflow-x: hidden;
}

.nav-group + .nav-group {
  margin-top: var(--space-4);
}

.nav-group-label {
  padding: var(--space-1) var(--space-3);
  margin-bottom: var(--space-1);
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  color: #475569;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
  white-space: nowrap;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-link:hover {
  background: var(--surface-muted);
  color: var(--text);
}

.nav-link.active {
  background: var(--accent-tint);
  color: #1d4ed8;
}

/* 2px accent bar on the left edge marks the active page */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: calc(-1 * var(--space-3));
  top: var(--space-1);
  bottom: var(--space-1);
  width: 2px;
  background: var(--accent);
  border-radius: 2px;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--border);
}

.sidebar-footer .language-button,
.sidebar-footer .profile-button {
  width: 100%;
}

/* Footer sits at the bottom edge, so dropdowns open upward and match the sidebar width.
   Selectors are doubled-up to beat the child components' scoped rules. */
.sidebar-footer .language-switcher .dropdown-menu,
.sidebar-footer .profile-menu .dropdown-menu {
  top: auto;
  bottom: calc(100% + var(--space-2));
  left: 0;
  right: 0;
  min-width: 0;
  max-height: 70vh;
  overflow-y: auto;
}

.shell-body {
  grid-column: 2;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* Slim header: page title only; the sidebar toggle lives in the sidebar itself. */
.page-bar {
  position: sticky;
  top: 0;
  z-index: 100;
  height: var(--page-bar-height);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-5);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.page-bar-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
}

.nav-link:focus-visible,
.sidebar-toggle:focus-visible,
.skip-link:focus-visible,
.sidebar-footer button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.main-content {
  flex: 1;
  width: 100%;
  max-width: var(--content-max);
  margin: 0 auto;
  padding: var(--space-5);
}

.main-content:focus {
  outline: none;
}

.drawer-backdrop {
  display: none;
}

/* ---------- Icon-only mode ----------
   Applied by the .icon-only class: the desktop collapsed state, and the default state on small screens. */

.sidebar.icon-only .brand {
  flex-direction: column;
  padding: var(--space-4) var(--space-3) var(--space-3);
}

.sidebar.icon-only .brand-mark {
  display: flex;
}

.sidebar.icon-only .brand-text,
.sidebar.icon-only .nav-group-label,
.sidebar.icon-only .nav-link > span,
.sidebar.icon-only .language-label,
.sidebar.icon-only .profile-name,
.sidebar.icon-only .sidebar-footer .chevron {
  display: none;
}

/* Group labels are gone, so a hairline keeps the groups visually separate. */
.sidebar.icon-only .nav-group + .nav-group {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--border);
}

.sidebar.icon-only .nav-link {
  justify-content: center;
  height: 40px;
  padding: 0;
}

/* Triple-class selectors to beat the child components' scoped button padding. */
.sidebar.icon-only .sidebar-footer .language-button,
.sidebar.icon-only .sidebar-footer .profile-button {
  justify-content: center;
  height: 40px;
  padding: 0;
}

/* A 64px rail cannot hold the dropdowns, and the footer's overflow is visible, so open them to the
   right of the rail instead of matching its width. Bottom-aligned so they grow upward from the footer.
   The offset = footer padding + sidebar border + gap, measured from the 40px wrapper's right edge. */
.sidebar.icon-only .sidebar-footer .language-switcher .dropdown-menu,
.sidebar.icon-only .sidebar-footer .profile-menu .dropdown-menu {
  top: auto;
  bottom: 0;
  left: calc(100% + var(--space-3) + 1px + var(--space-2));
  right: auto;
  min-width: 200px;
  max-width: calc(100vw - var(--sidebar-collapsed) - var(--space-4));
}

.sidebar.icon-only .sidebar-footer .profile-menu .dropdown-menu {
  min-width: 260px;
}

/* Breakpoint is where the 248px sidebar plus a wide table stops fitting, not a device size.
   Keep in sync with SMALL_QUERY in the script. */
@media (max-width: 1023px) {
  /* The grid always reserves only the rail; the expanded sidebar overlays the content instead of pushing it. */
  .app-shell,
  .app-shell.sidebar-collapsed {
    --sidebar-current: var(--sidebar-collapsed);
  }

  .sidebar.open {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 200;
    width: var(--sidebar-width);
    box-shadow: var(--shadow);
  }

  .drawer-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: 150;
    background: rgba(15, 23, 42, 0.4);
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition: none !important;
    animation: none !important;
  }
}

/* ---------- Shared page components ---------- */

.page-header {
  margin-bottom: var(--space-5);
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.02em;
}

.page-header p {
  color: var(--text-muted);
  font-size: 0.9375rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  background: var(--surface);
  padding: var(--space-5);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  transition: border-color 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
}

.stat-label {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.02em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: var(--surface);
  border-radius: var(--radius);
  padding: var(--space-5);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--surface-muted);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--surface-muted);
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: var(--space-7);
  color: var(--text-muted);
  font-size: 0.9375rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: var(--space-4);
  border-radius: var(--radius);
  margin: var(--space-4) 0;
  font-size: 0.9375rem;
}
</style>
