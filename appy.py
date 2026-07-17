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

def obtener_conexao():
    try:
        conn = mysql.connector.connect(**config_banco)
        return conn
    except mysql.connector.Error as err:
        st.error(f"Erro ao conectar ao banco HostGator: {err}")
        return None

# Função para calcular a capacidade real (usada no relatório de análise)
def calcular_capacidade_real(df_pedidos):
    if df_pedidos.empty:
        return 160.0
    data_minima = df_pedidos['data_pedido'].min()
    data_maxima = df_pedidos['data_pedido'].max()
    todos_os_dias = pd.date_range(start=data_minima, end=data_maxima)
    
    total_horas_capacidade = 0.0
    for dia in todos_os_dias:
        dia_semana = dia.weekday()
        if dia_semana <= 4:  # Seg a Sex
            total_horas_capacidade += 12.0
        elif dia_semana == 5: # Sábado
            total_horas_capacidade += 6.0
    return max(total_horas_capacidade, 12.0)

# Função para atualizar horas, faturamento e expandir/encolher o horário de término no banco de dados
def atualizar_horas_banco(id_pedido, novas_horas, data_pedido, hora_inicio_original):
    conn = obtener_conexao()
    if conn:
        cursor = conn.cursor()
        
        # 1. Puxa o valor cobrado por hora para este pedido específico
        cursor.execute("SELECT valor_hora FROM pedidos WHERE id = %s", (id_pedido,))
        resultado = cursor.fetchone()
        if resultado:
            valor_hora = resultado[0]
            # 2. Recalcula o faturamento total exato (Novas Horas x Valor da Hora)
            novo_faturamento = float(novas_horas) * float(valor_hora)
            
            # 3. Recalcula o novo horário de término baseado nas novas horas inseridas
            data_com_hora = datetime.combine(data_pedido, hora_inicio_original)
            novo_termino_dt = data_com_hora + timedelta(hours=float(novas_horas))
            novo_horario_string = f"{hora_inicio_original.strftime('%H:%M')} as {novo_termino_dt.strftime('%H:%M')}"
            
            # 4. Atualiza tudo no banco para manter os relatórios e a agenda precisos
            query = """
                UPDATE pedidos 
                SET horas = %s, faturamento_total = %s, horario = %s 
                WHERE id = %s
            """
            cursor.execute(query, (novas_horas, novo_faturamento, novo_horario_string, id_pedido))
            conn.commit()
            st.toast(f"🕒 Atualizado! Novo faturamento calculado: R$ {novo_faturamento:.2f}", icon="✅")
            
        cursor.close()
        conn.close()

# Inicialização das variáveis de controle de navegação e preenchimento
if 'aba_selecionada' not in st.session_state:
    st.session_state['aba_selecionada'] = "📅 Agenda Diária"

if 'planner_data' not in st.session_state:
    st.session_state['planner_data'] = datetime.today().date()
if 'planner_inicio' not in st.session_state:
    st.session_state['planner_inicio'] = time(7, 0)
if 'planner_fim' not in st.session_state:
    st.session_state['planner_fim'] = time(9, 0)
if 'planner_horas' not in st.session_state:
    st.session_state['planner_horas'] = 2.0
if 'agenda_data_selecionada' not in st.session_state:
    st.session_state['agenda_data_selecionada'] = datetime.today().date()

# Função auxiliar para mudar de aba programaticamente
def ir_para_aba_inserir():
    st.session_state['aba_selecionada'] = "📝 Inserir Pedido"

# Seletor horizontal para alternar entre as telas do sistema
opcao_menu = st.radio(
    "Navegação do Sistema",
    ["📅 Agenda Diária", "📝 Inserir Pedido", "📊 Relatório de Análise"],
    index=["📅 Agenda Diária", "📝 Inserir Pedido", "📊 Relatório de Análise"].index(st.session_state['aba_selecionada']),
    horizontal=True,
    key="menu_navegacao"
)
st.session_state['aba_selecionada'] = opcao_menu

st.markdown("---")

