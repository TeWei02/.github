# 貢獻指南

感謝你願意撥空參與。這個帳號下的專案多為個人研究與實驗性質，但非常歡迎 issue 與 pull request。

## 回報問題

- 請使用 [Issue 範本](https://github.com/TeWei02/.github/tree/main/ISSUE_TEMPLATE) 開立 issue。
- 描述**可重現的步驟**、**預期行為**與**實際行為**，並附上環境資訊（作業系統、語言版本、套件管理工具）。
- 視覺或介面問題請附截圖。

## 提交 Pull Request

1. 建議先開 issue 討論方向，避免白費工。
2. 從 `main` 開分支，命名如 `fix/tcp-timeout`、`feat/quantum-grover`。
3. 提交訊息採 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:`、`fix:`、`docs:`、`refactor:`、`chore:`。
4. 保持變更聚焦，一個 PR 解決一件事。
5. 確認該專案既有的 lint 與測試通過後再送出。

## 開發環境

各專案需求不同，請先閱讀該專案的 README。常見需求為 Python 3.11+、Node.js 20+ 或 CMake 3.20+。

## 授權

除個別專案另有註明外，本帳號專案採用 MIT 授權。提交貢獻即表示你同意以相同授權釋出你的貢獻。