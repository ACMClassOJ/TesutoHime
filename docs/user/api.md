# ACMOJ API

为方便第三方应用使用 ACMOJ 的功能，ACMOJ 提供了一系列 API 接口以供调用。

## 授权方式

所有 API 均通过 HTTP header 中的 Authorization 字段进行授权，格式为：

```
Authorization: Bearer acmoj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

其中 acmoj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX 为 access token。

获取 access token 有两种方式。如果您的应用程序仅供自己使用，您可以使用个人访问令牌（personal access token）。如果您的应用程序部署在互联网上，供 ACMOJ 的其他用户使用，建议使用 OAuth 获取用户的授权。

您可以在界面右上角的用户选单中选择「API」进入 API 设置界面，生成并管理个人访问令牌、管理已授权的第三方应用。

### OAuth 授权

ACMOJ 采用业界通用的 [OAuth 2.0 Authorization Code Grant][oauth2] 进行授权，流程如下：

1. 用户访问第三方应用的网站；
1. 第三方应用将用户引导至授权页面；
1. 用户点击确认授权；
1. 用户跳转回第三方应用，返回地址中带有 code；
1. 第三方应用服务端获取 code，凭 client_id, client_secret 和 code 换取 access token。

授权页面为 <https://acm.sjtu.edu.cn/OnlineJudge/oauth/authorize>，参数如下：

- response_type: 填写为“code”（不含引号）
- client_id: 必填
- redirect_uri: 必填，表示用户确认授权后返回的地址
- scope: 必填，希望获得的[授权范围](#授权范围)，以空格分隔
- state: 选填，返回 redirect_uri 时将带有 state，开发者可以利用此机制防止攻击

例如：https://acm.sjtu.edu.cn/OnlineJudge/oauth/authorize?response_type=code&client_id=XXXXXX&redirect_uri=https%3A%2F%2Fexample.com%2Fcallback&scope=user%3Aprofile%20problem%3Aread&state=YYYYYY 授权后将重定向至 https://example.com/callback?state=YYYYYY&code=ZZZZZZ 。

服务端获得 code 后，需请求 ACMOJ 服务器换取 access token；code 不是访问凭证，不能直接用于授权请求。获取 access token 的地址为 https://acm.sjtu.edu.cn/OnlineJudge/api/v1/oauth/token 。具体接口请参见 [API 详情][swagger]。code 的有效期为一分钟，请及时换取 access token。

如需获取 client_id 及 client_secret，请联系 ACMOJ 运维组。client_secret 为服务端密钥，请勿传输至前端。

### 授权范围

Access token 有一定的授权范围（scope），不同的 scope 可以使用不同的 API 接口。具体对应关系请参见 [API 详情][swagger]。建议您在使用时，根据实际使用情况，选择最小的授权范围，以保证安全性。

## 使用 API

向 API 传参一般使用 application/x-www-form-urlencoded 格式，返回的数据一般为 json 格式。

## API 详情

请参见 [API 详情][swagger]。

[oauth2]: https://www.rfc-editor.org/rfc/rfc6749#section-4.1
[swagger]: /OnlineJudge/static/api/index.html
