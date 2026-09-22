import { Ionicons } from "@expo/vector-icons";
import {
  Redirect,
  router,
  useLocalSearchParams,
} from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthSession } from "@/src/auth";
import {
  type CommunityReportReason,
  useCreateCommunityReport,
} from "@/src/reporting";
import { appTheme } from "@/src/ui";

type ReasonOption = Readonly<{
  value: CommunityReportReason;
  label: string;
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
}>;

const REASON_OPTIONS: readonly ReasonOption[] = [
  {
    value: "spam",
    label: "Spam",
    description: "Conteúdo repetitivo, promocional ou sem utilidade.",
    icon: "mail-unread-outline",
  },
  {
    value: "fraud",
    label: "Fraude",
    description: "Tentativa de enganar, falsificar preço ou oferta.",
    icon: "warning-outline",
  },
  {
    value: "malicious_link",
    label: "Link malicioso",
    description: "Link suspeito, perigoso ou que tenta roubar dados.",
    icon: "shield-outline",
  },
  {
    value: "abuse",
    label: "Abuso",
    description: "Conteúdo abusivo, ofensivo ou direcionado a alguém.",
    icon: "hand-left-outline",
  },
  {
    value: "off_topic",
    label: "Fora do tema",
    description: "A contribuição não corresponde a uma oferta válida.",
    icon: "unlink-outline",
  },
  {
    value: "duplicate",
    label: "Duplicado",
    description: "A mesma contribuição já aparece em outro registro.",
    icon: "copy-outline",
  },
  {
    value: "other",
    label: "Outro problema",
    description: "Algo está errado, mas não se encaixa nas opções acima.",
    icon: "ellipsis-horizontal-circle-outline",
  },
];

function firstParam(
  value: string | string[] | undefined,
): string {
  return Array.isArray(value)
    ? value[0] ?? ""
    : value ?? "";
}

