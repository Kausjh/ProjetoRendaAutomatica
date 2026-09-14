import { StyleSheet, Text, View } from "react-native";

export default function BootstrapScreen() {
  return (
    <View style={styles.container}>
      <Text style={styles.eyebrow}>PROJETO RENDA AUTOMÁTICA</Text>
      <Text style={styles.title}>Public App MVP</Text>
      <Text style={styles.body}>
        Bootstrap Android pronto. A próxima etapa conecta esta interface à
        User-Facing API V1.
      </Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>Fundação ativa</Text>
        <Text style={styles.item}>Expo Router</Text>
        <Text style={styles.item}>TypeScript estrito</Text>
        <Text style={styles.item}>TanStack Query</Text>
        <Text style={styles.item}>Secure Store</Text>
        <Text style={styles.item}>Zero segredos no bundle</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: 24,
    gap: 16,
  },
  eyebrow: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1.5,
    opacity: 0.6,
  },
  title: {
    fontSize: 34,
    fontWeight: "800",
  },
  body: {
    fontSize: 16,
    lineHeight: 24,
    opacity: 0.75,
  },
  card: {
    marginTop: 8,
    padding: 20,
    borderRadius: 18,
    borderWidth: StyleSheet.hairlineWidth,
    gap: 8,
  },
  cardTitle: {
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 4,
  },
  item: {
    fontSize: 15,
  },
});
