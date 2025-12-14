#!/usr/bin/env sh

# 确保脚本抛出遇到的错误
set -e

# 获取提交信息
Change=$1

# 如果没有传递提交信息，提醒并退出
if [ -z "$Change" ]; then
  echo "错误: 提交信息不能为空"
  exit 1
fi

# 添加所有变更文件
git add -A

# 执行提交
git commit -m "$Change"

# 推送到远程仓库
git push
