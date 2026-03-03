/**
 * Feature flags — controlled via VITE_ environment variables.
 * Set to "true" to enable; anything else (or absent) = disabled.
 */
export const FEATURE_BILLING = import.meta.env.VITE_FEATURE_BILLING === 'true'
