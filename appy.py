import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, time, timedelta

# Configuração da página do Streamlit
st.set_page_config(page_title="Sistema de Relatórios - GapTech", layout="wide")

# 1. CONFIGURAÇÃO DA CONEXÃO COM A HOSTGATOR
config_banco = {
    'host': '162.241.3.46', # Ou o IP do seu servidor informado na HostGator
    'user': 'jeff1591_db_user',
    'password': '0~nh1U!.y89|',
    'database': 'jeff1591_Gaptech'
}

def obter_conexao():
    try:
        conn = mysql.connector.connect(**config_banco)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Erro ao conectar ao banco HostGator: {err}")
        return None

# Função para atualizar horas diretamente no banco de dados
def atualizar_horas_banco(id_pedido, novas_horas):
    conn = obter_conexao()
    if conn:
        cursor = conn.cursor()
        # Seleciona o valor da hora atual para refazer a multiplicação
        cursor.execute("SELECT valor_hora FROM pedidos WHERE id = %s", (id_pedido,))
        resultado = cursor.fetchone()
        if resultado:
            valor_hora = resultado[0]
            novo_faturamento = float(novas_horas) * float(valor_hora)
            
            query = "UPDATE pedidos SET horas = %s, faturamento_total = %s WHERE id = %s"
            cursor.execute(query, (novas_horas, novo_faturamento, id_pedido))
            conn.commit()
            st.toast("🕒 Horas atualizadas com sucesso no banco!", icon="✅")
        cursor.close()
        conn.close()

# Inicialização das variáveis de estado (Session State) para o clique na Agenda
if 'planner_data' not in st.session_state:
    st.session_state['planner_data'] = datetime.today().date()
if 'planner_inicio' not in st.session_state:
    st.session_state['planner_inicio'] = time(7, 0)
if 'planner_fim' not in st.session_state:
    st.session_state['planner_fim'] = time(9, 0)
if 'agenda_data_selecionada' not in st.session_state:
    st.session_state['agenda_data_selecionada'] = datetime.today().date()

# Sistema de Abas
aba_insercao, aba_analise, aba_agenda = st.tabs(["📝 Inserir Pedido", "📊 Relatório de Análise", "📅 Agenda Diária"])

