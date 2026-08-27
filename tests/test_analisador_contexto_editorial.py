from __future__ import annotations

from models.oferta import Oferta
from services.analisador_contexto_editorial import AnalisadorContextoEditorial


def oferta(nome: str, categoria: str = "") -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=500.0,
        preco_antigo=650.0,
        link="https://example.com/contexto",
        imagem=None,
    )
    item.categoria = categoria
    return item


def tipos(nome: str, categoria: str = "") -> list[str]:
    resultado = AnalisadorContextoEditorial().analisar(oferta(nome, categoria))
    return [sinal.tipo for sinal in resultado.sinais]


def test_detecta_intel_core_antigo_sem_depender_de_kit_upgrade():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Processador Intel Core i5-4570 3.2GHz")
    )
    assert resultado.principal is not None
    assert "cpu_antiga" in [sinal.tipo for sinal in resultado.sinais]
    assert "4ª geração" in next(
        sinal.detalhe for sinal in resultado.sinais if sinal.tipo == "cpu_antiga"
    )


def test_upgrade_com_cpu_antiga_vira_mismatch_editorial():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Upgrade Intel Core i7-4770 16GB DDR3")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "upgrade_antigo"


def test_gt_1030_com_marketing_4k_vira_mismatch_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Gamer 4K Intel i5 GT 1030 16GB SSD")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "marketing_gpu_desproporcional"


def test_gpu_antiga_e_detectada_mesmo_sem_marketing_exagerado():
    assert "gpu_antiga_entrada" in tipos("Placa de Vídeo GeForce GTX 1050 Ti 4GB")


def test_ram_de_4gb_e_sinalizada():
    assert "ram_baixa" in tipos("Notebook Intel N100 4GB RAM 128GB SSD")


def test_ssd_de_120gb_e_sinalizado():
    assert "armazenamento_apertado" in tipos(
        "SSD SATA 120GB 2.5",
        "Armazenamento",
    )


def test_monitor_gamer_75hz_e_sinalizado():
    assert "monitor_gamer_basico" in tipos(
        "Monitor Gamer 24 Full HD 75Hz",
        "Monitor",
    )


def test_xeon_e5_e_sinalizado():
    assert "xeon_antigo" in tipos("Kit Xeon E5-2670 v3 X99 16GB")


def test_hardware_moderno_normal_nao_recebe_sinal_negativo():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Ryzen 7 7700 RTX 4070 32GB DDR5 SSD NVMe 1TB")
    )
    assert resultado.tem_contexto is False
