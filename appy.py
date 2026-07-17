import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime

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

# Criando as duas abas no topo da página do Streamlit
aba_insercao, aba_analise = st.tabs(["📝 Inserir Pedido", "📊 Relatório de Análise"])

# =====================================================================
# ABA 1: INSERÇÃO DE DADOS
# =====================================================================
with aba_insercao:
    st.header("Inserir Novo Pedido")
    
    # Criando o formulário visual
    with st.form("form_pedido", clear_on_submit=True):
        cliente = st.text_input("Nome do Cliente")
        data_pedido = st.date_input("Data do Trabalho", value=datetime.today())
        
        # Horários
        col_horario1, col_horario2 = st.columns(2)
        with col_horario1:
            hora_inicio = st.time_input("Horário de Início", value=datetime.strptime("08:00", "%H:%M").time())
        with col_horario2:
            hora_fim = st.time_input("Horário de Término", value=datetime.strptime("12:00", "%H:%M").time())
            
        horas = st.number_input("Quantas horas levou?", min_value=0.1, max_value=24.0, value=4.0, step=0.5)
        
        # Seleção da Máquina
        maquina_opcao = st.selectbox(
            "Selecione a Máquina",
            [
                "Erosão a Fio (R$ 120/h)",
                "Erosão a Penetração (R$ 90/h)",
                "Erosão a Penetração (R$ 120/h)"
            ]
        )
        
        # Botão para enviar
        submetido = st.form_submit_button("Salvar Pedido no Banco de Dados")
        
        if submetido:
            if not cliente:
                st.warning("Por favor, digite o nome do cliente.")
            else:
                # Trata a escolha da máquina e o valor da hora
                if "Fio" in maquina_opcao:
                    maquina = "Erosão a Fio"
                    valor_hora = 120
                elif "90" in maquina_opcao:
                    maquina = "Erosão a Penetração"
                    valor_hora = 90
                else:
                    maquina = "Erosão a Penetração"
                    valor_hora = 120
                    
                faturamento_total = horas * valor_hora
                horario_string = f"{hora_inicio.strftime('%H:%M')} as {hora_fim.strftime('%H:%M')}"
                
                # Inserindo no banco
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
                    
                    st.success(f"✅ Pedido do cliente '{cliente}' salvo com sucesso!")

# =====================================================================
# ABA 2: ANÁLISE DOS DADOS (RELATÓRIO)
# =====================================================================
with aba_analise:
    st.header("Análise de Faturamento e Ocupação")
    
    # Botão para atualizar os dados manualmente se necessário
    if st.button("Atualizar Relatório 🔄"):
        st.rerun()
        
    conn = obter_conexao()
    if conn:
        query = "SELECT * FROM pedidos"
        df = pd.read_sql(query, con=conn)
        conn.close()
        
        if df.empty:
            st.info("Nenhum dado encontrado no banco de dados.")
        else:
            # Tratamento da data
            df['data_pedido'] = pd.to_datetime(df['data_pedido'])
            
            # --- Bloco de Faturamento ---
            st.subheader("💰 Faturamento")
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Faturamento Semanal**")
                faturamento_semanal = df.resample('W', on='data_pedido')['faturamento_total'].sum()
                # Mostra como tabela formatada
                df_semanal = faturamento_semanal.reset_index()
                df_semanal.columns = ['Fim da Semana', 'Faturamento (R$)']
                df_semanal['Fim da Semana'] = df_semanal['Fim da Semana'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_semanal.style.format({'Faturamento (R$)': 'R$ {:.2f}'}))
                
            with col2:
                st.markdown("**Faturamento Mensal**")
                faturamento_mensal = df.resample('M', on='data_pedido')['faturamento_total'].sum()
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
            
            # Capacidade mensal estimada (ex: 160h)
            CAPACIDADE_MENSAL = 160.0
            
            col_maq = st.columns(len(horas_por_maquina))
            for i, (maquina, horas_ocupadas) in enumerate(horas_por_maquina.items()):
                with col_maq[i]:
                    horas_livres = max(0.0, CAPACIDADE_MENSAL - horas_ocupadas)
                    st.info(f"**{maquina}**")
                    st.metric("Horas Ocupadas", f"{horas_ocupadas:.1f}h")
                    st.metric("Horas Livres Estimadas (Mês)", f"{horas_livres:.1f}h")
