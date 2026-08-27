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
        oferta("Processador Intel Core i5-4570 3.2GHz", "Processador")
    )
    assert resultado.principal is not None
    assert "cpu_antiga" in [sinal.tipo for sinal in resultado.sinais]
    assert "4ª geração" in next(
        sinal.detalhe for sinal in resultado.sinais if sinal.tipo == "cpu_antiga"
    )
    assert resultado.principal.severidade == 1


def test_cpu_antiga_em_pc_completo_continua_relevante():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Gamer Intel Core i5-4570 16GB SSD", "Computador")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "cpu_antiga"
    assert resultado.principal.severidade == 3


def test_upgrade_com_cpu_antiga_vira_mismatch_editorial():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Upgrade Intel Core i7-4770 16GB DDR3", "Kit upgrade")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "upgrade_antigo"


def test_gt_1030_com_marketing_4k_vira_mismatch_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Gamer 4K Intel i5 GT 1030 16GB SSD", "Computador")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "marketing_gpu_desproporcional"


def test_gpu_antiga_avulsa_e_detectada_com_baixa_severidade():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Placa de Vídeo GeForce GTX 1050 Ti 4GB", "Placa de vídeo")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "gpu_antiga_entrada"
    assert resultado.principal.severidade == 1


def test_ram_de_4gb_em_notebook_e_sinalizada():
    assert "ram_baixa" in tipos(
        "Notebook Intel N100 4GB RAM 128GB SSD",
        "Notebook",
    )


def test_pente_de_4gb_avulso_nao_e_tratado_como_pc_com_pouca_ram():
    assert "ram_baixa" not in tipos(
        "Memória RAM DDR4 4GB 3200MHz",
        "Memória RAM",
    )


def test_ssd_de_120gb_em_computador_e_sinalizado():
    assert "armazenamento_apertado" in tipos(
        "Mini PC Intel N100 8GB RAM SSD SATA 120GB",
        "Computador",
    )


def test_ssd_de_120gb_avulso_nao_recebe_critica_de_capacidade():
    assert "armazenamento_apertado" not in tipos(
        "SSD SATA 120GB 2.5",
        "Armazenamento",
    )


def test_ddr3_avulsa_nao_recebe_critica_so_por_ser_antiga():
    assert "ddr3" not in tipos(
        "Memória 8GB DDR3 1600MHz",
        "Memória RAM",
    )


def test_monitor_gamer_75hz_e_sinalizado():
    assert "monitor_gamer_basico" in tipos(
        "Monitor Gamer 24 Full HD 75Hz",
        "Monitor",
    )


def test_xeon_e5_em_kit_e_sinalizado():
    assert "xeon_antigo" in tipos(
        "Kit Xeon E5-2670 v3 X99 16GB",
        "Kit upgrade",
    )


def test_ryzen_com_ddr3_vira_incompatibilidade_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Upgrade Ryzen 5 5600G 16GB DDR3", "Kit upgrade")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "incompatibilidade_memoria"
    assert resultado.principal.severidade == 5


def test_intel_12a_geracao_com_ddr3_vira_incompatibilidade_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Intel Core i5-12400 16GB DDR3", "Kit upgrade")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "incompatibilidade_memoria"
    assert resultado.principal.severidade == 5


def test_ryzen_com_socket_lga_vira_incompatibilidade_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Upgrade Ryzen 5 5600 LGA 1700 16GB DDR4", "Kit upgrade")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "incompatibilidade_socket"
    assert resultado.principal.severidade == 5


def test_intel_core_com_socket_am4_vira_incompatibilidade_forte():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("Kit Intel Core i5-12400 AM4 16GB DDR4", "Kit upgrade")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "incompatibilidade_socket"
    assert resultado.principal.severidade == 5


def test_cpu_muito_basica_com_marketing_gamer_e_sinalizada():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Gamer Intel N100 16GB SSD 512GB", "Computador")
    )
    assert resultado.principal is not None
    assert resultado.principal.tipo == "marketing_cpu_basica"
    assert resultado.principal.severidade == 4


def test_hardware_moderno_normal_nao_recebe_sinal_negativo():
    resultado = AnalisadorContextoEditorial().analisar(
        oferta("PC Ryzen 7 7700 RTX 4070 32GB DDR5 SSD NVMe 1TB", "Computador")
    )
    assert resultado.tem_contexto is False
