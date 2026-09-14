export const radarBrand = {
  name: "Radar de Ofertas",
  core: {
    night: "#0C101D",
    nightRaised: "#101827",
    deepTeal: "#174255",
    cyan: "#4ADDDC",
    cyanStrong: "#25C9CC",
    cyanSoft: "#123A41",
    mint: "#7EF2A5",
    mintSoft: "#15352B",
    white: "#F5F7FA",
    muted: "#9AA8BC",
    subtle: "#6F7F95",
    border: "#24354A",
    borderStrong: "#35566A",
  },
  semantic: {
    warning: "#F3C969",
    danger: "#FF6673",
    dangerSurface: "#30171D",
    dangerBorder: "#6C2C38",
    shadow: "#000000",
  },
  verticals: {
    gamer: {
      id: "gamer",
      label: "Gamer",
      primary: "#4ADDDC",
      secondary: "#7EF2A5",
      gradient: ["#4ADDDC", "#7EF2A5"] as const,
    },
  },
} as const;

export type RadarBrand = typeof radarBrand;
