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

# Função para calcular a capacidade real
def calcular_capacidade_real(df_pedidos):
    if df_pedidos.empty:
        return 160.0
    data_minima = df_pedidos['data_pedido'].min()
    data_maxima = df_pedidos['data_pedido'].max()
    todos_os_dias = pd.date_range(start=data_minima, end=data_maxima)
    
    total_horas_capacidade = 0.0
    for dia in todos_os_dias:
        dia_semana = dia.weekday()
        if dia_semana <= 4:
            total_horas_capacidade += 12.0
        elif dia_semana == 5:
            total_horas_capacidade += 6.0
    return max(total_horas_capacidade, 12.0)

# Gerenciador de estado para navegação entre abas e preenchimento automático
if 'aba_ativa' not in st.session_state:
    st.session_state['aba_ativa'] = 0
if 'planner_data' not in st.session_state:
    st.session_state['planner_data'] = datetime.today().date()
if 'planner_inicio' not in st.session_state:
    st.session_state['planner_inicio'] = time(7, 0)
if 'planner_fim' not in st.session_state:
    st.session_state['planner_fim'] = time(19, 0)
if 'planner_horas' not in st.session_state:
    st.session_state['planner_horas'] = 4.0

# Renderização das Abas controlada por Session State
abas = ["📝 Inserir Pedido", "📊 Relatório de Análise"]
aba_insercao, aba_analise = st.tabs(abas)

# =====================================================================
# ABA 1: INSERÇÃO DE DADOS
# =====================================================================
with aba_insercao:
    st.header("Inserir Novo Pedido")
    
    with st.form("form_pedido", clear_on_submit=True):
        # Os valores padrões são alimentados pelo que foi clicado no Planner (se houver)
        cliente = st.text_input("Nome do Cliente")
        data_pedido = st.date_input("Data do Trabalho", value=st.session_state['planner_data'])
        
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
                    
                    st.session_state['sucesso_insercao'] = f"✅ Pedido do cliente '{cliente}' salvo com sucesso!"
                    
                    # Reseta os valores padrões após salvar
                    st.session_state['planner_data'] = datetime.today().date()
                    st.session_state['planner_inicio'] = time(7, 0)
                    st.session_state['planner_fim'] = time(19, 0)
                    st.session_state['planner_horas'] = 4.0
                    st.rerun()

    if 'sucesso_insercao' in st.session_state:
        st.success(st.session_state['sucesso_insercao'])
        del st.session_state['sucesso_insercao']

# =====================================================================
# ABA 2: ANÁLISE DOS DADOS (RELATÓRIO)
# =====================================================================
with aba_analise:
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
            CAPACIDADE_REAL_PERIODO = calcular_capacidade_real(df)
            
            col_maq = st.columns(len(horas_por_maquina))
            for i, (maquina, horas_ocupadas) in enumerate(horas_por_maquina.items()):
                with col_maq[i]:
                    horas_livres = max(0.0, CAPACIDADE_REAL_PERIODO - horas_ocupadas)
                    st.info(f"**{maquina}**")
                    st.metric("Horas Ocupadas", f"{horas_ocupadas:.1f}h")
                    st.metric("Horas Livres Totais no Período", f"{horas_livres:.1f}h")
            
            st.markdown("---")
            
            # =====================================================================
            # 📅 NOVO COMPONENTE: PLANNER / AGENDA INTERATIVA
            # =====================================================================
            st.subheader("📅 Planner de Horas Disponíveis")
            st.markdown("Abaixo estão listados os próximos dias e turnos padrão. Você pode **editar o campo de horas** e, se houver interesse, **marcar o Checkbox** da linha para enviar esses dados direto para a aba de cadastro!")
            
            # Gerando os próximos 6 dias úteis/sábados para o Planner
            hoje = datetime.today()
            lista_planner = []
            dias_gerados = 0
            contador_dias = 0
            
            while dias_gerados < 6:
                data_verificar = hoje + timedelta(days=contador_dias)
                dia_semana = data_verificar.weekday()
                
                if dia_semana <= 4: # Seg a Sex
                    lista_planner.append({"Agendar": False, "Data": data_verificar.date(), "Dia": data_verificar.strftime('%A (Seg-Sex)'), "Turno": "Integral (07h as 19h)", "Horas Disponíveis": 12.0, "Início": time(7,0), "Fim": time(19,0)})
                    dias_gerados += 1
                elif dia_semana == 5: # Sábado
                    lista_planner.append({"Agendar": False, "Data": data_verificar.date(), "Dia": data_verificar.strftime('%A (Sábado)'), "Turno": "Reduzido (07h as 13h)", "Horas Disponíveis": 6.0, "Início": time(7,0), "Fim": time(13,0)})
                    dias_gerados += 1
                contador_dias += 1
                
            df_planner = pd.DataFrame(lista_planner)
            
            # Renderiza a tabela editável (O usuário pode mudar o número de horas disponíveis)
            df_editado = st.data_editor(
                df_planner,
                hide_index=True,
                column_config={
                    "Agendar": st.column_config.CheckboxColumn("Selecionar Slot", default=False),
                    "Data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
                    "Dia": st.column_config.TextColumn("Dia da Semana", disabled=True),
                    "Turno": st.column_config.TextColumn("Turno Operacional", disabled=True),
                    "Horas Disponíveis": st.column_config.NumberColumn("Horas", min_value=0.5, max_value=12.0, step=0.5),
                    "Início": st.column_config.TimeColumn("Início", disabled=True),
                    "Fim": st.column_config.TimeColumn("Fim", disabled=True)
                },
                use_container_width=True
            )
            
            # Verifica se alguma linha foi selecionada pelo Checkbox
            linha_selecionada = df_editado[df_editado['Agendar'] == True]
            
            if not linha_selecionada.empty:
                # Captura os dados da linha que foi clicada
                slot = linha_selecionada.iloc[0]
                
                # Injeta os dados no Session State para a outra aba ler
                st.session_state['planner_data'] = slot['Data']
                st.session_state['planner_inicio'] = slot['Início']
                st.session_state['planner_fim'] = slot['Fim']
                st.session_state['planner_horas'] = float(slot['Horas Disponíveis'])
                
                st.success(f"📌 Horário selecionado: {slot['Data'].strftime('%d/%m/%Y')} das {slot['Início'].strftime('%H:%M')} às {slot['Fim'].strftime('%H:%M')} ({slot['Horas Disponíveis']}h). Vá para a aba '📝 Inserir Pedido' para concluir!")
                
                # Nota: Para trocar de aba via código 100% automático no Streamlit sem travar,
                # o usuário visualiza o aviso de sucesso e clica na aba de inserção que já estará preenchida.

            st.caption("Tradução dos Dias: Monday=Segunda, Tuesday=Terça, Wednesday=Quarta, Thursday=Quinta, Friday=Sexta, Saturday=Sábado.")
