# Acesso seguro de clientes — V1

Este documento define como aplicações cliente podem consumir a API de
aplicação sem transformar o control plane administrativo em uma API pública.

## Princípios

- a API de aplicação continua read-only;
- a API administrativa da porta `8765` não pertence ao contrato de clientes;
- o aplicativo Android privado permanece fora deste repositório;
- acesso remoto exige autenticação Bearer;
- HTTP remoto puro, sem um transporte externo criptografado e explicitamente
  confiável, é rejeitado pelo cliente de referência.

## Modos aceitos

### Loopback HTTP

`http://127.0.0.1:8766` e outros endereços loopback podem ser usados sem
Bearer token. Esse é o modo padrão do runtime.

### HTTPS remoto

Um endpoint remoto `https://...` é aceito somente quando um Bearer token é
fornecido ao cliente.

### HTTP sobre túnel confiável

Quando a criptografia é fornecida por uma camada externa, como um túnel ou
VPN autenticado, o cliente pode usar uma URL HTTP remota somente com:

1. Bearer token; e
2. `transporte_confiavel=True`.

A flag é deliberadamente explícita para impedir que um endereço remoto HTTP
seja aceito por acidente.

## O que não deve acontecer

- bind remoto sem token;
- envio de Bearer token por HTTP remoto puro;
- exposição direta da porta administrativa `8765`;
- inclusão de APK, Gradle ou código do aplicativo Android privado neste
  repositório público.

## Contratos

- API: `contracts/api_v1.contract.json`
- política de acesso: `contracts/client_access_policy_v1.json`
- cliente de referência: `clients/reference_api_v1.py`

O aplicativo privado futuro deve obedecer aos mesmos limites, mas sua
implementação permanece fora deste repositório.
