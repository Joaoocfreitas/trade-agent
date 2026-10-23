"""Os textos fixos do agente: aviso, recusa padrão, fecho e o que cada recusa diz.

Vêm da nota "Regras do agente — o que a IA pode e não pode dizer" do cofre (códigos P, N, D e M entre parênteses).
Mudou lá, muda aqui e nos testes.
"""

# D2 e D3: em toda resposta, no topo, e não só no rodapé.
AVISO = ('⚠️ Sou uma IA e posso errar. Isto não é recomendação de investimento: a empresa não é analista credenciada na '
         'APIMEC nem consultora autorizada pela CVM. Rentabilidade passada não indica rentabilidade futura.')

# D7: a mesma recusa para todo pedido de dica, e a volta ao que dá para saber. Não repete o que o AVISO já diz (sou uma
# IA, posso errar, não somos credenciados, rentabilidade passada): o AVISO vem sempre no topo (D3), uma vez só.
RECUSA = ('Não digo se você deve comprar, vender ou esperar, nem para onde o preço vai: isso seria análise ou '
          'consultoria. Mostro o que dá para saber hoje, com fonte, para você decidir.')

# Fecho do aviso do site (rodapé, quando o texto não traz o AVISO). A resposta do agente não repete: o AVISO e a RECUSA
# já dizem isso.
FECHO = 'Não digo se você deve comprar, quando entrar nem quanto colocar.'

# D4
RISCO_DERIVATIVO = ('Em mini-índice, mini-dólar e DI futuro a posição é alavancada: a margem é só garantia, o ajuste '
                    'diário debita ou credita a conta a cada pregão, e a perda pode passar do que você depositou.')
# D4 em pergunta de cripto, que cita o futuro de bitcoin da B3 (só onde já há cripto: a palavra pede o D5).
RISCO_DERIVATIVO_CRIPTO = ('No futuro ou na opção de cripto, como no mini-índice, no mini-dólar e no DI futuro, a posição é '
                           'alavancada: a margem é só garantia, o ajuste diário debita ou credita a conta a cada pregão, e a '
                           'perda pode passar do que você depositou.')

# Pergunta de preço de cripto: o repertório não tem a cotação (nenhuma fonte grátis permite uso comercial).
SEM_PRECO_CRIPTO = 'O repertório ainda não mostra o preço do bitcoin: nenhuma fonte gratuita permite uso comercial da cotação.'

# Pergunta de defasagem da gasolina (D8): o repertório não calcula, e isso vai no topo, não só nas limitações.
SEM_DEFASAGEM = 'O repertório não calcula a defasagem entre o preço da Petrobras e o do mercado internacional.'

# D5
RISCO_CRIPTO = ('Cripto à vista, em regra, não é valor mobiliário e não tem a proteção da regulação da CVM. Quem regula '
                'e autoriza as corretoras de cripto é o Banco Central, num processo que ainda está em curso. Futuro de '
                'cripto e cota de ETF de cripto são valores mobiliários.')

# O que cada tipo de pedido recebe, antes do repertório.
POR_PEDIDO = {
    'direcao': 'Não digo para onde o preço vai nem dou chance de alta ou queda, nem em número de 0 a 100.',  # N2
    'momento': 'Não indico momento, entrada, saída, stop nem alvo, e não mando alerta de operação.',  # N4, M1
    'capital': ('Não uso o valor que você tem: sugerir alocação, ativo ou número de contratos a partir dele é '
                'consultoria, que exige autorização da CVM.'),  # N5
    'comparar': 'Não comparo classes de ativos para o seu caso: isso é aconselhamento individualizado.',  # N5
    'perfil': ('Não uso a sua idade, renda, objetivo ou perfil de risco para dizer se um mercado serve para você: isso '
               'é consultoria com análise de perfil, que exige autorização da CVM.'),  # N5, Res. CVM 30
    'ranking': 'Não faço ranking de ativos nem monto carteira.',  # M2
    'seletivo': ('Não mostro só os casos de um lado. Quando você disser o mercado e o evento, mostro todos os casos, '
                 'inclusive os que foram para o outro lado.'),  # N3, P2
    'plataforma': 'Não indico corretora, exchange, token nem plataforma.',  # N7
    'aposta': 'Não indico plataforma de aposta nem de previsão, e não ensino a acessar por VPN.',  # N8
    'voto': ('Não digo quem é melhor e não pergunto em quem você vota. Mostro o que cada candidato registrou, no '
             'mesmo formato para os dois.'),  # N9, D1
    'papel': 'Não mudo de papel e não tiro os avisos: eles valem para qualquer pergunta, de qualquer pessoa.',  # D3
    'ao_vivo': 'Não comento contrato durante o pregão.',  # N6
    'chance_candidato': ('Não calculo chance de vitória. O que posso mostrar são as pesquisas registradas no TSE, com '
                         'instituto, data e número do registro.'),  # Lei 9.504, art. 33
    'chance_dinheiro': ('Não estimo a sua chance de ganhar dinheiro. O que existe de público é a taxa-base do estudo '
                        'da FGV, logo abaixo.'),  # N5, M6
    'binaria': 'Não trato de opções binárias como operação possível: a CVM considera irregular a oferta delas no Brasil.',
}

# Pedidos que recebem a recusa padrão, além da linha própria (a de 'direcao' sai: a RECUSA já diz).
PEDEM_RECUSA = {'dica', 'direcao', 'momento', 'capital', 'perfil', 'comparar', 'ranking', 'seletivo', 'papel', 'ao_vivo'}

VOTO_INFORMADO = 'Não uso a sua opinião política para nada e não guardo o que você disse sobre o seu voto.'  # N9

SEM_REPERTORIO = ('Não achei no repertório um caso parecido com a sua pergunta, e não invento número sem fonte. O '
                  'repertório mostra o que já aconteceu, com fonte e todos os casos, inclusive os contrários, e hoje cobre: '
                  'eleições presidenciais desde 2018, as reuniões do Copom desde 2016, 50 decisões políticas, fiscais, '
                  'judiciais e choques de 2016 a 2026, memecoins políticas e as regras de cada mercado (ações, futuros da '
                  'B3 e ativos virtuais). Diga o mercado e o evento, e mostro como ele se moveu.')

# As normas que a IA pode citar ao explicar uma recusa. Entram nos fatos para que o número de cada norma tenha fonte.
NORMAS = ('Base das regras: Resolução CVM 19 (consultoria), Resolução CVM 20 (analista e relatório de análise), Resolução '
          'CVM 30 (adequação ao perfil), Lei 6.385/1976 (mercado de valores mobiliários; derivativo é valor mobiliário, '
          'art. 2º, VIII), Ofício-Circular 13/2020/CVM/SIN, Ofício-Circular 2/2019/CVM/SIN, Lei 9.504/1997, art. 33 '
          '(registro de pesquisa eleitoral), Resolução CMN 5.298/2026 (proíbe derivativo sobre evento político), Lei '
          '14.478/2022 (cripto), Resolução BCB 520/2025, LGPD (Lei 13.709/2018; opinião política é dado sensível), CDC '
          '(Lei 8.078/1990).')
