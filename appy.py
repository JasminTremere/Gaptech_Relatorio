import mysql.connector
import pandas as pd

# 1. CONFIGURAÇÃO DA CONEXÃO
# Pegue essas informações no painel da HostGator / phpMyAdmin
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
        print(f"Erro ao conectar ao banco HostGator: {err}")
        return None

# -------------------------------------------------------------
# PARTE 1: INSERÇÃO DE DADOS NO BANCO
# -------------------------------------------------------------
def salvar_pedido_no_banco():
    print("\n--- INSERÇÃO DE NOVO PEDIDO ---")
    cliente = input("Nome do Cliente: ")
    data_str = input("Data (AAAA-MM-DD): ")
    horario = input("Horário (Ex: 08:00 as 12:00): ")
    horas = float(input("Quantas horas levou? "))
    
    print("Selecione a Máquina:\n1 - Erosão a Fio (R$ 120/h)\n2 - Erosão a Penetração (R$ 90/h)\n3 - Erosão a Penetração (R$ 120/h)")
    opcao = input("Opção: ")
    
    # Define máquina e valores baseados na sua regra anterior
    maquina, valor_hora = "Erosão a Fio", 120
    if opcao == '2': maquina, valor_hora = "Erosão a Penetração", 90
    elif opcao == '3': maquina, valor_hora = "Erosão a Penetração", 120

    faturamento = horas * valor_hora

    # Conecta e insere
    conn = obter_conexao()
    if conn:
        cursor = conn.cursor()
        # Comando SQL (ajuste os nomes das colunas conforme sua tabela no banco)
        comando_sql = """
        INSERT INTO pedidos (cliente, data_pedido, horario, horas, maquina, valor_hora, faturamento_total)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        valores = (cliente, data_str, horario, horas, maquina, valor_hora, faturamento)
        
        cursor.execute(comando_sql, valores)
        conn.commit() # Salva as alterações no banco
        print("✅ Dados salvos com sucesso na HostGator!")
        
        cursor.close()
        conn.close()

# -------------------------------------------------------------
# PARTE 2: TRAZER DADOS DO BANCO E GERAR ANÁLISE
# -------------------------------------------------------------
def carregar_dados_e_analisar():
    conn = obter_conexao()
    if not conn:
        return
    
    # O Pandas lê a query SQL e já cria o DataFrame estruturado automaticamente
    query = "SELECT * FROM pedidos"
    df = pd.read_sql(query, con=conn)
    conn.close()

    if df.empty:
        print("O banco de dados está vazio.")
        return

    # Garante que a coluna de data está no formato correto para análise temporal
    df['data_pedido'] = pd.to_datetime(df['data_pedido'])

    print("\n==================================================")
    print("📌 RELATÓRIO ATUALIZADO VIA HOSTGATOR")
    print("==================================================")
    
    # Faturamento Semanal e Mensal
    faturamento_semanal = df.resample('W', on='data_pedido')['faturamento_total'].sum()
    faturamento_mensal = df.resample('M', on='data_pedido')['faturamento_total'].sum()
    
    print("\n💰 [FATURAMENTO SEMANAL]")
    for data, valor in faturamento_semanal.items():
        print(f"Semana terminando em {data.strftime('%d/%m/%Y')}: R$ {valor:,.2f}")
        
    print("\n📅 [FATURAMENTO MENSAL]")
    for data, valor in faturamento_mensal.items():
        print(f"Mês {data.strftime('%B/%Y')}: R$ {valor:,.2f}")

    # Análise de Clientes
    print("\n👥 [ANÁLISE DE CLIENTES]")
    pedidos_por_cliente = df['cliente'].value_counts()
    print(f"• Total de pedidos por cliente:\n{pedidos_por_cliente.to_string()}")
    print(f"• MAIS pedidos: {pedidos_por_cliente.idxmax()} ({pedidos_por_cliente.max()} pedidos)")
    print(f"• MENOS pedidos: {pedidos_por_cliente.idxmin()} ({pedidos_por_cliente.min()} pedidos)")

    # Ocupação de Máquinas
    print("\n⚙️ [TEMPO DE OCUPAÇÃO DAS MÁQUINAS]")
    horas_por_maquina = df.groupby('maquina')['horas'].sum()
    CAPACIDADE_MENSAL_ESTIMADA = 160.0 
    
    for maquina, horas_ocupadas in horas_por_maquina.items():
        horas_livres = max(0.0, CAPACIDADE_MENSAL_ESTIMADA - horas_ocupadas)
        print(f"• {maquina}:\n  - Ocupado: {horas_ocupadas}h\n  - Livre Estimado (Mês): {horas_livres}h")
    print("==================================================")

# --- MENU DE EXECUÇÃO ---
if __name__ == "__main__":
    # Exemplo de fluxo: você escolhe se quer inserir ou ver o relatório
    print("1 - Inserir Novo Pedido no Banco")
    print("2 - Gerar Relatório de Análise")
    opcao_menu = input("Escolha: ")
    
    if opcao_menu == '1':
        salvar_pedido_no_banco()
    elif opcao_menu == '2':
        carregar_dados_e_analisar()