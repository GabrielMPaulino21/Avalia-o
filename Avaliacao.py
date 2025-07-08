import streamlit as st
import pandas as pd
import os
import plotly.express as px

# --- CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(
    page_title="AVALIAÇÃO DE FORNECEDORES",
    page_icon="📊",
    layout="wide"
)

# --- DADOS E CONSTANTES ---
# Lista de "nomes chave" dos administradores.
ADMIN_KEYS = [('gabriel', 'paulino'), ('rodrigo', 'saito')]

EMPRESAS = [
    "ABSAFE ENGENHARIA E SEGURANCA", "ASSESSORIA TECNICA ATENE LTDA", "ATUS ENGENHARIA LDA",
    "BECOMEX CONSULTORIA LTDA", "BONA - TERCEIRIZACAO DE MAO-DE-OBRA PARA LOGISTICA LTDA",
    "CASTELL COMERCIAL DE EQUIPAMENTOS", "CAVE ENGENHARIA E OBRAS LTDA", "CHARLES ELBLINK ME",
    "CLIMAVENT COMERCIO", "CONDUTIVA ENGENHARIA ELETRICA LTDA", "COPE E CIA LTDA",
    "ENGECOMP MANUTENCAO INDUSTRIAL LTDA", "ESTRUTEZZA INDUSTRIA E COMERCIO LTDA",
    "FRM ENGENHARIA LTDA", "GIISAPTEC SOLUCOES INDUSTRIAIS LTDA", "JOSE FERNANDO ALVES JUNIOR EPP",
    "LOCALLTAINER LOCACOES DE CONTAINERS LTDA.", "M GARCIA SERRALHERIA E CALDEIRARIA LTDA",
    "MAMUTH TRANSPORTE DE MAQUINAS LTDA", "MANTEST ENGENHARIA ELETRICA LTDA",
    "MARCATO GESTAO EMPRESARIAL E TERCEIRIZACAO DE SERVICOS EIRELLI", "MENSURA ENGENHARIA LTDA",
    "MP ENGENHARIA ELETRICA LTDA.", "NOVAC CONSTRUCOES EMPREENDIMENTOS LTDA",
    "ODOURNET BRASIL LTDA.", "PEOPLE TEAM LTDA", "PROENG MONTAGENS E MANUTENCAO INDUSTRIAL LTDA",
    "RICAMIL ENGENHARIA E SERVICOS LTDA", "RIDARP CONSTRUCOES LTDA",
    "ROCKWELL AUTOMATION DO BRASIL LTDA", "RYCE ENGENHARIA & CONSTRUCAO LTDA.",
    "SGS INDUSTRIAL - INSTALACOES, TESTES E COMISSIONAMENTOS LTDA", "SICK SOLUCAO EM SENSORES LTDA",
    "SIEMENS INFRAESTRUTURA E INDUSTRIA LTDA", "SOS SERVICE COMERCIO E ENGENHARIA LTDA",
    "SPI INTEGRACAO DE SISTEMAS LTDA", "TEC AND TEC LATAM AMERICA LTDA",
    "TITAN INDUSTRIA E COMERCIO DE FERRAMENTAS E PERIFERICOS LTDA",
    "TOPICO LOCACOES DE GALPOES E EQUIPAMENTOS PARA INDUSTRIAS S.A",
    "VENDART SOLUCOES INDUSTRIAIS LTDA", "VENDOR TRADUCOES TECNICAS E COMERCIO LTDA",
    "VIVA EQUIPAMENTOS INDUSTRIAIS E COMERCIO LTDA", "WORK'S ENGENHARIA E MONTAGENS INDUSTRIAIS LTDA"
]
PERGUNTAS = {
    "SAFETY": {
        "1.1": "Accidents / near miss", "1.2": "Work Permit (LTR, PPT) performance",
        "1.3": "EHS documentation (like training certifications and clinic exams (ASO))",
        "1.4": "Leadership - Safety technician is on work execution", "1.5": "Safety audit"
    },
    "QUALITY": {
        "2.1": "Delivering jobs on time", "2.2": "Executions comply with designs",
        "2.3": "Housekeeping during work execution and after", "2.4": "Work tools condition (personal and equipments)",
        "2.5": "Delivery jobs on cost"
    },
    "PEOPLE": {
        "3.1": "Crew sizing according to approved contracts",
        "3.2": "Workteam knowledge meet the minimum technical requirements",
        "3.3": "Leadership - Supervisors is on work execution"
    },
    "DOCUMENTATION": {
        "4.1": "Supplier is following accordinly with SAM system requirements (evidences like schedules, measurements, pictures, reports, ART)",
        "4.2": "Suppliers delivery all the documentation (Company and employees) on time, according to the plan",
        "4.3": "Suppliers deliver all the project documentation required (Ex: As Built, Drawings, Data sheets, Manuals, etc)"
    }
}
OPCOES_VOTO = ['1', '2', '3', '4', '5', 'N/A']
ARQUIVO_VOTOS = 'votos.csv'

