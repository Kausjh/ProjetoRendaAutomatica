# Bloco 26 — Client Transport V1 com Tailscale

## Objetivo

Disponibilizar a Application API V1 para um cliente remoto sem alterar o bind seguro do backend e sem publicar a API na Internet.

O transporte oficial do cliente é:

```text
cliente remoto
    |
    | HTTP dentro da tailnet autenticada
    v
Tailscale IPv4 :18767
    |
    | TCP forwarder tailnet-only
    v
127.0.0.1:8766
    |
    v
Application API V1
```

## Decisão arquitetural

A Application API continua ouvindo somente em `127.0.0.1:8766`.

O Tailscale fornece o transporte externo confiável. O cliente usa o IPv4 da máquina dentro da tailnet e a porta TCP `18767`. O forwarder entrega o tráfego ao backend loopback.

O Bearer token continua obrigatório para as rotas de dados. A rota de health pode permanecer sem autenticação para diagnóstico.

## Por que o transporte usa IPv4 Tailscale

O transporte não depende de MagicDNS nem de hostname `*.ts.net`.

Isso evita que a disponibilidade do cliente fique acoplada à resolução de nomes do dispositivo. O endereço remoto deve ser obtido da própria instalação Tailscale (`tailscale ip -4`) e não deve ser gravado no repositório.

## Segurança

Este modo corresponde à política `remote_http_over_trusted_tunnel` do Client Access Policy V1.

Garantias:

- backend em loopback;
- Tailscale tailnet-only;
- transporte externo confiável e criptografado;
- Bearer obrigatório para dados;
- sem Tailscale Funnel;
- sem exposição pública da porta `8766`;
- sem CORS como requisito para Android nativo;
- sem credenciais, tokens, IPs pessoais ou nomes de dispositivos no Git.

## Fronteiras

A API administrativa em `127.0.0.1:8765` é um control plane separado e não integra o contrato do cliente.

Este repositório público não contém o aplicativo Android privado nem seu transporte administrativo.

O transporte cliente do Bloco 26 encaminha exclusivamente para `127.0.0.1:8766`.

## Operação

Aplicar ou reconciliar o forwarder:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\client_transport_tailscale.ps1 -Action apply
```

Consultar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\client_transport_tailscale.ps1 -Action status
```

Remover somente o forwarder do cliente:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\client_transport_tailscale.ps1 -Action remove
```

A remoção afeta somente a porta configurada para o transporte cliente e não deve resetar a configuração global do Tailscale.

## Critérios de aceite

O Bloco 26 pode ser considerado completo quando:

1. a API local responde em `127.0.0.1:8766`;
2. uma rota de dados sem Bearer responde `401`;
3. existe forwarder tailnet-only `18767 -> 127.0.0.1:8766`;
4. o cliente remoto alcança `/api/v1/health` pelo IPv4 Tailscale;
5. o cliente remoto sem token recebe `401` em rota de dados;
6. o backend continua loopback;
7. Funnel permanece fora da arquitetura;
8. MagicDNS não é requisito;
9. a API administrativa permanece fora do contrato cliente;
10. o aplicativo privado permanece fora do repositório público.
