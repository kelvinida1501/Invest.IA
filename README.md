
### Título do Projeto: InvestIA – Assistente Inteligente para Acompanhamento de Investimentos

### Nome do Estudante: Kelvin Katsuo Alves Ida

### Curso: Engenharia de Software

### Data de Entrega: 2025

## Resumo

Este documento apresenta a proposta de desenvolvimento do InvestIA, um sistema para acompanhamento de investimentos com o auxílio de uma Inteligência Artificial baseada em agentes com LangChain. O projeto busca oferecer ao usuário uma interface interativa para o controle de sua carteira de investimentos, além de fornecer dicas e orientações baseadas em seus dados e no mercado atual. O documento abrange desde o contexto e motivação, até as especificações técnicas, arquitetura da solução e cronograma de desenvolvimento.

## 1. Introdução - 

### 1.1. Contexto
O mercado financeiro brasileiro vivencia uma expansão sem precedentes no número de investidores individuais. Dados da B3 indicam que o número de pessoas físicas na bolsa ultrapassou a marca de 5 milhões, um público que, em grande parte, está em fase inicial de aprendizado. Este cenário de democratização expõe uma lacuna crítica: a carência de ferramentas que traduzam a complexidade do mercado para uma linguagem acessível. Investidores iniciantes frequentemente se deparam com o fenômeno da "infobesidade" (excesso de informação), sentindo-se inseguros com plataformas convencionais que, apesar de repletas de dados, carecem de orientação clara e suporte interpretativo sobre o desempenho de seus próprios ativos.

### 1.2. Justificativa
O desenvolvimento do InvestIA é relevante sob duas óticas principais: acadêmica e de engenharia de software.

#### Relevância para a Engenharia de Software: O projeto integra conceitos avançados e atuais, como o desenvolvimento de sistemas web reativos, a aplicação de Inteligência Artificial via LLMs (Modelos de Linguagem Ampla) e a construção de uma arquitetura de microsserviços escalável. A utilização de frameworks como FastAPI e React, em conjunto com ferramentas como Docker e LangChain para orquestração de agentes inteligentes, posiciona o projeto na vanguarda das práticas de desenvolvimento modernas.

#### Relevância Acadêmica e Inovação: A proposta inova ao ir além da tradicional análise de sentimento. Enquanto modelos como o FinBERT são eficazes na classificação de textos, a escolha por uma arquitetura baseada em LLM com LangChain permite a geração de resumos analíticos e insights contextuais, abordando o "porquê" por trás dos dados. O trabalho contribui academicamente ao explorar a engenharia de prompts e a orquestração de múltiplos agentes para resolver um problema prático no domínio financeiro, uma área de intensa pesquisa e desenvolvimento.

### 1.3. Objetivos

#### 1.3.1. Objetivo Principal
Desenvolver uma aplicação web protótipo (MVP) com suporte de Inteligência Artificial para auxiliar usuários no acompanhamento de seus investimentos, fornecendo análises contextuais e simplificadas para apoiar a tomada de decisões financeiras.

#### 1.3.2. Objetivos Secundários
OE1: Projetar e implementar um agente conversacional com LangChain, capaz de responder a perguntas sobre o desempenho e a composição da carteira do usuário.

OE2: Desenvolver um módulo de registro e visualização de ativos, permitindo que o usuário construa e acompanhe sua carteira de investimentos.

OE3: Criar um sistema de análise de notícias que utilize PLN para extrair e classificar o sentimento de informações relevantes aos ativos do usuário.

OE4: Integrar a aplicação com APIs de dados de mercado (ex: Yahoo Finance) para obter cotações e informações financeiras atualizadas.

OE5: Estruturar a aplicação em uma arquitetura de serviços escalável, utilizando FastAPI para o back-end e React para o front-end.

## 2. Descrição do Projeto

### 2.1. Tema do Projeto
Sistema inteligente de acompanhamento de investimentos, com painel visual e assistente virtual baseado em IA. O núcleo do sistema é seu módulo de análise automática de notícias, que utiliza processamento de linguagem natural para detectar e classificar o sentimento de notícias relacionadas aos ativos da carteira do usuário. Esse recurso visa simplificar a interpretação do noticiário financeiro e fornecer contexto adicional para auxiliar nas decisões do investidor. A IA será responsável por identificar palavras-chave, extrair entidades relevantes e indicar o possível impacto das notícias.

### 2.2. Problemas a Resolver
- Dificuldade dos usuários em interpretar os dados brutos de sua carteira.

- Falta de orientação personalizada e contextual em plataformas de investimento.

- Excesso de informações técnicas não traduzidas para o usuário final.

### 2.3. Limitações (Escopo Negativo)
- O sistema não fará recomendações de compra/venda de ativos.

- Não será implementada integração com corretoras para execução de ordens.

- O escopo se limita ao acompanhamento e análise de dados, sem movimentações financeiras reais.
  
## 3. Especificação Técnica

### 3.1. Requisitos de Software

#### 3.1.1. Requisitos Funcionais (RF)

- **RF01**: Permitir cadastro e remoção de ativos na carteira.
- **RF02**: Exibir painel com gráficos de desempenho e alocação.
- **RF03**: Integrar com API de dados financeiros para cotações atualizadas.
- **RF04**: Implementar chat com IA para análise da carteira.
- **RF05**: Gerar dicas e sugestões com base nos dados do usuário.
- **RF06**: Analisar automaticamente notícias relacionadas aos ativos da carteira e classificar seu impacto (positivo, negativo ou neutro) com uso de IA.


