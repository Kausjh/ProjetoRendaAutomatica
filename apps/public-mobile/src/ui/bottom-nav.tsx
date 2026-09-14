import { Ionicons } from "@expo/vector-icons";
import { router, usePathname } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { appTheme } from "@/src/ui/theme";

type MainRoute = "/home" | "/alerts" | "/watchlist" | "/account";

type NavItem = Readonly<{
  route: MainRoute;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  activeIcon: keyof typeof Ionicons.glyphMap;
}>;

const NAV_ITEMS: readonly NavItem[] = [
  {
    route: "/home",
    label: "Início",
    icon: "home-outline",
    activeIcon: "home",
  },
  {
    route: "/alerts",
    label: "Alertas",
    icon: "notifications-outline",
    activeIcon: "notifications",
  },
  {
    route: "/watchlist",
    label: "Lista",
    icon: "heart-outline",
    activeIcon: "heart",
  },
  {
    route: "/account",
    label: "Perfil",
    icon: "person-circle-outline",
    activeIcon: "person-circle",
  },
];

export function AppBottomNav() {
  const pathname = usePathname();

  const visible = NAV_ITEMS.some((item) => item.route === pathname);
  if (!visible) {
    return null;
  }

  return (
    <View style={styles.shell} pointerEvents="box-none">
      <View style={styles.nav}>
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.route;

          return (
            <Pressable
              key={item.route}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              accessibilityLabel={item.label}
              style={styles.item}
              onPress={() => {
                if (!active) {
                  router.replace(item.route);
                }
              }}
            >
              <View style={[styles.iconWrap, active && styles.iconWrapActive]}>
                <Ionicons
                  name={active ? item.activeIcon : item.icon}
                  size={22}
                  color={
                    active
                      ? appTheme.colors.accent
                      : appTheme.colors.textMuted
                  }
                />
              </View>

              <Text style={[styles.label, active && styles.labelActive]}>
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  shell: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 12,
    paddingBottom: 8,
  },
  nav: {
    minHeight: 68,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-around",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: 22,
    backgroundColor: appTheme.colors.surface,
    paddingHorizontal: 8,
    paddingVertical: 6,
    shadowColor: appTheme.colors.shadow,
    shadowOpacity: 0.24,
    shadowRadius: 16,
    shadowOffset: {
      width: 0,
      height: -5,
    },
    elevation: 18,
  },
  item: {
    flex: 1,
    minHeight: 54,
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
  },
  iconWrap: {
    width: 34,
    height: 30,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: appTheme.radius.pill,
  },
  iconWrapActive: {
    backgroundColor: appTheme.colors.accentSoft,
  },
  label: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    fontWeight: "700",
  },
  labelActive: {
    color: appTheme.colors.text,
  },
});
