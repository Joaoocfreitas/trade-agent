from coletor.assuntos import classificar
from coletor.conteudo import classificar_captura, palavras_corpo


def test_assuntos_por_palavra_inteira_e_prefixo():
    assert classificar('Copom mantém Selic e dólar cai') == ['Juros e Copom', 'Câmbio']
    assert 'Congresso' in classificar('Deputados aprovam PEC na Câmara')
    assert 'Eleição 2026' in classificar('Quaest: Flávio Bolsonaro tem 45% no 2º turno')
    assert classificar('Federação de futebol anuncia calendário') == []  # 'fed' não casa dentro de 'federação'


def test_assuntos_ignoram_acento_e_caixa():
    assert classificar('INFLAÇÃO E IPCA') == ['Inflação']
    assert classificar('Petróleo sobe com China') == ['China e commodities']


def test_falsos_amigos_de_mercado_ficam_de_fora():
    assert classificar('Governo amplia Bolsa Família') == []
    assert classificar('Bolsas de estudo da Capes atrasam') == []
    assert classificar('Prefeitura estuda tarifa zero no ônibus') == []
    assert classificar('Ações do governo no Rio Grande do Sul') == []
    assert classificar('Bolsas sobem no exterior') == ['Bolsa']
    assert classificar('PETR4 dispara') == ['Bolsa']  # ticker da B3
    assert classificar('Trump anuncia tarifa de 50%') == ['EUA, Fed e tarifas']


TEXTO_LONGO = 'palavra ' * 700


def test_captura_ok_e_curta():
    assert classificar_captura(TEXTO_LONGO, 200, None) == 'ok'
    assert classificar_captura('pouco texto aqui', 200, None) == 'curto'


def test_captura_paywall_so_quando_o_corpo_e_curto():
    curto = 'Começo da matéria. ' * 30 + 'Conteúdo exclusivo para assinantes. Assine para continuar.'
    assert classificar_captura(curto, 200, None) == 'paywall'
    assert classificar_captura(TEXTO_LONGO + ' para continuar lendo', 200, None) == 'ok'


def test_previa_com_veja_tambem_comprido_continua_paywall():
    # o caso do Nexo de 21/10: lead + caixa de assinatura + 600 palavras de links "veja também"
    previa = ('A eleição mais disputada da ABL teve três candidatos. ' * 8
              + '\n[Para continuar lendo, torne-se um assinante. Já é assinante? Entre](https://x.com/assine)\n'
              + '\n'.join(f'- [Outra matéria interessante número {i}](https://x.com/{i})' for i in range(120)))
    assert palavras_corpo(previa) < 120
    assert classificar_captura(previa, 200, None) == 'paywall'


def test_bloqueios_nao_viram_erro_generico():
    assert classificar_captura('', 403, 'Access denied by robots.txt') == 'bloqueado_robots'
    assert classificar_captura('', 403, None) == 'bloqueado'
    assert classificar_captura('Just a moment... verify you are human', 200, None) == 'bloqueado'
    assert classificar_captura('', 404, 'not found') == 'erro_http'
    assert classificar_captura('', None, 'timeout') == 'erro'
