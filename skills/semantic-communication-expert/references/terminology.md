# 语义通信术语表

## 核心概念
- Semantic Communication（语义通信）：以"传递语义信息"而非"逐比特保真"为目标的通信范式。
- Semantic Information（语义信息）：接收端对消息含义的解读所需的信息量。
- Knowledge Graph（知识图谱）：以实体-关系三元组组织的结构化知识库，用于语义提取与对齐。
- DeepSC：基于深度学习的语义通信系统（Deep Learning enabled Semantic Communication）。
- JSCC：联合信源信道编码（Joint Source-Channel Coding）。
- Task-Oriented Communication（任务导向通信）：以目标任务完成度而非重建保真度为指标。
- Semantic Noise（语义噪声）：发送端与接收端知识/语义空间不一致引入的失真。
- SIA（Semantic Information Assurance）：语义信息可用性保证。

## 系统与评估
- Latency（时延）、Rate（速率）、Distortion（失真）
- BLEU / SentenceBLEU：文本语义相似度评估指标
- PSNR / SSIM：图像重建质量评估指标
- Task Completion Rate：任务完成率（任务导向通信指标）

## 相关技术
- Transformer、Attention Mechanism（注意力机制）
- VAE（变分自编码器）、GAN（生成对抗网络）
- RL（强化学习）用于语义编码策略优化
