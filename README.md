
### Título do Projeto: InvestIA – Assistente Inteligente para Acompanhamento de Investimentos

### Nome do Estudante: Kelvin Katsuo Alves Ida

### Curso: Engenharia de Software

### Data de Entrega: 2025

## Resumo

Este documento apresenta a proposta de desenvolvimento do InvestIA, um sistema para acompanhamento de investimentos com o auxílio de uma Inteligência Artificial baseada em agentes com LangChain. O projeto busca oferecer ao usuário uma interface interativa para o controle de sua carteira de investimentos, além de fornecer dicas e orientações baseadas em seus dados e no mercado atual. O documento abrange desde o contexto e motivação, até especificações técnicas e cronograma futuro.

## 1. Introdução

### Contexto
A crescente democratização do acesso a investimentos exige ferramentas que aliem simplicidade, inteligência e personalização. Muitos investidores iniciantes se sentem inseguros com plataformas convencionais, que carecem de orientação clara e suporte interpretativo sobre o desempenho de seus ativos.
### Justificativa
O projeto é relevante para a engenharia de software por integrar conceitos de sistemas web, inteligência artificial baseada em LLMs e arquitetura escalável, aplicando práticas modernas de desenvolvimento como o uso de agentes inteligentes via LangChain. Trata-se de uma solução inovadora e didática, aplicável em contextos reais de mercado.
### Objetivos
- **Objetivo Principal**: Desenvolver uma aplicação web com suporte de IA para auxiliar usuários no acompanhamento de seus investimentos e na tomada de decisões financeiras.
- **Objetivos Secundários**:
  - Criar um agente conversacional com LangChain.
  - Permitir o registro e visualização de ativos.
  - Oferecer dicas personalizadas com base em análises automatizadas.
  - Utilizar APIs de dados de mercado para obter informações atualizadas.

## 2. Descrição do Projeto

### Tema do Projeto
Sistema inteligente de acompanhamento de investimentos, com painel visual e assistente virtual baseado em IA. Além disso, o sistema contará com um módulo de análise automática de notícias, utilizando processamento de linguagem natural para detectar e classificar o sentimento de notícias relacionadas aos ativos da carteira do usuário. Esse recurso visa simplificar a interpretação do noticiário financeiro e fornecer contexto adicional para auxiliar nas decisões do investidor. A IA será responsável por identificar palavras-chave, extrair entidades relevantes e indicar o possível impacto das notícias.


### Problemas a Resolver
- Dificuldade dos usuários em interpretar os dados de sua carteira.
- Falta de orientação personalizada em plataformas de investimento.
- Excesso de informações técnicas não traduzidas para o usuário final.

### Limitações
- O sistema não fará recomendações de compra/venda com fins comerciais.
- Não será implementada integração com corretoras para ordens de negociação.
- O escopo se limita ao acompanhamento e análise de dados, sem movimentações financeiras reais.

## 3. Especificação Técnica

### 3.1. Requisitos de Software

#### Requisitos Funcionais (RF)
- **RF01**: Permitir cadastro e remoção de ativos na carteira.
- **RF02**: Exibir painel com gráficos de desempenho e alocação.
- **RF03**: Integrar com API de dados financeiros para cotações atualizadas.
- **RF04**: Implementar chat com IA para análise da carteira.
- **RF05**: Gerar dicas e sugestões com base nos dados do usuário.
- **RF06**: Analisar automaticamente notícias relacionadas aos ativos da carteira e classificar seu impacto (positivo, negativo ou neutro) com uso de IA.


#### Requisitos Não-Funcionais (RNF)
- **RNF01**: A interface deve ser responsiva.
- **RNF02**: A aplicação deve responder em até 2 segundos.
- **RNF03**: Os dados devem ser armazenados de forma segura.
- **RNF04**: O sistema deve suportar escalabilidade horizontal.

### 3.2. Considerações de Design

#### **Visão Inicial da Arquitetura**

O sistema será estruturado em três camadas principais:

- Front-end (React ou Streamlit)

- Back-end (Python + FastAPI)

- - Módulo IA (LangChain + GPT + ferramentas personalizadas): responsável por gerar recomendações, analisar o desempenho da carteira e realizar a análise de sentimento em notícias do mercado relacionadas aos ativos registrados.

#### **Padrões de Arquitetura**

- MVC no front-end.

- Arquitetura Orientada a Serviços (SOA) para escalabilidade.

#### **Modelos C4**

- Contexto: Usuário interage com um sistema que orquestra IA, APIs e banco de dados.

- Contêineres: Front-end, API REST, Módulo IA, Banco de Dados.

- Componentes: Painel visual, serviço de recomendação, orquestrador de agentes.

- Código: Será documentado com diagramas de sequência e estrutura.2

### 3.3. Tecnologias Utilizadas

- **Linguagem de Programação**: Python (back-end), JavaScript (front-end)
- **Framework e Bibliotecas**:
  - FastAPI, React.js.
  - LangChain, OpenAI SDK, Pandas, Matplotlib.
- **Ferramentas de Desenvolvimento**:
  - GitHub, Docker, VSCode.
  - Trello ou Notion para gestão ágil.
- **APIs externas**:
  - Yahoo Finance, Alpha Vantage, ou similares.


### 3.4. Considerações de Segurança

- **Proteção dos dados sensíveis do usuário com autenticação JWT**
- **Implementação de HTTPS para tráfego seguro.**
- **Evitar injeção de código na interação com LLMs.**
- **Validação de dados e sanitização de entradas.**

## 4. Próximos Passos

### 4.1 Portfólio I

- **Finalizar definição do escopo e requisitos.**
- **Criar primeira versão do protótipo funcional.**
- **Implementar integração básica com API de dados financeiros.**
- **Implementar primeira versão do agente com LangChain.**

### 4.2 Portfólio II

- **Aprofundar funcionalidades da IA.**
- **Desenvolver sistema de geração de dicas automatizadas.**
- **Implementar sistema de autenticação e segurança.**
- **Testar com usuários reais.**
- **Publicar MVP online e documentar no GitHub.**
- **Integrar sistema de análise de notícias com classificação de sentimento.**

## 5. Referências 

- [LangChain](https://docs.langchain.com)  
- [React.js](https://reactjs.org/)  
- [Python](https://www.python.org/)  
- [PostgreSQL](https://www.postgresql.org/docs/)  
- [FastAPI](https://fastapi.tiangolo.com/)  
- [OpenAI API](https://platform.openai.com/docs/overview)

## 6. Apêndices 

## 7. Avaliações de Professores



