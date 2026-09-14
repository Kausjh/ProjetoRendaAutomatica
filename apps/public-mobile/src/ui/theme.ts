import { radarBrand } from "@/src/ui/brand";

const gamer = radarBrand.verticals.gamer;

export const appTheme = {
  brand: radarBrand,
  vertical: gamer,
  colors: {
    background: radarBrand.core.night,
    surface: radarBrand.core.nightRaised,
    surfaceElevated: radarBrand.core.deepTeal,
    surfaceSoft: radarBrand.core.cyanSoft,

    border: radarBrand.core.border,
    borderStrong: radarBrand.core.borderStrong,

    text: radarBrand.core.white,
    textMuted: radarBrand.core.muted,
    textSubtle: radarBrand.core.subtle,

    accent: gamer.primary,
    accentStrong: radarBrand.core.cyanStrong,
    accentSoft: radarBrand.core.cyanSoft,

    price: gamer.secondary,
    success: gamer.secondary,
    successSurface: radarBrand.core.mintSoft,

    warning: radarBrand.semantic.warning,

    danger: radarBrand.semantic.danger,
    dangerSurface: radarBrand.semantic.dangerSurface,
    dangerBorder: radarBrand.semantic.dangerBorder,

    shadow: radarBrand.semantic.shadow,

    white: radarBrand.core.white,
    black: radarBrand.semantic.shadow,
  },
  commerce: {
    price: gamer.secondary,
    discount: gamer.secondary,
    coupon: gamer.primary,
  },
  gradients: {
    brand: gamer.gradient,
  },
  radius: {
    sm: 10,
    md: 14,
    lg: 18,
    xl: 24,
    pill: 999,
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 20,
    xxl: 24,
    xxxl: 32,
  },
} as const;

export type AppTheme = typeof appTheme;