#### 3.1.2. Requisitos Não-Funcionais (RNF)
- **RNF01**: A interface deve ser responsiva.
- **RNF02**: O tempo de resposta para uma análise de IA não deve exceder 5 segundos.
- **RNF03**: Os dados do usuário e de sua carteira devem ser armazenados de forma segura no banco de dados.
- **RNF04**: O sistema deve suportar escalabilidade horizontal.

### 3.2. Considerações de Design

#### 3.2.1. Visão Geral e Padrões de Arquitetura

A solução será estruturada seguindo o padrão Arquitetura em N Camadas (N-Tier Architecture), com uma clara separação entre a camada de apresentação (Front-end), a camada de lógica de negócio (Back-end) e a camada de dados (Banco de Dados). Adicionalmente, a comunicação entre os serviços seguirá princípios da Arquitetura Orientada a Serviços (SOA), garantindo baixo acoplamento e alta coesão entre os componentes.

#### 3.2.2. Modelagem C4

Para detalhar a arquitetura, foi utilizado o Modelo C4, que permite a visualização do sistema em diferentes níveis de abstração.

- Nível 1: Contexto
Este diagrama ilustra como o Sistema InvestIA interage com seus usuários e com outros sistemas no ambiente. Ele define os limites e as principais relações do sistema.

![C1](https://github.com/user-attachments/assets/db194816-1065-4c18-bd56-6665955fe833)


- Nível 2: Contêineres
Este diagrama detalha a estrutura interna do Sistema InvestIA, mostrando os principais blocos de construção tecnológicos (contêineres), como a aplicação front-end, a API back-end e o banco de dados.

![C2](https://github.com/user-attachments/assets/f17ff4ae-5564-4c00-90c2-a0a26d7afb9e)


- Nível 3: Componentes
Este diagrama foca no contêiner "API Back-end", detalhando seus componentes internos e como eles colaboram para realizar as funcionalidades do sistema, como autenticação, gerenciamento da carteira e orquestração das análises de IA.

![C3](https://github.com/user-attachments/assets/725a0a64-aacf-4752-abf9-800f05ef1a90)

#### 3.2.3. Diagrama de Casos de Uso

![Casos de Uso](https://github.com/user-attachments/assets/2a56c292-c882-4af4-a6dd-6ca0acd97841)

### 3.3. Tecnologias Utilizadas

#### Linguagem de Programação (Back-end): Python
  
- Justificativa: Escolhido por ser a linguagem padrão da indústria para Inteligência Artificial e Ciência de Dados, oferecendo um ecossistema incomparável com bibliotecas como Pandas, NumPy e, crucialmente, LangChain. Sua sintaxe clara acelera o desenvolvimento.
- Alternativas: Node.js foi considerado, mas o ecossistema de IA em Python é mais maduro e alinhado aos objetivos do projeto.

#### Framework (Back-end): FastAPI

- Justificativa: Selecionado por sua altíssima performance (comparável a Node.js e Go), suporte nativo a operações assíncronas (essencial para lidar com chamadas de API externas), e geração automática de documentação interativa (Swagger UI), o que otimiza o desenvolvimento e teste da API.
- Alternativas: Django e Flask. FastAPI foi preferido sobre Django por ser mais leve e menos opinativo para a criação de APIs, e sobre Flask por oferecer validação de dados e suporte assíncrono de forma nativa.

#### Framework (Front-end): React.js

- Justificativa: Biblioteca líder para criação de interfaces de usuário ricas e dinâmicas (Single Page Applications). Sua arquitetura baseada em componentes facilita a manutenção e a escalabilidade da UI. Possui uma comunidade vasta e um ecossistema robusto.
- Alternativas: Streamlit, Vue.js. React foi escolhido sobre Streamlit para permitir um maior controle sobre a personalização e a complexidade da UI.

#### Orquestração de IA: LangChain

- Justificativa: Ferramenta essencial para o desenvolvimento com LLMs. Em vez de uma implementação manual, LangChain fornece uma arquitetura robusta para criar "chains" e "agentes", gerenciar prompts, ferramentas externas (como a busca de notícias) e memória de conversação. Isso reduz o código repetitivo e organiza a lógica da IA de forma modular.
- Alternativas: Implementação manual via SDK da OpenAI. LangChain foi preferido por abstrair a complexidade e promover uma arquitetura de IA mais limpa e extensível.

#### Outras Ferramentas e Bibliotecas:

- Banco de Dados: PostgreSQL, por sua robustez, confiabilidade (ACID) e escalabilidade.

- Containerização: Docker, para garantir a consistência dos ambientes de desenvolvimento e produção e simplificar o deploy.

- Controle de Versão: GitHub.

- Gestão de Projeto: Trello, para gestão ágil das tarefas.

- APIs Externas: Yahoo Finance ou similar, pela disponibilidade de um plano gratuito robusto para dados de mercado.

### 3.4. Considerações de Segurança

- **Proteção dos dados sensíveis do usuário com autenticação JWT**
- **Implementação de HTTPS para tráfego seguro.**
- **Evitar injeção de código na interação com LLMs.**
- **Validação de dados e sanitização de entradas.**

## 4. Próximos Passos

### 4.1 Portfólio I

- **Finalizar definição do escopo e requisitos.**

## 5. Referências 

- [LangChain](https://docs.langchain.com)  
- [React.js](https://reactjs.org/)  
- [Python](https://www.python.org/)  
- [PostgreSQL](https://www.postgresql.org/docs/)  
- [FastAPI](https://fastapi.tiangolo.com/)  
- [OpenAI API](https://platform.openai.com/docs/overview)

## 6. Apêndices 

## 7. Avaliações de Professores



