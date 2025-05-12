# Llama Stack 

Welcome to Llama Stack, the open-source framework for building generative AI applications.

Llama 4 is here!

Check out [Getting Started with Llama 4](<https://colab.research.google.com/github/meta-llama/llama-stack/blob/main/docs/getting_started_llama4.ipynb>)

News

Llama Stack 0.2.5 is now available! See the [release notes](<https://github.com/meta-llama/llama-stack/releases/tag/v0.2.5>) for more details.

## What is Llama Stack? 

Llama Stack defines and standardizes the core building blocks needed to bring generative AI applications to market. It provides a unified set of APIs with implementations from leading service providers, enabling seamless transitions between development and production environments. More specifically, it provides

  * **Unified API layer** for Inference, RAG, Agents, Tools, Safety, Evals, and Telemetry.

  * **Plugin architecture** to support the rich ecosystem of implementations of the different APIs in different environments like local development, on-premises, cloud, and mobile.

  * **Prepackaged verified distributions** which offer a one-stop solution for developers to get started quickly and reliably in any environment

  * **Multiple developer interfaces** like CLI and SDKs for Python, Node, iOS, and Android

  * **Standalone applications** as examples for how to build production-grade AI applications with Llama Stack

[![Llama Stack](https://llama-stack.readthedocs.io/_images/llama-stack.png) ](<https://llama-stack.readthedocs.io/_images/llama-stack.png>)

Our goal is to provide pre-packaged implementations (aka “distributions”) which can be run in a variety of deployment environments. LlamaStack can assist you in your entire app development lifecycle - start iterating on local, mobile or desktop and seamlessly transition to on-prem or public cloud deployments. At every point in this transition, the same set of APIs and the same developer experience is available.

## How does Llama Stack work? 

Llama Stack consists of a [server](<https://llama-stack.readthedocs.io/distributions/index.html>) (with multiple pluggable API [providers](<https://llama-stack.readthedocs.io/providers/index.html>)) and Client SDKs (see below) meant to be used in your applications. The server can be run in a variety of environments, including local (inline) development, on-premises, and cloud. The client SDKs are available for Python, Swift, Node, and Kotlin.

## Quick Links 

  * Ready to build? Check out the [Quick Start](<https://llama-stack.readthedocs.io/getting_started/index.html>) to get started.

  * Want to contribute? See the [Contributing](<https://llama-stack.readthedocs.io/contributing/index.html>) guide.

## Client SDKs 

We have a number of client-side SDKs available for different languages.

**Language** | **Client SDK** | **Package**  
---|---|---  
Python | [llama-stack-client-python](<https://github.com/meta-llama/llama-stack-client-python>) |   
Swift | [llama-stack-client-swift](<https://github.com/meta-llama/llama-stack-client-swift/tree/latest-release>) |   
Node | [llama-stack-client-node](<https://github.com/meta-llama/llama-stack-client-node>) |   
Kotlin | [llama-stack-client-kotlin](<https://github.com/meta-llama/llama-stack-client-kotlin/tree/latest-release>) |   
## Supported Llama Stack Implementations 

A number of “adapters” are available for some popular Inference and Vector Store providers. For other APIs (particularly Safety and Agents), we provide _reference implementations_ you can use to get started. We expect this list to grow over time. We are slowly onboarding more providers to the ecosystem as we get more confidence in the APIs.

**Inference API**

**Provider** | **Environments**  
---|---  
Meta Reference | Single Node  
Ollama | Single Node  
Fireworks | Hosted  
Together | Hosted  
NVIDIA NIM | Hosted and Single Node  
vLLM | Hosted and Single Node  
TGI | Hosted and Single Node  
AWS Bedrock | Hosted  
Cerebras | Hosted  
Groq | Hosted  
SambaNova | Hosted  
PyTorch ExecuTorch | On-device iOS, Android  
OpenAI | Hosted  
Anthropic | Hosted  
Gemini | Hosted  
  
**Vector IO API**

**Provider** | **Environments**  
---|---  
FAISS | Single Node  
SQLite-Vec | Single Node  
Chroma | Hosted and Single Node  
Milvus | Hosted and Single Node  
Postgres (PGVector) | Hosted and Single Node  
Weaviate | Hosted  
  
**Safety API**

**Provider** | **Environments**  
---|---  
Llama Guard | Depends on Inference Provider  
Prompt Guard | Single Node  
Code Scanner | Single Node  
AWS Bedrock | Hosted
