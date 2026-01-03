---
trigger: always_on
---

* 日本語でやりとりし、ドキュメントも日本語で記述する
* pipによるライブラリ管理とし、python3.13を利用する
* 前提とする構成はコンテナ利用型のAWS Lambda、API Gatewayとする
* IaCはCloudFormation Templateで記述する
* 高速な稼働、基盤動作も含めたオーバーヘッドの排除を強く意識して実装する。
* t_wada が推奨する開発プロセス、開発ベストプラクティスに従う
* ドキュメントは squidfunk/mkdocs-material を利用した形式で必ず出力する。
* テスト実装時、開発内容とドキュメント内容が乖離しないことを必ず確認する