# --- FUNÇÕES DE DADOS ---
def carregar_votos():
    if os.path.exists(ARQUIVO_VOTOS):
        return pd.read_csv(ARQUIVO_VOTOS)
    else:
        return pd.DataFrame(columns=['user_name', 'empresa', 'categoria', 'pergunta_id', 'pergunta_texto', 'voto'])

# --- GERENCIAMENTO DE ESTADO E LOGIN ---
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
    st.session_state.is_admin = False

if st.session_state.user_name is None:
    st.title("Bem-vindo ao Sistema de Avaliação de Fornecedores")
    st.header("Por favor, identifique-se para continuar")
    
    with st.form("login_form"):
        nome = st.text_input("Digite seu nome completo:")
        submitted = st.form_submit_button("Entrar")
        if submitted:
            if nome:
                st.session_state.user_name = nome.strip().upper()
                
                nome_digitado_lower = st.session_state.user_name.lower()
                if any(all(key in nome_digitado_lower for key in key_tuple) for key_tuple in ADMIN_KEYS):
                    st.session_state.is_admin = True
                else:
                    st.session_state.is_admin = False
                    
                st.rerun()
            else:
                st.error("Por favor, insira seu nome para continuar.")
else:
    # --- APLICAÇÃO PRINCIPAL (APÓS LOGIN) ---
    st.title("RELATÓRIO DE VOTAÇÃO DE FORNECEDORES")

    st.sidebar.success(f"Logado como:\n**{st.session_state.user_name}**")
    if st.session_state.is_admin:
        st.sidebar.warning("👑 **Nível de Acesso:** Administrador")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.user_name = None
        st.session_state.is_admin = False
        st.rerun()

    tab_votacao, tab_relatorio, tab_dados = st.tabs(["📝 VOTAÇÃO", "📊 RELATÓRIO DE MÉDIAS", "⚙️ DADOS E ADMINISTRAÇÃO"])

    df_votos_geral = carregar_votos()

    with tab_votacao:
        st.header(f"Formulário de Avaliação - Bem-vindo(a), {st.session_state.user_name.title()}")
        st.write("Selecione um fornecedor para avaliar. Você só pode avaliar cada empresa uma única vez.")

        empresa_selecionada = st.selectbox(
            "Selecione o Fornecedor:", options=EMPRESAS, index=None, placeholder="Escolha uma empresa..."
        )

        if empresa_selecionada:
            ja_votou = not df_votos_geral[
                (df_votos_geral['user_name'] == st.session_state.user_name) &
                (df_votos_geral['empresa'] == empresa_selecionada)
            ].empty

            if ja_votou:
                st.warning(f"Você já completou a avaliação para a empresa **{empresa_selecionada}**. Para corrigir, peça a um administrador para remover sua avaliação anterior na aba de administração.")
            else:
                with st.form(key=f"form_{empresa_selecionada}", clear_on_submit=True):
                    st.subheader(f"Avaliação para: **{empresa_selecionada}**")
                    respostas = {}
                    for categoria, perguntas_categoria in PERGUNTAS.items():
                        st.markdown("---")
                        st.markdown(f"### **{categoria}**")
                        for pid, ptexto in perguntas_categoria.items():
                            respostas[f"{categoria}_{pid}"] = st.radio(f"**{pid}** - {ptexto}", OPCOES_VOTO, horizontal=True, key=f"vote_{empresa_selecionada}_{categoria}_{pid}")
                    
                    if st.form_submit_button("Registrar Avaliação"):
                        novos_votos = []
                        for chave, voto in respostas.items():
                            categoria, pid = chave.split('_')
                            novos_votos.append({
                                'user_name': st.session_state.user_name, 'empresa': empresa_selecionada, 
                                'categoria': categoria, 'pergunta_id': pid, 
                                'pergunta_texto': PERGUNTAS[categoria][pid], 'voto': voto
                            })
                        
                        df_novos_votos = pd.DataFrame(novos_votos)
                        df_votos_atualizado = pd.concat([df_votos_geral, df_novos_votos], ignore_index=True)
                        df_votos_atualizado.to_csv(ARQUIVO_VOTOS, index=False)
                        st.success(f"Avaliação para **{empresa_selecionada}** registrada com sucesso! Você pode agora avaliar outra empresa.")
                        st.rerun()

    with tab_relatorio:
        st.header("Análise de Desempenho dos Fornecedores")
        if df_votos_geral.empty:
            st.info("Ainda não há votos registrados.")
        else:
            df_calculo = df_votos_geral[df_votos_geral['voto'] != 'Não se Aplica'].copy()
            df_calculo['voto'] = pd.to_numeric(df_calculo['voto'])
            media_por_categoria = df_calculo.groupby(['empresa', 'categoria'])['voto'].mean().reset_index()
            media_por_categoria.rename(columns={'voto': 'media_avaliacao'}, inplace=True)
            
            st.subheader("Gráficos Individuais por Fornecedor")
            empresas_avaliadas = media_por_categoria['empresa'].unique()
            cols = st.columns(3)
            for i, empresa in enumerate(empresas_avaliadas):
                df_empresa = media_por_categoria[media_por_categoria['empresa'] == empresa]
                fig = px.bar(df_empresa, x='categoria', y='media_avaliacao', color='categoria', title=empresa, text_auto='.2f')
                fig.update_layout(yaxis_range=[0, 5], xaxis_title=None, yaxis_title="Média", showlegend=False, title_font_size=14, title_x=0.5)
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("Tabela Geral de Médias por Categoria")
            tabela_pivot = media_por_categoria.pivot_table(index='empresa', columns='categoria', values='media_avaliacao').round(2)
            st.dataframe(tabela_pivot, use_container_width=True)

    with tab_dados:
        st.header("Painel de Administração e Dados")
        if not st.session_state.is_admin:
            st.warning("🔒 Acesso Restrito. Apenas administradores podem visualizar esta aba.")
            st.stop()

        st.subheader("Resumo de Participação por Usuário")
        if df_votos_geral.empty:
            st.info("Nenhuma participação registrada ainda.")
        else:
            votos_por_usuario = df_votos_geral.groupby('user_name')['empresa'].unique().reset_index()
            for index, row in votos_por_usuario.iterrows():
                with st.expander(f"**{row['user_name']}** avaliou **{len(row['empresa'])}** empresa(s)"):
                    for empresa_avaliada in sorted(row['empresa']):
                        st.markdown(f"- {empresa_avaliada}")
        
        st.markdown("---")
        
        st.subheader("Administração de Avaliações (Exclusão por Usuário)")
        st.write("Use esta seção para apagar uma avaliação incorreta feita por um usuário.")
        
        if not df_votos_geral.empty:
            usuarios_com_voto = sorted(df_votos_geral['user_name'].unique())
            user_selecionado_admin = st.selectbox("1. Selecione o usuário para gerenciar:", usuarios_com_voto, index=None, placeholder="Escolha um usuário...")

            if user_selecionado_admin:
                empresas_avaliadas_pelo_user = sorted(df_votos_geral[df_votos_geral['user_name'] == user_selecionado_admin]['empresa'].unique())
                empresa_para_apagar = st.selectbox("2. Selecione a avaliação para apagar:", empresas_avaliadas_pelo_user, index=None, placeholder="Escolha uma avaliação...")

                if empresa_para_apagar:
                    st.warning(f"Atenção: Você está prestes a apagar TODOS os dados da avaliação da empresa **{empresa_para_apagar}** feita pelo usuário **{user_selecionado_admin}**. Esta ação é irreversível.")
                    if st.button(f"Confirmar Exclusão de Avaliação Individual", type="primary"):
                        df_filtrado = df_votos_geral[~((df_votos_geral['user_name'] == user_selecionado_admin) & (df_votos_geral['empresa'] == empresa_para_apagar))]
                        df_filtrado.to_csv(ARQUIVO_VOTOS, index=False)
                        st.success(f"Avaliação de '{empresa_para_apagar}' por '{user_selecionado_admin}' foi apagada com sucesso.")
                        st.rerun()
        else:
            st.info("Nenhuma avaliação para administrar no momento.")

        st.markdown("---")
        st.subheader("Visualizar Todos os Votos Registrados (Dados Brutos)")
        st.dataframe(df_votos_geral, use_container_width=True)
        
        st.markdown("---")

        # NOVO: Seção para apagar todos os dados
        st.subheader("Zona de Perigo: Apagar Todo o Histórico")
        st.warning("🚨 CUIDADO: O botão abaixo apagará **TODAS AS AVALIAÇÕES DE TODOS OS USUÁRIOS** permanentemente. Esta ação não pode ser desfeita.")
        
        if st.checkbox("Eu entendo as consequências e quero apagar todos os dados."):
            if st.button("APAGAR TODO O HISTÓRICO PERMANENTEMENTE", type="primary"):
                if os.path.exists(ARQUIVO_VOTOS):
                    os.remove(ARQUIVO_VOTOS)
                    st.success("Todo o histórico de votos foi apagado com sucesso!")
                    st.rerun()
                else:
                    st.info("Não há dados para apagar.")