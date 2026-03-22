# Autopat Minikube 部署说明

## 目标

将当前仓库以“源码挂载、不构建业务镜像”的方式部署到本机 `minikube`，统一运行在 `autopat` namespace。

## 前提

- `kubectl config current-context` 为 `minikube`
- 仓库位于 `/Users/...` 路径下，便于通过 `minikube mount` 挂载
- 已准备好 `.env` 或 `.env.autopat`

推荐至少配置：

```bash
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=你的密钥
```

脚本会优先读取 `.env.autopat`，没有时回退到 `.env`。

## 一键部署

```bash
bash scripts/deploy_autopat_minikube.sh
```

脚本会自动完成这些动作：

- 确认当前上下文为 `minikube`
- 启用 `ingress` addon
- 挂载 `/Users` 到节点内 `/minikube-users`
- 清理并停掉 `llmsafe` 的运行实例和旧 Ingress
- 创建 `autopat-env` Secret
- 用动态 `hostPath` 渲染并应用 `deploy/k8s/autopat/autopat.yaml`
- 强制滚动重启前后端，让挂载的新代码和前端构建生效
- 等待前后端 rollout 完成

## 访问与验证

- 首页：`http://127.0.0.1/`
- 健康检查：`http://127.0.0.1/api/v1/health`

常用检查：

```bash
kubectl get all -n autopat
kubectl get ingress -n autopat
kubectl get deploy -n llmsafe
```

## 持久化说明

当前部署直接挂载仓库目录，因此以下内容都会保存在本机工作区：

- `data/patent.db`
- `data/vector_db/chroma/`
- `data/cache/`
- `data/runtime/k8s/pip-cache/`
- `data/runtime/k8s/npm-cache/`
- `logs/`

后端启动时会自动执行数据库建表检查，首次启动不需要手工运行 `scripts/init_db.py`。第一次部署仍会较慢，后续部署会复用 pip/npm 缓存，但 backend venv 仍按 Pod 生命周期重建。
