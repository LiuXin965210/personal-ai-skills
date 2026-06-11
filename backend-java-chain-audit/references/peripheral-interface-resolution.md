# 外围接口解析规则

## 目标

每个外围调用必须尽可能产出以下四个可复查事实：

1. 完整服务名。
2. 客户端类和方法。
3. HTTP 方法。
4. 完整接口路径。

Java 方法名和中文用途只能作为辅助字段，不能替代接口路径。

## Feign 解析

1. 从业务调用点确定注入字段的静态类型和实际方法，例如 `stockFeign.iprpUpdate(...)` -> `StockFeign.iprpUpdate`。
2. 打开 Feign 接口，读取 `@FeignClient` 的 `value`、`name`、`url`、`path`。
3. 读取 Feign 接口上的类级 `@RequestMapping`。
4. 读取目标方法上的 `@GetMapping`、`@PostMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping` 或 `@RequestMapping`。
5. 按 URL 中已有的 path + `@FeignClient.path` + 类级 Mapping + 方法级 Mapping 拼接路径，合并重复 `/`，保留开头 `/`。
6. `@RequestMapping(method = RequestMethod.POST)` 解析为 `POST`；未声明 method 时写 `未声明（RequestMapping）`。
7. 方法路径使用常量时追到常量定义；无法解析时保留表达式并标记待确认。

示例：

```java
@FeignClient(value = "${ylh.cloud.service.stock}/api")
interface StockFeign {
  @PostMapping("/composite/stock/iprp/iprp-update")
  Result iprpUpdate(...);
}
```

输出：

| 完整服务名 | 服务配置/地址证据 | 客户端类/方法 | HTTP方法 | 完整接口路径 |
|---|---|---|---|---|
| `ylh-cloud-service-stock` | `${ylh.cloud.service.stock}/api`；本地同名工程 | `StockFeign.iprpUpdate` | `POST` | `/api/composite/stock/iprp/iprp-update` |

## 服务完整名称解析优先级

按以下顺序取证，尽量使用两种证据交叉确认：

1. 当前环境配置文件或配置中心导出中的实际服务地址、注册名。
2. 对端工程的 `spring.application.name`。
3. 本地后端工程根目录中的工程目录名。
4. `@FeignClient` 的固定 `name/value`。
5. 配置占位符语义推断。

JSH/YLH 常见推断规则：

- `${ylh.cloud.service.goods}` -> 候选 `ylh-cloud-service-goods`。
- `${ylh.cloud.service.stock}` -> 候选 `ylh-cloud-service-stock`。
- `${ylh.cloud.service.user}` -> 候选 `ylh-cloud-service-user`。
- `${ylh.cloud.service.base}` -> 候选 `ylh-cloud-service-base`。

只有占位符推断而没有配置值、`spring.application.name` 或本地同名工程佐证时，写成 `推断：ylh-cloud-service-xxx`，状态保持 `待确认`。

不要使用业务域简称冒充服务完整名称，例如 `goods`、`stock`、`fund`、`OMS order`。

## 其他 HTTP 客户端

- `RestTemplate`：解析 `getForObject`、`postForObject`、`exchange` 等调用的 URL；追踪 URI 变量和常量。
- `WebClient`：合并 `baseUrl` 与 `.uri(...)`，HTTP 方法取 `.get()`、`.post()` 等。
- Retrofit/OkHttp/Apache HttpClient：解析注解或 Request 构造器中的 method、base URL 和 path。
- 自定义 wrapper/OpenAPI client：继续打开实现类，直到找到上述标准客户端、SDK 注解或实际 URL。不能停在 `getDistributionPrice` 之类 wrapper 方法名。

## Dubbo 和其他 RPC

Dubbo 没有 HTTP 路径时，不伪造 URL。输出：

- 完整服务名：应用名或注册服务名。
- 客户端类/方法：接口全限定名 + 方法。
- HTTP方法：`不适用（Dubbo/RPC）`。
- 完整接口路径：`不适用（Dubbo/RPC）`。
- 额外记录 group、version、interfaceName。

## 完成判定

满足以下任一情况才可将单行外围接口标记为 `已确认`：

- HTTP 调用已确认完整服务名、客户端类/方法、HTTP 方法和完整路径。
- 非 HTTP RPC 已确认协议、完整服务名、接口和方法，并明确标记 HTTP 字段不适用。

存在以下情况时必须标记 `待确认`：

- 只有 Java 方法名，没有 Mapping/URL。
- 只有中文接口用途，没有具体路径。
- 只知道业务域简称，不知道服务完整名。
- 类级 `/api`、Feign `path` 或 base URL 是否应拼接尚未确认。
- 多个接口被合并成一条概括描述。
