import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime, time

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

# Função para calcular a capacidade real de horas com base nos dias úteis e sábados
def calcular_capacidade_real(df_pedidos):
    if df_pedidos.empty:
        return 160.0
    
    # Descobre o período dos dados cadastrados
    data_minima = df_pedidos['data_pedido'].min()
    data_maxima = df_pedidos['data_pedido'].max()
    
    # Gera todos os dias entre a menor e a maior data
    todos_os_dias = pd.date_range(start=data_minima, end=data_maxima)
    
    total_horas_capacidade = 0.0
    for dia in todos_os_dias:
        dia_semana = dia.weekday() # 0 = Segunda, 4 = Sexta, 5 = Sábado, 6 = Domingo
        
        if dia_semana <= 4: # Segunda a Sexta
            total_horas_capacidade += 12.0 # 07h às 19h = 12 horas
        elif dia_semana == 5: # Sábado
            total_horas_capacidade += 6.0 # 07h às 13h = 6 horas
            
    return max(total_horas_capacidade, 12.0) # Garante um mínimo para não zerar

# Criando as duas abas no topo da página do Streamlit
aba_insercao, aba_analise = st.tabs(["📝 Inserir Pedido", "📊 Relatório de Análise"])

# =====================================================================
# ABA 1: INSERÇÃO DE DADOS
# =====================================================================
with aba_insercao:
    st.header("Inserir Novo Pedido")
    
    with st.form("form_pedido", clear_on_submit=True):
        cliente = st.text_input("Nome do Cliente")
        data_pedido = st.date_input("Data do Trabalho", value=datetime.today())
        
        # Horários operacionais padrões sugeridos
        col_horario1, col_horario2 = st.columns(2)
        with col_horario1:
            hora_inicio = st.time_input("Horário de Início", value=time(7, 0))
        with col_horario2:
            hora_fim = st.time_input("Horário de Término", value=time(19, 0))
            
        horas = st.number_input("Quantas horas levou?", min_value=0.1, max_value=24.0, value=4.0, step=0.5)
        
        maquina_opcao = st.selectbox(
            "Selecione a Máquina",
            ["Erosão a Fio (R$ 120/h)", "Erosão a Penetração (R$ 90/h)", "Erosão a Penetração (R$ 120/h)"]
        )
        
        submetido = st.form_submit_button("Salvar Pedido no Banco de Dados")
        
        if submetido:
            dia_da_semana = data_pedido.weekday() # 0=Segunda, 5=Sábado, 6=Domingo
            
            # --- VALIDAÇÕES DE HORÁRIO DA EMPRESA ---
            if not cliente:
                st.warning("Por favor, digite o nome do cliente.")
            elif dia_da_semana == 6:
                st.error("❌ Não é permitido cadastrar trabalhos aos Domingos. A empresa opera de segunda a sábado.")
            elif dia_da_semana == 5 and (hora_inicio < time(7, 0) or hora_fim > time(13, 0)):
                st.warning("⚠️ Atenção: O horário padrão de sábado é das 07h às 13h. Verifique se os dados estão corretos.")
                # Permite salvar mesmo assim caso seja uma exceção real, removendo o "elif" se preferir bloquear totalmente
            elif hora_inicio < time(7, 0) or hora_fim > time(19, 0):
                st.warning("⚠️ Atenção: O horário de expediente padrão é das 07h às 19h.")
            
            if cliente and dia_da_semana != 6:
                # Trata a escolha da máquina
                if "Fio" in maquina_opcao:
                    maquina, valor_hora = "Erosão a Fio", 120
                elif "90" in maquina_opcao:
                    maquina, valor_hora = "Erosão a Penetração", 90
                else:
                    maquina, valor_hora = "Erosão a Penetração", 120
                    
                faturamento_total = horas * valor_hora
                horario_string = f"{hora_inicio.strftime('%H:%M')} as {hora_fim.strftime('%H:%M')}"
                
                # Inserindo no banco
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
            
            # --- Bloco de Máquinas (Dinamizado pelas novas regras) ---
            st.subheader("⚙️ Tempo de Ocupação das Máquinas")
            horas_por_maquina = df.groupby('maquina')['horas'].sum()
            
            # Calcula a capacidade com base na regra de 12h (seg-sex) e 6h (sáb)
            CAPACIDADE_REAL_PERIODO = calcular_capacidade_real(df)
            
            col_maq = st.columns(len(horas_por_maquina))
            for i, (maquina, horas_ocupadas) in enumerate(horas_por_maquina.items()):
                with col_maq[i]:
                    # Tempo livre é a capacidade real total calculada menos o que já foi trabalhado
                    horas_livres = max(0.0, CAPACIDADE_REAL_PERIODO - horas_ocupadas)
                    st.info(f"**{maquina}**")
                    st.metric("Horas Ocupadas", f"{horas_ocupadas:.1f}h")
                    st.metric("Horas Livres Totais no Período", f"{horas_livres:.1f}h")
            
            st.caption(f"ℹ️ O tempo livre é baseado na capacidade operacional da empresa para o intervalo de datas detectado (Seg-Sex: 12h/dia | Sáb: 6h/dia).")