# =====================================================================
# TELA: 📅 DESIGN DA AGENDA (AÇÕES E VISUALIZAÇÃO)
# =====================================================================
if st.session_state['aba_selecionada'] == "📅 Agenda Diária":
    st.header("📅 Agenda de Ocupação Operacional")
    
    # ADICIONADO: format="DD/MM/YYYY" para converter a exibição para PT-BR
    data_agenda = st.date_input("Filtrar Dia da Agenda", value=st.session_state['agenda_data_selecionada'], format="DD/MM/YYYY")
    st.session_state['agenda_data_selecionada'] = data_agenda

    conn = obtener_conexao()
    if conn:
        query = "SELECT * FROM pedidos WHERE data_pedido = %s"
        df_dia = pd.read_sql(query, con=conn, params=[data_agenda.strftime('%Y-%m-%d')])
        conn.close()
        
        # Criação dos blocos de 30 em 30 minutos (07:00 até 19:00)
        horarios_agenda = []
        hora_atual_dt = datetime.combine(data_agenda, time(7, 0))
        hora_fim_dt = datetime.combine(data_agenda, time(19, 0))
        
        while hora_atual_dt <= hora_fim_dt:
            horarios_agenda.append(hora_atual_dt.time())
            hora_atual_dt += timedelta(minutes=30)
            
        st.write(f"### Linha do Tempo — Dia: {data_agenda.strftime('%d/%m/%Y')}")
        
        for h in horarios_agenda:
            ocupado = False
            dados_pedido = None
            p_inicio_original = None
            p_fim_original_str = ""
            
            if not df_dia.empty:
                for _, pedido in df_dia.iterrows():
                    try:
                        h_inicio_str, h_fim_str = pedido['horario'].split(" as ")
                        p_inicio = datetime.strptime(h_inicio_str.strip(), "%H:%M").time()
                        p_fim = datetime.strptime(h_fim_str.strip(), "%H:%M").time()
                        
                        # Verifica se o bloco de 30 minutos atual pertence a esse agendamento
                        if p_inicio <= h < p_fim:
                            ocupado = True
                            dados_pedido = pedido
                            p_inicio_original = p_inicio
                            p_fim_original_str = h_fim_str.strip()
                            break
                    except:
                        continue
            
            # --- CARD OCUPADO ---
            if ocupado:
                with st.container(border=True):
                    col_info, col_acao = st.columns([5, 1])
                    with col_info:
                        st.markdown(f"🔴 **{h.strftime('%H:%M')}**   |   **Duração:** {dados_pedido['horas']}h")
                        st.markdown(f"👤 **{str(dados_pedido['cliente']).upper()}**")
                        st.markdown(f"⚙️ *{dados_pedido['maquina']} — (Total: R$ {dados_pedido['faturamento_total']:.2f}) — Término às {p_fim_original_str}*")
                    
                    with col_acao:
                        with st.popover("⚙️ Editar"):
                            st.write("**Ajustar Tempo de Máquina**")
                            novas_horas = st.number_input("Horas:", min_value=0.1, max_value=24.0, value=float(dados_pedido['horas']), step=0.5, key=f"edit_{dados_pedido['id']}_{h}")
                            if st.button("Salvar no Banco", key=f"btn_{dados_pedido['id']}_{h}"):
                                atualizar_horas_banco(dados_pedido['id'], novas_horas, data_agenda, p_inicio_original)
                                st.rerun()
                                
            # --- CARD DISPONÍVEL ---
            else:
                with st.container(border=True):
                    col_disp, col_btn = st.columns([5, 1])
                    with col_disp:
                        st.markdown(f"🟢 **{h.strftime('%H:%M')}** — *Horário Disponível*")
                    with col_btn:
                        st.button(
                            "➕ Reservar", 
                            key=f"disp_{h}", 
                            on_click=ir_para_aba_inserir
                        )
                        if st.session_state.get(f"disp_{h}"):
                            st.session_state['planner_data'] = data_agenda
                            st.session_state['planner_inicio'] = h
                            st.session_state['planner_fim'] = (datetime.combine(data_agenda, h) + timedelta(hours=2)).time()
                            st.session_state['planner_horas'] = 2.0

# =====================================================================
# TELA: 📝 INSERIR PEDIDO (ALIMENTADA PELA AGENDA)
# =====================================================================
elif st.session_state['aba_selecionada'] == "📝 Inserir Pedido":
    st.header("Inserir Novo Pedido")
    
    with st.form("form_pedido", clear_on_submit=True):
        cliente = st.text_input("Nome do Cliente")
        # ADICIONADO: format="DD/MM/YYYY" para converter a exibição para PT-BR também na inserção
        data_pedido = st.date_input("Data do Trabalho", value=st.session_state['planner_data'], format="DD/MM/YYYY")
        
        col_horario1, col_horario2 = st.columns(2)
        with col_horario1:
            hora_inicio = st.time_input("Horário de Início", value=st.session_state['planner_inicio'])
        with col_horario2:
            hora_fim = st.time_input("Horário de Término", value=st.session_state['planner_fim'])
            
        horas = st.number_input("Quantas horas levou?", min_value=0.1, max_value=24.0, value=st.session_state['planner_horas'], step=0.5)
        
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
                
                conn = obtener_conexao()
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
                    
                    st.success(f"✅ Pedido do cliente '{cliente}' salvo com sucesso!")
                    st.session_state['planner_data'] = datetime.today().date()
                    st.session_state['planner_inicio'] = time(7, 0)
                    st.session_state['planner_fim'] = time(9, 0)
                    st.session_state['planner_horas'] = 2.0
                    st.session_state['aba_selecionada'] = "📅 Agenda Diária"
                    st.rerun()

