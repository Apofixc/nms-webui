<template>
  <div class="p-6 w-full flex flex-col lg:flex-row gap-6 text-on-surface animate-fade-in relative">
    <!-- Toast Notification & Confirm Modal -->
    <ToastNotification />
    <ConfirmModal />



    <!-- Mandatory Password Change Alert Banner -->
    <div v-if="mustChangeBanner && authEnabled" class="w-full bg-error-container/20 border border-error/40 text-error p-4 rounded-xl flex items-center gap-3 shadow-glow font-mono text-xs mb-2">
      <span class="material-symbols-outlined text-lg">warning</span>
      <span>{{ t('mfaMandatoryPasswordBanner') }}</span>
    </div>

    <!-- Left Column -->
    <div class="lg:w-1/3 flex flex-col gap-6">
      <!-- Avatar Card -->
      <div class="bg-surface-container-high border border-outline-variant rounded-lg p-6 shadow-glow backdrop-blur-sm flex flex-col items-center text-center">
        <div class="relative mb-4">
          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            class="hidden"
            @change="onFileSelected"
          />
          <div
            v-if="avatarUrl"
            class="w-32 h-32 rounded-full border-2 border-primary overflow-hidden shadow-glow flex items-center justify-center bg-surface-container-highest"
          >
            <img :src="avatarUrl" alt="Avatar" class="w-full h-full object-cover" />
          </div>
          <div
            v-else
            class="w-32 h-32 rounded-full border-2 border-primary bg-primary/20 flex items-center justify-center text-primary font-mono font-bold text-3xl shadow-glow uppercase select-none"
          >
            {{ initials }}
          </div>
          <div
            class="absolute bottom-0 right-0 w-4 h-4 rounded-full border-2 border-surface-container-high transition-colors"
            :class="!isSessionTerminated ? 'bg-emerald-400' : 'bg-error'"
            :title="!isSessionTerminated ? t('active') : t('sessionTerminated')"
          />
        </div>

        <h2 class="font-bold text-lg text-on-surface mb-0.5">{{ fullName || username || '—' }}</h2>
        <p class="text-on-surface-variant font-semibold text-xs mb-1">{{ roleTitle }}</p>
        <p class="text-on-surface-variant/70 font-mono text-[11px] mb-4">UID: {{ uid || '—' }}</p>

        <div class="w-full flex justify-between items-center bg-surface-container p-2.5 rounded mb-4 border border-outline-variant text-xs font-mono">
          <span class="text-on-surface-variant">{{ t('status') }}: 
            <span v-if="!isSessionTerminated" class="text-emerald-400 font-bold">{{ t('active') }}</span>
            <span v-else class="text-error font-bold">{{ t('sessionTerminated') }}</span>
          </span>
          <span class="text-on-surface-variant text-[11px]">{{ currentTime }}</span>
        </div>

        <div class="flex w-full gap-2 text-xs">
          <button
            @click="triggerUpload"
            class="flex-1 bg-secondary-container text-on-surface py-2 px-3 rounded hover:bg-surface-bright transition-colors font-semibold border border-outline-variant flex items-center justify-center gap-1 cursor-pointer"
          >
            <span class="material-symbols-outlined text-[16px]">upload</span>
            {{ t('upload') }}
          </button>
          <button
            @click="handleResetAvatar"
            class="flex-1 bg-transparent text-error py-2 px-3 rounded hover:bg-error/10 transition-colors font-semibold border border-outline-variant flex items-center justify-center gap-1 cursor-pointer"
          >
            <span class="material-symbols-outlined text-[16px]">restart_alt</span>
            {{ t('reset') }}
          </button>
        </div>
      </div>

      <!-- Security Settings Card -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow">
        <h3 class="font-semibold text-sm text-on-surface mb-4 pb-2 border-b border-outline-variant flex items-center gap-2">
          <span class="material-symbols-outlined text-[18px]">security</span>
          <span>{{ t('securityPolicies') }}</span>
        </h3>

        <div v-if="!authEnabled" class="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded text-xs leading-relaxed flex items-start gap-2">
          <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5">info</span>
          <span>{{ t('authDisabledBannerProfile') }}</span>
        </div>

        <template v-else>
          <!-- Status / Error Banner -->
          <div
            v-if="statusMessage"
            class="mb-4 p-2.5 rounded text-xs font-mono flex items-center gap-2"
            :class="isError ? 'bg-error/15 text-error border border-error/30' : 'bg-tertiary/15 text-tertiary border border-tertiary/30'"
          >
            <span class="material-symbols-outlined text-[16px]">{{ isError ? 'warning' : 'check_circle' }}</span>
            <span>{{ statusMessage }}</span>
          </div>

          <form @submit.prevent="handleChangePassword" class="flex flex-col gap-4 text-xs">
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('currentPassword') }}</label>
              <input
                v-model="oldPassword"
                type="password"
                required
                class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('newPassword') }}</label>
              <input
                v-model="newPassword"
                type="password"
                required
                class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
              <div v-if="newPassword" class="flex items-center gap-2 mt-1 font-mono text-[10px]">
                <span class="text-on-surface-variant">{{ t('pwdStrength') }}:</span>
                <div class="flex gap-1 h-1.5 flex-1 max-w-[120px]">
                  <div class="h-full flex-1 rounded transition-colors" :class="passwordStrength.score >= 1 ? passwordStrength.color : 'bg-surface-variant'" />
                  <div class="h-full flex-1 rounded transition-colors" :class="passwordStrength.score >= 2 ? passwordStrength.color : 'bg-surface-variant'" />
                  <div class="h-full flex-1 rounded transition-colors" :class="passwordStrength.score >= 3 ? passwordStrength.color : 'bg-surface-variant'" />
                </div>
                <span :class="passwordStrength.textColor" class="font-bold">{{ passwordStrength.label }}</span>
              </div>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('confirmPassword') }}</label>
              <input
                v-model="confirmPassword"
                type="password"
                required
                class="bg-surface-container-highest text-on-surface font-mono px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
            <button
              type="submit"
              class="bg-surface-variant text-on-surface py-2 px-3 rounded hover:bg-surface-bright transition-colors font-semibold border border-outline-variant mt-2 cursor-pointer flex items-center justify-center gap-1"
            >
              <span class="material-symbols-outlined text-[16px]">lock_reset</span>
              {{ t('changePassword') }}
            </button>
          </form>
        </template>
      </div>

      <!-- 2FA / MFA Card -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow">
        <h3 class="font-semibold text-sm text-on-surface mb-2 pb-2 border-b border-outline-variant flex items-center justify-between">
          <span class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[18px] text-primary">verified_user</span>
            <span>{{ t('mfaTitle') }}</span>
          </span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase" :class="mfaEnabled && authEnabled ? 'bg-tertiary/20 text-tertiary border border-tertiary/30' : 'bg-surface-variant text-on-surface-variant border border-outline-variant'">
            {{ mfaEnabled && authEnabled ? t('mfaEnabled') : t('mfaDisabled') }}
          </span>
        </h3>

        <div v-if="!authEnabled" class="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded text-xs leading-relaxed flex items-start gap-2 my-2">
          <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5">info</span>
          <span>{{ t('authDisabledBannerProfile') }}</span>
        </div>

        <template v-else>
          <p class="text-xs text-on-surface-variant leading-relaxed my-3">
            {{ t('mfaDescription') }}
          </p>

          <div class="pt-1">
            <button
              v-if="!mfaEnabled"
              @click="openMfaSetupModal"
              class="w-full bg-primary text-on-primary py-2 px-3 rounded hover:bg-primary-container transition-colors font-semibold shadow-glow cursor-pointer text-xs flex items-center justify-center gap-1.5"
            >
              <span class="material-symbols-outlined text-[16px]">qr_code_2</span>
              <span>{{ t('mfaSetupBtn') }}</span>
            </button>
            <div v-else class="space-y-1.5">
              <button
                @click="handleDisableMfa"
                :disabled="forceMfa"
                class="w-full py-2 px-3 rounded font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                :class="forceMfa ? 'bg-surface-variant text-on-surface-variant cursor-not-allowed opacity-70 border border-outline-variant' : 'bg-error/15 text-error border border-error/30 hover:bg-error/25 cursor-pointer'"
              >
                <span class="material-symbols-outlined text-[16px]">no_encryption</span>
                <span>{{ t('mfaDisableBtn') }}</span>
              </button>
              <p v-if="forceMfa" class="text-[10px] text-tertiary font-mono text-center">
                {{ t('mfaEnforcedPolicy') }}
              </p>
            </div>
          </div>
        </template>
      </div>
    </div>


    <!-- Right Column -->
    <div class="lg:w-2/3 flex flex-col gap-6">
      <!-- Personal Information -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">{{ t('personalInfo') }}</h2>
        <form @submit.prevent="saveProfile" class="flex flex-col gap-4">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('fullName') }}</label>
              <input
                v-model="fullName"
                type="text"
                required
                class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">
                {{ t('department') }}
                <span class="text-on-surface-variant/50 lowercase text-[9px]">{{ t('readonlyField') }}</span>
              </label>
              <input
                v-model="department"
                type="text"
                readonly
                disabled
                class="bg-surface-container-highest/50 text-on-surface-variant font-mono text-xs px-3 py-2 rounded border border-outline-variant/60 cursor-not-allowed"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">
                {{ t('role') }}
                <span class="text-on-surface-variant/50 lowercase text-[9px]">{{ t('readonlyField') }}</span>
              </label>
              <input
                :value="roleTitle"
                type="text"
                readonly
                disabled
                class="bg-surface-container-highest/50 text-on-surface-variant font-mono text-xs px-3 py-2 rounded border border-outline-variant/60 cursor-not-allowed"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('emailAddress') }}</label>
              <input
                v-model="email"
                type="email"
                class="bg-surface-container-highest text-on-surface font-mono text-xs px-3 py-2 rounded border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>
          </div>
          <div class="flex justify-end pt-2">
            <button
              type="submit"
              :disabled="isSaving || !isProfileDirty"
              class="bg-primary text-on-primary font-semibold text-xs px-6 py-2 rounded transition-colors shadow-glow flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
              :class="!isSaving && isProfileDirty ? 'cursor-pointer hover:bg-primary-container' : ''"
            >
              <span v-if="isSaving" class="animate-spin material-symbols-outlined text-[16px]">progress_activity</span>
              <span v-else class="material-symbols-outlined text-[16px]">save</span>
              {{ t('saveChanges') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Appearance & Regionality -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant">{{ t('appearanceRegionality') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <div class="h-5 flex items-center">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('theme') }}</label>
            </div>
            <select
              v-model="selectedTheme"
              class="w-full h-9 bg-white text-slate-900 font-mono text-xs px-3 rounded border border-outline-variant focus:outline-none focus:border-primary transition-all"
            >
              <option value="system">{{ t('themeSystem') }}</option>
              <option value="dark">{{ t('themeDark') }}</option>
              <option value="light">{{ t('themeLight') }}</option>
            </select>
          </div>
          <div class="flex flex-col gap-1">
            <div class="h-5 flex items-center">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('language') }}</label>
            </div>
            <select
              :value="lang"
              @change="onLangChange"
              class="w-full h-9 bg-white text-slate-900 font-mono text-xs px-3 rounded border border-outline-variant focus:outline-none focus:border-primary transition-all"
            >
              <option value="ru">{{ t('langRu') }}</option>
              <option value="en">{{ t('langEn') }}</option>
            </select>
          </div>

          <!-- Timezone Picker -->
          <div class="flex flex-col gap-1">
            <div class="h-5 flex justify-between items-center">
              <label class="text-on-surface-variant font-mono text-[10px] uppercase tracking-wider font-bold">{{ t('timezone') }}</label>
              <button
                type="button"
                @click="detectSystemTimezone"
                class="text-[10px] text-primary hover:underline font-mono cursor-pointer flex items-center gap-0.5"
                :title="t('autoDetectBrowser')"
              >
                <span class="material-symbols-outlined text-[12px]">my_location</span>
                {{ t('autoDetect') }}
              </button>
            </div>
            <select
              v-model="selectedTimezone"
              class="w-full h-9 bg-white text-slate-900 font-mono text-xs px-3 rounded border border-outline-variant focus:outline-none focus:border-primary transition-all cursor-pointer"
            >
              <option v-for="tz in availableTimezones" :key="tz" :value="tz">{{ tz }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Notification Preferences -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <h2 class="font-bold text-base text-on-surface pb-2 border-b border-outline-variant flex items-center justify-between">
          <span>{{ t('notificationSettings') }}</span>
          <span class="material-symbols-outlined text-[20px] text-primary">notifications_active</span>
        </h2>
        <p class="text-on-surface-variant text-xs">{{ t('notificationSettingsSub') }}</p>

        <!-- Module Subscriptions -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <h3 class="text-xs font-bold text-on-surface">{{ t('moduleSubscriptions') }}</h3>
            <button
              v-if="notifSubscribedModules !== null"
              @click="resetModulesToAll"
              class="text-[11px] text-primary hover:underline cursor-pointer flex items-center gap-1 font-medium"
            >
              <span class="material-symbols-outlined text-[14px]">restart_alt</span>
              {{ t('subscribedAllModules') }}
            </button>
          </div>
          <p class="text-[10px] text-on-surface-variant mb-3">{{ t('moduleSubscriptionsSub') }}</p>

          <div class="space-y-2">
            <div
              v-for="mod in availableModules"
              :key="mod.id"
              class="flex flex-col sm:flex-row sm:items-center justify-between p-2.5 bg-surface-container-highest/30 border border-outline-variant/50 rounded-lg gap-2"
            >
              <div class="flex items-center gap-2.5">
                <input
                  type="checkbox"
                  :checked="isModuleSubscribed(mod.id)"
                  :disabled="mod.id === 'core'"
                  @change="toggleModuleSubscription(mod.id)"
                  class="rounded border-outline-variant text-primary focus:ring-primary h-4 w-4 cursor-pointer disabled:opacity-60"
                />
                <div>
                  <div class="flex items-center gap-1.5">
                    <span class="font-semibold text-xs text-on-surface">{{ mod.name }}</span>
                    <span class="text-[10px] px-1.5 py-0.2 bg-surface-variant text-on-surface-variant rounded font-mono">{{ mod.id }}</span>
                  </div>
                  <p v-if="mod.description" class="text-[10px] text-on-surface-variant/80 mt-0.5">{{ mod.description }}</p>
                </div>
              </div>

              <div class="flex items-center gap-2 self-end sm:self-center">
                <label class="text-[10px] text-on-surface-variant whitespace-nowrap">{{ t('minSeverity') }}:</label>
                <select
                  :value="notifModuleRules[mod.id]?.min_severity || 'info'"
                  @change="setModuleMinSeverity(mod.id, ($event.target as HTMLSelectElement).value)"
                  :disabled="!isModuleSubscribed(mod.id)"
                  class="text-[11px] bg-surface-container-high border border-outline-variant rounded px-2 py-1 text-on-surface focus:outline-none focus:border-primary disabled:opacity-50 cursor-pointer"
                >
                  <option value="info">{{ t('severityAll') }}</option>
                  <option value="warning">{{ t('severityWarning') }}</option>
                  <option value="error">{{ t('severityError') }}</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Sessions -->
      <div class="bg-surface-container-low border border-outline-variant rounded-lg p-6 shadow-glow space-y-4">
        <div class="flex justify-between items-center pb-2 border-b border-outline-variant">
          <div>
            <h2 class="font-bold text-base text-on-surface">{{ t('activeSessions') }}</h2>
            <p class="text-on-surface-variant text-xs">{{ t('terminateSessionsSub') }}</p>
          </div>
          <div v-if="authEnabled" class="flex items-center gap-2">
            <button
              @click="handleTerminateOtherSessions"
              class="bg-tertiary/20 text-tertiary hover:bg-tertiary/30 border border-tertiary/40 font-semibold text-xs px-3 py-1.5 rounded transition-colors flex items-center gap-1 cursor-pointer"
              :title="t('terminateOthersTitle')"
            >
              <span class="material-symbols-outlined text-[16px]">shield_lock</span>
              {{ t('terminateOthersBtn') }}
            </button>
            <button
              @click="handleTerminateAllSessions"
              class="bg-error/20 text-error hover:bg-error/30 border border-error/40 font-semibold text-xs px-3 py-1.5 rounded transition-colors flex items-center gap-1 cursor-pointer"
              :title="t('terminateAllLogoutTitle')"
            >
              <span class="material-symbols-outlined text-[16px]">logout</span>
              {{ t('terminateAllLogoutBtn') }}
            </button>
          </div>
        </div>

        <div v-if="!authEnabled" class="p-3 bg-amber-500/10 border border-amber-500/30 text-amber-300 rounded text-xs leading-relaxed flex items-start gap-2">
          <span class="material-symbols-outlined text-base flex-shrink-0 mt-0.5">info</span>
          <span>{{ t('authDisabledBannerProfile') }}</span>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr class="border-b border-outline-variant text-on-surface-variant uppercase tracking-wider text-[11px]">
                <th class="py-2.5 px-3">{{ t('ipAddress') }}</th>
                <th class="py-2.5 px-3">{{ t('deviceBrowser') }}</th>
                <th class="py-2.5 px-3">{{ t('lastSeen') }}</th>
                <th class="py-2.5 px-3 text-right">{{ t('actions') }}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant/50 text-on-surface">
              <tr v-if="isMySessionsLoading">
                <td colspan="4" class="py-4 text-center text-xs text-on-surface-variant">
                  {{ t('loadingText') }}
                </td>
              </tr>
              <tr v-else-if="mySessions.length === 0">
                <td colspan="4" class="py-4 text-center text-xs text-on-surface-variant">
                  {{ t('noActiveOtherSessions') }}
                </td>
              </tr>
              <tr v-else v-for="sess in mySessions" :key="sess.id" class="hover:bg-surface-variant/30 transition-colors">
                <td class="py-2.5 px-3 font-bold text-primary">
                  <div class="flex items-center gap-1.5">
                    <span>{{ sess.ip_address || 'local' }}</span>
                    <span v-if="sess.is_current" class="px-1.5 py-0.5 rounded bg-tertiary/20 text-tertiary text-[10px] font-semibold border border-tertiary/30">
                      {{ t('sessionCurrentBadge') }}
                    </span>
                  </div>
                </td>
                <td class="py-2.5 px-3 max-w-[200px] truncate" :title="sess.user_agent">{{ parseUserAgent(sess.user_agent) }}</td>
                <td class="py-2.5 px-3 text-on-surface-variant">{{ formatTime(sess.last_seen) }}</td>
                <td class="py-2.5 px-3 text-right">
                  <button
                    @click="revokeMySessionItem(sess)"
                    class="px-2 py-1 rounded bg-error/15 text-error border border-error/30 hover:bg-error/25 text-[11px] font-bold cursor-pointer"
                  >
                    {{ t('sessionRevokeBtn') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>


    </div>

    <!-- Modal: Setup 2FA / MFA -->
    <div v-if="isMfaModalOpen" class="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-surface-container-low border border-outline-variant rounded-xl p-6 w-full max-w-md shadow-glow space-y-4">
        <div class="flex items-center justify-between border-b border-outline-variant/60 pb-3">
          <h3 class="font-bold text-base text-on-surface flex items-center gap-2">
            <span class="material-symbols-outlined text-primary">qr_code_2</span>
            <span>{{ t('mfaSetupBtn') }}</span>
          </h3>
          <button @click="isMfaModalOpen = false" class="text-on-surface-variant hover:text-on-surface cursor-pointer">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>

        <div class="space-y-4 text-xs text-on-surface">
          <p class="text-on-surface-variant leading-relaxed">
            {{ t('scanQrInstruction') }}
          </p>

          <div v-if="mfaQrCode" class="flex justify-center p-2">
            <img :src="mfaQrCode" alt="QR Code" class="w-48 h-48 rounded-lg shadow-glow border border-outline-variant/40" />
          </div>

          <div class="bg-surface-container-highest p-3 rounded border border-outline-variant/40 space-y-1">
            <span class="text-[10px] font-mono uppercase text-outline block">{{ t('mfaSecretKey') }}</span>
            <code class="font-mono font-bold text-primary text-sm select-all break-all block">{{ mfaSecret }}</code>
          </div>

          <div class="space-y-1.5 pt-2">
            <label class="block font-mono text-[11px] uppercase font-bold text-on-surface-variant">
              2. {{ t('mfaEnterCodeToConfirm') }}
            </label>
            <input
              v-model="mfaConfirmCode"
              type="text"
              maxlength="6"
              placeholder="000000"
              class="w-full bg-surface-container-high border border-outline-variant rounded px-3 py-2 text-center text-base font-mono font-bold text-on-surface tracking-widest outline-none focus:border-primary"
            />
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-outline-variant/60">
            <button
              type="button"
              @click="isMfaModalOpen = false"
              class="px-4 py-2 rounded bg-surface-variant text-on-surface-variant font-semibold hover:bg-surface-bright cursor-pointer"
            >
              {{ t('cancel') }}
            </button>
            <button
              type="button"
              @click="confirmEnableMfa"
              :disabled="mfaConfirmCode.length !== 6 || isMfaSaving"
              class="px-4 py-2 rounded bg-primary text-on-primary font-semibold shadow-glow hover:bg-primary-container disabled:opacity-50 cursor-pointer"
            >
              {{ t('mfaEnableBtn') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n, type Language } from '@/core/i18n'
import { getStoredUser, clearAuthSession, updateStoredUser, isAuthEnabled } from '@/core/auth'
import { getStoredTheme, setStoredTheme, type ThemeMode } from '@/core/theme'
import { useToast } from '@/composables/useToast'
import ToastNotification from '@/components/ToastNotification.vue'
import { useConfirm } from '@/composables/useConfirm'
import ConfirmModal from '@/components/ConfirmModal.vue'
import { useDirtyGuard } from '@/composables/useDirtyGuard'

import {
  apiChangePassword,
  apiGetMe,
  apiLogout,
  apiTerminateSessions,
  apiUpdateMe,
  apiSetupMfa,
  apiEnableMfa,
  apiDisableMfa,
  apiFetchMySessions,
  apiRevokeMySession,
  apiFetchNotificationPreferences,
  apiUpdateNotificationPreferences,
  apiFetchNotificationModules,
  type NotificationModuleInfo,
} from '@/core/api'

const route = useRoute()
const router = useRouter()
const { lang, setLanguage, t, getRoleTitle, translateApiError, formatDateTime, formatTime: i18nFormatTime } = useI18n()
const { showToast } = useToast()
const { showConfirm } = useConfirm()

const authEnabled = computed(() => isAuthEnabled())



let clockTimer: ReturnType<typeof setInterval> | null = null

function parseUserAgent(ua: string): string {
  if (!ua) return t('browserSession')
  let browser = ''
  if (ua.includes('Firefox/')) browser = 'Firefox'
  else if (ua.includes('Edg/')) browser = 'Edge'
  else if (ua.includes('Chrome/')) browser = 'Chrome'
  else if (ua.includes('Safari/')) browser = 'Safari'
  else browser = 'Browser'

  let os = ''
  if (ua.includes('Windows')) os = 'Windows'
  else if (ua.includes('Mac OS') || ua.includes('Macintosh')) os = 'macOS'
  else if (ua.includes('Android')) os = 'Android'
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS'
  else if (ua.includes('Linux')) os = 'Linux'
  else os = 'OS'

  return `${browser} (${os})`
}

// Active Sessions State
interface MySessionItem {
  id: string
  ip_address: string
  user_agent: string
  created_at: string
  last_seen: string
  is_current?: boolean
}

const mySessions = ref<MySessionItem[]>([])
const isMySessionsLoading = ref(false)

async function loadMySessions() {
  isMySessionsLoading.value = true
  try {
    mySessions.value = await apiFetchMySessions()
  } catch (err) {
    console.error('Failed to load my sessions:', err)
  } finally {
    isMySessionsLoading.value = false
  }
}

async function revokeMySessionItem(sess: MySessionItem) {
  if (sess.is_current) {
    const confirmed = await showConfirm({
      title: t('sessionRevokeBtn'),
      message: t('terminateCurrentRevokeConfirm'),
      isDanger: true,
    })
    if (!confirmed) return
    try {
      await apiRevokeMySession(sess.id)
    } catch {}
    clearAuthSession()
    router.push('/login')
    return
  }
  try {
    await apiRevokeMySession(sess.id)
    showToast(t('sessionRevoked'))
    await loadMySessions()
  } catch (err: any) {
    showToast(err?.response?.data?.detail || t('errorRevokingSession'), true)
  }
}

function formatTime(ts: string) {
  if (!ts) return ''
  let s = String(ts).trim()
  if (/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d+)?$/.test(s)) {
    s = s.replace(' ', 'T') + 'Z'
  }
  try {
    return formatDateTime(s, { timeZone: selectedTimezone.value })
  } catch {
    return formatDateTime(s)
  }
}

// Form & Profile State
const fullName = ref('')
const username = ref('')
const email = ref('')
const role = ref('')
const uid = ref('')
const avatarUrl = ref('')
const department = ref('Network Operations')

const initialFullName = ref('')
const initialEmail = ref('')

const isProfileDirty = computed(() => {
  return fullName.value.trim() !== initialFullName.value.trim() || email.value.trim() !== initialEmail.value.trim()
})

useDirtyGuard(isProfileDirty)


const roleTitle = computed(() => getRoleTitle(role.value) || role.value || t('defaultUserRole'))

// MFA / 2FA State
const mfaEnabled = ref(false)
const forceMfa = ref(false)
const isMfaModalOpen = ref(false)
const mfaSecret = ref('')
const mfaQrCode = ref('')
const mfaConfirmCode = ref('')
const isMfaSaving = ref(false)

async function openMfaSetupModal() {
  mfaConfirmCode.value = ''
  try {
    const res = await apiSetupMfa()
    mfaSecret.value = res.secret
    mfaQrCode.value = res.qr_code
    isMfaModalOpen.value = true
  } catch (err: any) {
    showToast(err?.response?.data?.detail || t('errorSettingUpMfa'), true)
  }
}

async function confirmEnableMfa() {
  isMfaSaving.value = true
  try {
    await apiEnableMfa(mfaSecret.value, mfaConfirmCode.value)
    mfaEnabled.value = true
    isMfaModalOpen.value = false
    showToast(t('mfaSuccessEnabledToast'))
  } catch (err: any) {
    showToast(err?.response?.data?.detail || t('invalid2faCode'), true)
  } finally {
    isMfaSaving.value = false
  }
}

async function handleDisableMfa() {
  const confirmed = await showConfirm({
    title: t('mfaDisableBtn'),
    message: t('mfaConfirmDisableQuestion'),
    isDanger: true,
  })
  if (confirmed) {
    try {
      await apiDisableMfa()
      mfaEnabled.value = false
      showToast(t('mfaDisabledToast'))
    } catch (err: any) {
      showToast(err?.response?.data?.detail || t('errorDisablingMfa'), true)
    }
  }
}

// Password State
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const statusMessage = ref('')
const isError = ref(false)
const mustChangeBanner = ref(false)

const passwordStrength = computed(() => {
  const pwd = newPassword.value
  if (!pwd) return { score: 0, label: '', color: '', textColor: '' }
  let score = 0
  if (pwd.length >= 8) score++
  if (/[A-Z]/.test(pwd) || /[0-9]/.test(pwd)) score++
  if (/[^A-Za-z0-9]/.test(pwd) && pwd.length >= 10) score++
  
  if (score <= 1) return { score: 1, label: t('pwdWeak'), color: 'bg-error', textColor: 'text-error' }
  if (score === 2) return { score: 2, label: t('pwdMedium'), color: 'bg-amber-500', textColor: 'text-amber-400' }
  return { score: 3, label: t('pwdStrong'), color: 'bg-emerald-500', textColor: 'text-emerald-400' }
})

// UI Feedback
const isSaving = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const isSessionTerminated = ref(false)


// Session info
const userIp = ref('127.0.0.1')
const userAgent = ref('Browser Session')
const loginTime = ref('14:32 UTC')
const currentTime = ref('14:32:11 UTC')

// Appearance settings
const selectedTheme = ref<ThemeMode>(getStoredTheme())
const selectedTimezone = ref(localStorage.getItem('nms_timezone') || Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC')
const availableTimezones = ref<string[]>([])

function initTimezones() {
  let list: string[] = []
  try {
    if (typeof Intl !== 'undefined' && 'supportedValuesOf' in Intl) {
      list = (Intl as any).supportedValuesOf('timeZone')
    }
  } catch {}
  if (!list.length) {
    list = [
      'UTC', 'Europe/Minsk', 'Europe/Moscow', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
      'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Dubai', 'Asia/Almaty', 'Asia/Tashkent',
      'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles', 'Australia/Sydney'
    ]
  }
  if (selectedTimezone.value && !list.includes(selectedTimezone.value)) {
    list.unshift(selectedTimezone.value)
  }
  availableTimezones.value = list
}

function detectSystemTimezone() {
  try {
    const sysTz = Intl.DateTimeFormat().resolvedOptions().timeZone
    if (sysTz) {
      selectedTimezone.value = sysTz
      showToast(`${t('tzSetToBrowser')}: ${sysTz}`)
    }
  } catch {
    selectedTimezone.value = 'UTC'
  }
}

// Calculate Initials from Full Name or Username
const initials = computed(() => {
  const name = fullName.value.trim() || username.value.trim()
  if (!name) return 'US'
  const parts = name.split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase()
  }
  return name.slice(0, 2).toUpperCase()
})


function updateClock() {
  const now = new Date()
  try {
    currentTime.value = i18nFormatTime(now, {
      timeZone: selectedTimezone.value,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }) + ` (${selectedTimezone.value})`
  } catch {
    currentTime.value = i18nFormatTime(now)
  }
}

async function loadProfile() {
  const localUser = getStoredUser()
  if (localUser) {
    fullName.value = localUser.full_name || ''
    username.value = localUser.username || ''
    email.value = localUser.email || ''
    role.value = localUser.role_name || ''
    uid.value = localUser.uid || ''
    initialFullName.value = fullName.value.trim()
    initialEmail.value = email.value.trim()
  }
  try {
    const me = await apiGetMe()
    if (me) {
      fullName.value = me.full_name || ''
      username.value = me.username || ''
      email.value = me.email || ''
      role.value = me.role_name || ''
      uid.value = me.uid || ''
      if (me.avatar) {
        avatarUrl.value = me.avatar
      }
      mfaEnabled.value = !!me.mfa_enabled
      forceMfa.value = !!me.force_mfa
      initialFullName.value = fullName.value.trim()
      initialEmail.value = email.value.trim()
    }
  } catch (err) {
    // fallback to local user
  }
}

function triggerUpload() {
  fileInput.value?.click()
}

function onFileSelected(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return
  const file = target.files[0]
  if (file.size > 2 * 1024 * 1024) {
    showToast(t('maxFileSize2MB'), true)
    return
  }
  const reader = new FileReader()
  reader.onload = async (e) => {
    const result = e.target?.result as string
    avatarUrl.value = result
    try {
      await apiUpdateMe({ avatar: result })
      updateStoredUser({ avatar: result })
      showToast(t('avatarUpdated'))
    } catch {
      showToast(t('avatarUpdateError'), true)
    }
  }
  reader.readAsDataURL(file)
}

async function handleResetAvatar() {
  avatarUrl.value = ''
  try {
    await apiUpdateMe({ avatar: '' })
    updateStoredUser({ avatar: '' })
    showToast(t('avatarReset'))
  } catch {
    showToast(t('avatarResetError'), true)
  }
}

async function saveProfile() {
  if (!isProfileDirty.value) return
  if (!fullName.value.trim()) {
    showToast(t('fullNameRequired'), true)
    return
  }
  isSaving.value = true
  try {
    await apiUpdateMe({
      full_name: fullName.value.trim(),
      email: email.value.trim(),
    })
    updateStoredUser({
      full_name: fullName.value.trim(),
      email: email.value.trim(),
    })
    initialFullName.value = fullName.value.trim()
    initialEmail.value = email.value.trim()
    showToast(t('profileSaved'))
  } catch (err: any) {
    showToast(translateApiError(err, 'profileSaveError'), true)
  } finally {
    isSaving.value = false
  }
}

async function handleChangePassword() {
  statusMessage.value = ''
  if (!oldPassword.value || !newPassword.value || !confirmPassword.value) {
    statusMessage.value = t('fillAllPasswordFields')
    isError.value = true
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    statusMessage.value = t('passwordsDoNotMatch')
    isError.value = true
    return
  }
  if (newPassword.value.length < 4) {
    statusMessage.value = t('passwordMinLength')
    isError.value = true
    return
  }
  try {
    await apiChangePassword(oldPassword.value, newPassword.value)
    statusMessage.value = t('passwordChangedSuccess')
    isError.value = false
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
    mustChangeBanner.value = false
    updateStoredUser({ must_change_password: false })
    showToast(t('passwordChangedSuccess'))
  } catch (err: any) {
    statusMessage.value = translateApiError(err, 'passwordChangeError')
    isError.value = true
  }
}

function onLangChange(e: Event) {
  const target = e.target as HTMLSelectElement
  setLanguage(target.value as Language)
}

async function handleTerminateOtherSessions() {
  const confirmed = await showConfirm({
    title: t('terminateOthersBtn'),
    message: t('terminateOthersConfirm'),
    isDanger: true,
  })
  if (!confirmed) return
  try {
    await apiTerminateSessions(true)
    showToast(t('terminateOthersSuccess'))
    await loadMySessions()
  } catch (err: any) {
    showToast(err?.response?.data?.detail || t('errorTerminatingSessions'), true)
  }
}

async function handleTerminateAllSessions() {
  const confirmed = await showConfirm({
    title: t('terminateAllLogoutBtn'),
    message: t('confirmTerminateAllSessionsCurrent'),
    isDanger: true,
  })
  if (!confirmed) return
  isSessionTerminated.value = true
  showToast(t('terminatingSessions'))
  try {
    await apiTerminateSessions(false)
  } catch {
    await apiLogout().catch(() => {})
  }
  setTimeout(() => {
    clearAuthSession()
    router.push('/login')
  }, 1000)
}

// Detection for user agent
function detectSession() {
  const ua = navigator.userAgent
  let browser = 'Browser'
  if (ua.includes('Chrome')) browser = 'Chrome'
  else if (ua.includes('Firefox')) browser = 'Firefox'
  else if (ua.includes('Safari')) browser = 'Safari'

  let os = 'OS'
  if (ua.includes('Win')) os = 'Windows'
  else if (ua.includes('Mac')) os = 'macOS'
  else if (ua.includes('Linux')) os = 'Linux'

  userAgent.value = `${browser} on ${os}`
}

watch(selectedTheme, (val) => {
  setStoredTheme(val)
})

watch(selectedTimezone, (val) => {
  localStorage.setItem('nms_timezone', val)
  if (availableTimezones.value.length && !availableTimezones.value.includes(val)) {
    availableTimezones.value.unshift(val)
  }
  updateClock()
  apiUpdateMe({ timezone: val }).catch(() => {})
})

const notifSubscribedModules = ref<string[] | null>(null)
const notifModuleRules = ref<Record<string, { min_severity?: string }>>({})
const availableModules = ref<NotificationModuleInfo[]>([])

async function loadNotificationPreferences() {
  try {
    const [prefs, modules] = await Promise.all([
      apiFetchNotificationPreferences(),
      apiFetchNotificationModules(),
    ])
    notifSubscribedModules.value = prefs.subscribed_modules ?? null
    notifModuleRules.value = prefs.module_rules || {}
    availableModules.value = modules || []
  } catch (err) {
    console.error('Failed to load notification preferences or modules:', err)
  }
}

async function saveNotificationPreferences() {
  try {
    await apiUpdateNotificationPreferences({
      subscribed_modules: notifSubscribedModules.value,
      module_rules: notifModuleRules.value,
    })
    showToast(t('profileSaved'))
  } catch (err) {
    showToast(t('profileSaveError'), true)
  }
}

function isModuleSubscribed(modId: string): boolean {
  if (modId === 'core') return true
  if (notifSubscribedModules.value === null) return true
  return notifSubscribedModules.value.includes(modId)
}

function toggleModuleSubscription(modId: string) {
  if (modId === 'core') return
  let current: string[]
  if (notifSubscribedModules.value === null) {
    current = availableModules.value.map(m => m.id)
  } else {
    current = [...notifSubscribedModules.value]
  }

  const idx = current.indexOf(modId)
  if (idx > -1) {
    current.splice(idx, 1)
  } else {
    current.push(modId)
  }
  notifSubscribedModules.value = current
  saveNotificationPreferences()
}

function resetModulesToAll() {
  notifSubscribedModules.value = null
  saveNotificationPreferences()
}

function setModuleMinSeverity(modId: string, sev: string) {
  const updatedRules = { ...notifModuleRules.value }
  if (!updatedRules[modId]) {
    updatedRules[modId] = {}
  }
  if (sev === 'info' || !sev) {
    delete updatedRules[modId].min_severity
    if (Object.keys(updatedRules[modId]).length === 0) {
      delete updatedRules[modId]
    }
  } else {
    updatedRules[modId] = { ...updatedRules[modId], min_severity: sev }
  }
  notifModuleRules.value = updatedRules
  saveNotificationPreferences()
}

onMounted(() => {
  initTimezones()
  loadProfile()
  loadMySessions()
  loadNotificationPreferences()
  detectSession()
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  if (!localStorage.getItem('nms_timezone')) {
    detectSystemTimezone()
  }
  const u = getStoredUser()
  if (route.query.must_change === 'true' || u?.must_change_password) {
    mustChangeBanner.value = true
  }
})

onUnmounted(() => {
  if (clockTimer) {
    clearInterval(clockTimer)
    clockTimer = null
  }
})
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(20px);
}
</style>