# =====================================================================
# ABA 1: INSERÇÃO DE DADOS
# =====================================================================
with aba_insercao:
    st.header("Inserir Novo Pedido")
    
    with st.form("form_pedido", clear_on_submit=True):
        cliente = st.text_input("Nome do Cliente")
        data_pedido = st.date_input("Data do Trabalho", value=st.session_state['planner_data'])
        
        col_horario1, col_horario2 = st.columns(2)
        with col_horario1:
            hora_inicio = st.time_input("Horário de Início", value=st.session_state['planner_inicio'])
        with col_horario2:
            hora_fim = st.time_input("Horário de Término", value=st.session_state['planner_fim'])
            
        horas = st.number_input("Quantas horas levou?", min_value=0.1, max_value=24.0, value=2.0, step=0.5)
        
        maquina_opcao = st.selectbox(
            "Selecione a Máquina",
            ["Erosão a Fio (R$ 120/h)", "Erosão a Penetração (R$ 90/h)", "Erosão a Penetração (R$ 120/h)"]
        )
        
        submetido = st.form_submit_button("Salvar Pedido no Banco de Dados")
        
        if submetido:
            dia_da_semana = data_pedido.weekday()
            if not cliente:
                st.warning("Por favor, digite o nome do cliente.")
            elif dia_da_semana == 6:
                st.error("❌ Não é permitido cadastrar trabalhos aos Domingos.")
            else:
                if "Fio" in maquina_opcao:
                    maquina, valor_hora = "Erosão a Fio", 120
                elif "90" in maquina_opcao:
                    maquina, valor_hora = "Erosão a Penetração", 90
                else:
                    maquina, valor_hora = "Erosão a Penetração", 120
                    
                faturamento_total = horas * valor_hora
                horario_string = f"{hora_inicio.strftime('%H:%M')} as {hora_fim.strftime('%H:%M')}"
                
                conn = obter_conexao()
                if conn:
                    cursor = conn.cursor()
                    comando_sql = """
                    INSERT INTO pedidos (cliente, data_pedido, horario, horas, maquina, valor_hora, faturamento_total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    valores = (cliente, data_pedido.strftime('%Y-%m-%d'), horario_string, horas, maquina, valor_hora, faturamento_total)
                    cursor.execute(comando_sql, valores)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    st.session_state['sucesso_insercao'] = f"✅ Pedido do cliente '{cliente}' salvo com sucesso!"
                    st.rerun()

    if 'sucesso_insercao' in st.session_state:
        st.success(st.session_state['sucesso_insercao'])
        del st.session_state['sucesso_insercao']

# =====================================================================
# ABA 2: ANÁLISE DOS DADOS (RELATÓRIO)
# =====================================================================
with aba_analise:
    st.header("Análise de Faturamento e Ocupação")
    conn = obter_conexao()
    if conn:
        query = "SELECT * FROM pedidos"
        df_analise = pd.read_sql(query, con=conn)
        conn.close()
        
        if df_analise.empty:
            st.info("Nenhum dado cadastrado.")
        else:
            df_analise['data_pedido'] = pd.to_datetime(df_analise['data_pedido'])
            df_temporal = df_analise.set_index('data_pedido')
            
            # Faturamento
            st.subheader("💰 Faturamento")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Semanal**")
                st.dataframe(df_temporal['faturamento_total'].resample('W-SUN').sum().reset_index())
            with c2:
                st.markdown("**Mensal**")
                st.dataframe(df_temporal['faturamento_total'].resample('ME').sum().reset_index())

# =====================================================================
# ABA 3: 📅 DESIGN DA AGENDA (ESTILO CELULAR COPIANDO O SEU RASCUNHO)
# =====================================================================
with aba_agenda:
    st.header("📅 Agenda de Ocupação Operacional")
    
    # Filtro de data no topo da agenda
    data_agenda = st.date_input("Filtrar Dia da Agenda", value=st.session_state['agenda_data_selecionada'])
    st.session_state['agenda_data_selecionada'] = data_agenda

    conn = obter_conexao()
    if conn:
        # Puxa apenas os pedidos do dia selecionado
        query = "SELECT * FROM pedidos WHERE data_pedido = %s"
        df_dia = pd.read_sql(query, con=conn, params=[data_agenda.strftime('%Y-%m-%d')])
        conn.close()
        
        # Criação dos blocos de horários de 30 em 30 minutos (07:00 até 19:00)
        horarios_agenda = []
        hora_atual_dt = datetime.combine(data_agenda, time(7, 0))
        hora_fim_dt = datetime.combine(data_agenda, time(19, 0))
        
        while hora_atual_dt <= hora_fim_dt:
            horarios_agenda.append(hora_atual_dt.time())
            hora_atual_dt += timedelta(minutes=30)
            
        st.write(f"### Linha do Tempo — Dia: {data_agenda.strftime('%d/%m/%Y')}")
        
        # Varre cada horário de 30 minutos para montar os cards verticais
        for h in horarios_agenda:
            # Verifica se existe um agendamento cobrindo esse horário específico
            ocupado = False
            dados_pedido = None
            
            if not df_dia.empty:
                for _, pedido in df_dia.iterrows():
                    try:
                        # Extrai o início e o fim da string do banco (ex: "08:00 as 12:00")
                        h_inicio_str, h_fim_str = pedido['horario'].split(" as ")
                        p_inicio = datetime.strptime(h_inicio_str.strip(), "%H:%M").time()
                        p_fim = datetime.strptime(h_fim_str.strip(), "%H:%M").time()
                        
                        if p_inicio <= h < p_fim:
                            ocupado = True
                            dados_pedido = pedido
                            break
                    except:
                        continue
            
            # --- CARD OCUPADO (Cor roxa/azul escuro do celular com nome e botão de editar) ---
            if ocupado:
                with st.container(border=True):
                    col_info, col_acao = st.columns([5, 1])
                    with col_info:
                        st.markdown(f"🔴 **{h.strftime('%H:%M')}**   |   **Duração:** {dados_pedido['horas']}h   |   Máquina: {dados_pedido['maquina']}")
                        st.markdown(f"👤 **{str(dados_pedido['cliente']).upper()}**")
                    
                    with col_acao:
                        # Botão de edição rápida por linha
                        with st.popover("⚙️ Editar"):
                            st.write("Alterar Tempo de Máquina")
                            novas_horas = st.number_input("Horas:", min_value=0.1, max_value=24.0, value=float(dados_pedido['horas']), step=0.5, key=f"edit_{dados_pedido['id']}_{h}")
                            if st.button("Salvar no Banco", key=f"btn_{dados_pedido['id']}_{h}"):
                                atualizar_horas_banco(dados_pedido['id'], novas_horas)
                                st.rerun()
                                
            # --- CARD DISPONÍVEL (Caixa vazia pontilhada / cinza de clique rápido) ---
            else:
                with st.container(border=True):
                    col_disp, col_btn = st.columns([5, 1])
                    with col_disp:
                        st.markdown(f"🟢 **{h.strftime('%H:%M')}** — *Horário Disponível*")
                    with col_btn:
                        # Se clicar, envia os parâmetros para a Aba 1
                        if st.button("➕ Reservar", key=f"disp_{h}"):
                            st.session_state['planner_data'] = data_agenda
                            st.session_state['planner_inicio'] = h
                            # Define término estimado padrão de 2h adiante
                            termino_estimado = (datetime.combine(data_agenda, h) + timedelta(hours=2)).time()
                            st.session_state['planner_fim'] = termino_estimado
                            st.toast(f"Horário de {h.strftime('%H:%M')} enviado para a tela de inserção!")
                            # Troca o foco visual para a aba de inserção
                            st.markdown('<script>window.parent.document.querySelector(".stTabs [id^=\'tabs-bnd\']-tab-0").click();</script>', unsafe_allow_html=True)