# =====================================================================
# TELA: 📊 RELATÓRIO DE ANÁLISE
# =====================================================================
elif st.session_state['aba_selecionada'] == "📊 Relatório de Análise":
    st.header("Análise de Faturamento e Ocupação")
    
    if st.button("Atualizar Relatório 🔄"):
        st.rerun()
        
    conn = obtener_conexao()
    if conn:
        query = "SELECT * FROM pedidos"
        df = pd.read_sql(query, con=conn)
        conn.close()
        
        if df.empty:
            st.info("Nenhum dado encontrado no banco de dados.")
        else:
            df['data_pedido'] = pd.to_datetime(df['data_pedido'])
            df_temporal = df.set_index('data_pedido')
            
            # --- Bloco de Faturamento ---
            st.subheader("💰 Faturamento")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Faturamento Semanal**")
                faturamento_semanal = df_temporal['faturamento_total'].resample('W-SUN').sum()
                df_semanal = faturamento_semanal.reset_index()
                df_semanal.columns = ['Fim da Semana', 'Faturamento (R$)']
                df_semanal['Fim da Semana'] = df_semanal['Fim da Semana'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_semanal.style.format({'Faturamento (R$)': 'R$ {:.2f}'}))
                
            with col2:
                st.markdown("**Faturamento Mensal**")
                faturamento_mensal = df_temporal['faturamento_total'].resample('ME').sum()
                df_mensal = faturamento_mensal.reset_index()
                df_mensal.columns = ['Mês/Ano', 'Faturamento (R$)']
                df_mensal['Mês/Ano'] = df_mensal['Mês/Ano'].dt.strftime('%m/%Y')
                st.dataframe(df_mensal.style.format({'Faturamento (R$)': 'R$ {:.2f}'}))
                
            st.markdown("---")
            
            # --- Bloco de Clientes ---
            st.subheader("👥 Análise de Clientes")
            pedidos_por_cliente = df['cliente'].value_counts()
            
            col_cli1, col_cli2 = st.columns([1, 2])
            with col_cli1:
                st.metric("Cliente com MAIS pedidos", f"{pedidos_por_cliente.idxmax()}", f"{pedidos_por_cliente.max()} pedidos")
                st.metric("Cliente com MENOS pedidos", f"{pedidos_por_cliente.idxmin()}", f"{pedidos_por_cliente.min()} pedidos")
            
            with col_cli2:
                st.markdown("**Total de pedidos por cliente:**")
                df_clientes = pedidos_por_cliente.reset_index()
                df_clientes.columns = ['Cliente', 'Quantidade de Pedidos']
                st.dataframe(df_clientes, use_container_width=True)
                
            st.markdown("---")
            
            # --- Bloco de Máquinas ---
            st.subheader("⚙️ Tempo de Ocupação das Máquinas")
            horas_por_maquina = df.groupby('maquina')['horas'].sum()
            
            # Calcula a capacidade com base na regra de 12h (seg-sex) e 6h (sáb)
            CAPACIDADE_REAL_PERIODO = calcular_capacidade_real(df)
            
            col_maq = st.columns(len(horas_por_maquina))
            for i, (maquina, horas_ocupadas) in enumerate(horas_por_maquina.items()):
                with col_maq[i]:
                    horas_livres = max(0.0, CAPACIDADE_REAL_PERIODO - horas_ocupadas)
                    st.info(f"**{maquina}**")
                    st.metric("Horas Ocupadas", f"{horas_ocupadas:.1f}h")
                    st.metric("Horas Livres Totais no Período", f"{horas_livres:.1f}h")
            
            st.caption(f"ℹ️ O tempo livre é baseado na capacidade operacional da empresa para o intervalo de datas detectado (Seg-Sex: 12h/dia | Sáb: 6h/dia).")
