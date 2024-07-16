# Github 的使用记录
## 注册 Github 账号
个人开发者可免费创建 1000 个仓库（不限公有、私有），提供最多 5G 的免费代码存储空间

通过访问[ Github 首页](https://gitee.com/)，从右上角点击「注册」或点击「加入 Github」即可注册个人账号。

## 创建 Github 仓库
在注册完成并成功登录 Gitee 账号后，用户可以开始创建自己的第一个仓库。

在新建仓库页面填写仓库信息。仓库相关概念说明如下：

- **仓库名称**： 仓库的名称，用于仓库命名。
- **归属**：仓库归属账户，可以是个人账号/组织/企业中的一种，创建成功后该账户默认为仓库的拥有者（管理员）。
- **路径**：仓库的git访问路径，由用户个性地址+仓库路径名称组成。创建仓库后用户将通过该路径访问仓库。
- **仓库介绍**：仓库的简单介绍。
- **是否开源**：设置仓库是否为公开仓库，公开仓库对所有人可见，私有仓库仅限仓库成员可见。
- **选择语言**：仓库主要开发用的编程语言。
- **添加.gitignore**：系统默认提供的git忽略提交的文件模板，设置.gitignore后将默认忽略指定目录/文件到仓库。
- **添加开源许可证**：如果仓库为公开仓库，可以添加设置仓库的开源协议，作为对当前项目仓库和衍生项目仓库许可约束，开源许可证决定了该开源项目是否对商业友好。
- **Readme**：项目仓库自述文档，通常包含有软件的描述或使用的注意事项。
- **使用模板文件初始化仓库**：使用Issue或Pull Request文件模板初始化仓库。

点击「创建」，即可在Gitee上创建你的仓库。

## 提交代码
**方法1、先将仓库clone到本地，修改后再push到 Gitee 的仓库**
```
git clone XXX
```

在克隆过程中，如果仓库是一个私有仓库，将会要求用户输入 Gitee 的账号和密码。按照提示输入即可。

当然，用户也可以通过配置本地的git配置信息，执行git config命令预先配置好相关的用户信息，配置执行如下：
```
git config --global user.name "你的名字或昵称"
git config --global user.email "你的邮箱"
```

修改代码后，在仓库目录下执行下面命令
```
git add . #将当前目录所有文件添加到git暂存区
git commit -m "my first commit" #提交并备注提交信息
git push origin master #将本地提交推送到远程仓库
```

**方法2、本地初始化一个仓库，设置远程仓库地址后再做push**

和方法1的差别，在于先创建仓库。
```
git init 
git remote add origin https://gitee.com/用户个性地址/HelloGitee.git
```
这样就完成了版本的一次初始化。

接下去，进入你已经初始化好的或者克隆仓库的目录,然后执行：
```
git pull origin master
```
修改/添加文件，否则与原文件相比就没有变动。
```
git add .
git commit -m "第一次提交"
git push origin master
```
在新建仓库时，如果在 Gitee 平台仓库上已经存在 readme 或其他文件，在提交时可能会存在冲突，这时用户需要选择的是保留线上的文件或者舍弃线上的文件，如果您舍弃线上的文件，则在推送时选择强制推送，强制推送需要执行下面的命令(默认不推荐该行为)：
```
git push origin master -f
```
如果您选择保留线上的 readme 文件,则需要先执行：
```
git pull origin master
```
注意，如果是从Windows系统提交，不妨使用
```
git config --global core.autocrlf input
```
避免由于回车（CR）和换行（LF）导致的提交错误。