export default function ReportScreen() {
  const { snapshot } = useAuthSession();

  const params = useLocalSearchParams<{
    targetId?: string | string[];
    targetLabel?: string | string[];
  }>();

  const targetId = firstParam(
    params.targetId,
  ).trim();

  const targetLabel = firstParam(
    params.targetLabel,
  ).trim();

  const createReport = useCreateCommunityReport();

  const [reason, setReason] =
    useState<CommunityReportReason | null>(
      null,
    );

  const [details, setDetails] =
    useState("");

  const [feedback, setFeedback] =
    useState<string | null>(
      null,
    );

  const [submitted, setSubmitted] =
    useState(false);

  if (
    snapshot.status
    === "restoring"
  ) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator
          size="large"
          color={appTheme.colors.accent}
        />
      </View>
    );
  }

  if (
    snapshot.status
    !== "authenticated"
  ) {
    return <Redirect href="/" />;
  }

  if (!targetId) {
    return (
      <SafeAreaView
        style={styles.screen}
        edges={["top"]}
      >
        <View style={styles.invalidState}>
          <Ionicons
            name="alert-circle-outline"
            size={38}
            color={appTheme.colors.danger}
          />

          <Text style={styles.invalidTitle}>
            Contribuição inválida
          </Text>

          <Text style={styles.bodyCentered}>
            Não recebemos uma identificação válida para registrar
            a denúncia.
          </Text>

          <Pressable
            accessibilityRole="button"
            style={styles.secondaryButton}
            onPress={() => router.back()}
          >
            <Text style={styles.secondaryButtonText}>
              Voltar
            </Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const submit = async (): Promise<void> => {
    setFeedback(null);

    if (!reason) {
      setFeedback(
        "Escolha o motivo da denúncia antes de enviar.",
      );
      return;
    }

    try {
      const result = await createReport.mutateAsync({
        targetId,
        reason,
        details: details.trim() || null,
      });

      setSubmitted(true);

      setFeedback(
        result.idempotentReplay
          ? "Essa denúncia já havia sido recebida com segurança."
          : "Denúncia recebida. A equipe poderá revisar esta contribuição.",
      );
    } catch (caught) {
      setFeedback(
        caught instanceof Error
          ? caught.message
          : "Não foi possível enviar a denúncia.",
      );
    }
  };

  return (
    <SafeAreaView
      style={styles.screen}
      edges={["top"]}
    >
      <ScrollView
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.container}
      >
        <View style={styles.header}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Voltar"
            style={styles.backButton}
            onPress={() => router.back()}
          >
            <Ionicons
              name="chevron-back"
              size={22}
              color={appTheme.colors.text}
            />
          </Pressable>

          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>
              MODERAÇÃO DA COMUNIDADE
            </Text>

            <Text style={styles.title}>
              Reportar problema
            </Text>
          </View>
        </View>

        <View style={styles.hero}>
          <View style={styles.heroIcon}>
            <Ionicons
              name="flag-outline"
              size={24}
              color={appTheme.colors.danger}
            />
          </View>

          <Text style={styles.heroTitle}>
            O que há de errado?
          </Text>

          <Text style={styles.body}>
            Sua denúncia não remove a contribuição automaticamente.
            Ela registra um sinal para revisão e fica vinculada à sua conta.
          </Text>
        </View>

        <View style={styles.targetCard}>
          <Text style={styles.sectionEyebrow}>
            CONTRIBUIÇÃO
          </Text>

          <Text
            style={styles.targetLabel}
            numberOfLines={1}
          >
            {targetLabel || "Contribuição comunitária"}
          </Text>

          <Text
            style={styles.targetId}
            numberOfLines={1}
          >
            {targetId}
          </Text>
        </View>

        <View style={styles.formCard}>
          <View>
            <Text style={styles.sectionEyebrow}>
              MOTIVO
            </Text>

            <Text style={styles.sectionTitle}>
              Escolha uma categoria
            </Text>
          </View>

          <View style={styles.reasonList}>
            {REASON_OPTIONS.map(
              (option) => {
                const selected =
                  reason === option.value;

                return (
                  <Pressable
                    key={option.value}
                    accessibilityRole="button"
                    accessibilityState={{
                      selected,
                    }}
                    style={[
                      styles.reasonCard,
                      selected &&
                        styles.reasonCardSelected,
                    ]}
                    onPress={() => {
                      if (!submitted) {
                        setReason(
                          option.value,
                        );
                      }
                    }}
                  >
                    <View
                      style={[
                        styles.reasonIcon,
                        selected &&
                          styles.reasonIconSelected,
                      ]}
                    >
                      <Ionicons
                        name={option.icon}
                        size={18}
                        color={
                          selected
                            ? appTheme.colors.accent
                            : appTheme.colors.textMuted
                        }
                      />
                    </View>

                    <View style={styles.reasonCopy}>
                      <Text
                        style={[
                          styles.reasonLabel,
                          selected &&
                            styles.reasonLabelSelected,
                        ]}
                      >
                        {option.label}
                      </Text>

                      <Text style={styles.reasonDescription}>
                        {option.description}
                      </Text>
                    </View>

                    <Ionicons
                      name={
                        selected
                          ? "radio-button-on"
                          : "radio-button-off"
                      }
                      size={19}
                      color={
                        selected
                          ? appTheme.colors.accent
                          : appTheme.colors.textSubtle
                      }
                    />
                  </Pressable>
                );
              },
            )}
          </View>
        </View>

        <View style={styles.formCard}>
          <Text style={styles.sectionEyebrow}>
            DETALHES
          </Text>

          <Text style={styles.sectionTitle}>
            Conte um pouco mais
          </Text>

          <Text style={styles.hint}>
            Opcional. Não inclua senhas, documentos ou outros dados
            pessoais.
          </Text>

          <TextInput
            editable={!submitted}
            multiline
            maxLength={1000}
            textAlignVertical="top"
            placeholder="Explique o problema encontrado..."
            placeholderTextColor={appTheme.colors.textSubtle}
            selectionColor={appTheme.colors.accent}
            style={styles.detailsInput}
            value={details}
            onChangeText={setDetails}
          />

          <Text style={styles.counter}>
            {details.length}/1000
          </Text>
        </View>

        {feedback ? (
          <View
            style={[
              styles.feedback,
              submitted &&
                styles.feedbackSuccess,
            ]}
          >
            <Ionicons
              name={
                submitted
                  ? "checkmark-circle-outline"
                  : "information-circle-outline"
              }
              size={19}
              color={
                submitted
                  ? appTheme.colors.success
                  : appTheme.colors.accent
              }
            />

            <Text style={styles.feedbackText}>
              {feedback}
            </Text>
          </View>
        ) : null}

        <Pressable
          accessibilityRole="button"
          disabled={
            createReport.isPending
            || submitted
          }
          style={[
            styles.submitButton,
            (
              createReport.isPending
              || submitted
            ) &&
              styles.disabledButton,
          ]}
          onPress={() => {
            void submit();
          }}
        >
          {createReport.isPending ? (
            <ActivityIndicator
              size="small"
              color={appTheme.colors.white}
            />
          ) : (
            <Ionicons
              name={
                submitted
                  ? "checkmark-circle-outline"
                  : "flag"
              }
              size={18}
              color={appTheme.colors.white}
            />
          )}

          <Text style={styles.submitButtonText}>
            {createReport.isPending
              ? "Enviando..."
              : submitted
                ? "Denúncia enviada"
                : "Enviar denúncia"}
          </Text>
        </Pressable>

        {submitted ? (
          <Pressable
            accessibilityRole="button"
            style={styles.secondaryButton}
            onPress={() => router.back()}
          >
            <Text style={styles.secondaryButtonText}>
              Voltar às contribuições
            </Text>
          </Pressable>
        ) : null}

        <View style={styles.notice}>
          <Ionicons
            name="shield-checkmark-outline"
            size={18}
            color={appTheme.colors.textMuted}
          />

          <Text style={styles.noticeText}>
            Uma denúncia é uma alegação para revisão. Ela não confirma
            abuso, fraude ou qualquer outra violação automaticamente.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: appTheme.colors.background,
  },
  loading: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: appTheme.colors.background,
  },
  container: {
    paddingHorizontal: 16,
    paddingTop: 10,
    paddingBottom: 42,
    gap: 16,
  },
  header: {
    minHeight: 54,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  backButton: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 13,
    backgroundColor: appTheme.colors.surface,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
  },
  headerCopy: {
    flex: 1,
  },
  eyebrow: {
    color: appTheme.colors.danger,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.35,
  },
  title: {
    marginTop: 2,
    color: appTheme.colors.text,
    fontSize: 24,
    fontWeight: "900",
    letterSpacing: -0.5,
  },
  hero: {
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.xl,
    backgroundColor: appTheme.colors.surface,
    padding: 18,
  },
  heroIcon: {
    width: 46,
    height: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 15,
    backgroundColor: appTheme.colors.dangerSurface,
  },
  heroTitle: {
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
    letterSpacing: -0.3,
  },
  body: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 19,
  },
  bodyCentered: {
    color: appTheme.colors.textMuted,
    fontSize: 12,
    lineHeight: 19,
    textAlign: "center",
  },
  targetCard: {
    gap: 5,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  sectionEyebrow: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1.2,
  },
  sectionTitle: {
    marginTop: 3,
    color: appTheme.colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  targetLabel: {
    color: appTheme.colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  targetId: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
  },
  formCard: {
    gap: 11,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 15,
  },
  reasonList: {
    gap: 8,
  },
  reasonCard: {
    minHeight: 66,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.border,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    padding: 11,
  },
  reasonCardSelected: {
    borderColor: appTheme.colors.accent,
    backgroundColor: appTheme.colors.accentSoft,
  },
  reasonIcon: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    backgroundColor: appTheme.colors.surface,
  },
  reasonIconSelected: {
    backgroundColor: appTheme.colors.surfaceElevated,
  },
  reasonCopy: {
    flex: 1,
    gap: 2,
  },
  reasonLabel: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  reasonLabelSelected: {
    color: appTheme.colors.accent,
  },
  reasonDescription: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 15,
  },
  hint: {
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 16,
  },
  detailsInput: {
    minHeight: 116,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surfaceElevated,
    color: appTheme.colors.text,
    paddingHorizontal: 13,
    paddingVertical: 12,
    fontSize: 13,
    lineHeight: 19,
  },
  counter: {
    color: appTheme.colors.textSubtle,
    fontSize: 9,
    textAlign: "right",
  },
  feedback: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.accentSoft,
    padding: 12,
  },
  feedbackSuccess: {
    backgroundColor: appTheme.colors.successSurface,
  },
  feedbackText: {
    flex: 1,
    color: appTheme.colors.text,
    fontSize: 11,
    lineHeight: 17,
  },
  submitButton: {
    minHeight: 50,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.danger,
    paddingHorizontal: 16,
  },
  submitButtonText: {
    color: appTheme.colors.white,
    fontSize: 13,
    fontWeight: "900",
  },
  secondaryButton: {
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: appTheme.colors.borderStrong,
    borderRadius: appTheme.radius.md,
    backgroundColor: appTheme.colors.surface,
    paddingHorizontal: 16,
  },
  secondaryButtonText: {
    color: appTheme.colors.text,
    fontSize: 12,
    fontWeight: "900",
  },
  disabledButton: {
    opacity: 0.55,
  },
  notice: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 9,
    borderRadius: appTheme.radius.lg,
    backgroundColor: appTheme.colors.surface,
    padding: 14,
  },
  noticeText: {
    flex: 1,
    color: appTheme.colors.textMuted,
    fontSize: 10,
    lineHeight: 16,
  },
  invalidState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    padding: 28,
  },
  invalidTitle: {
    color: appTheme.colors.text,
    fontSize: 20,
    fontWeight: "900",
  },
});
