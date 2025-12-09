---
title: "NoteSite Spring Boot Project Development"
collection: Learning
type: "Programming"
permalink: /blogs/notesite-project
date: 2024-11-05
---

# NoteSite Develop


## Study Schedule

- [ ] Database CRUD
- [ ] Java Annotation
- [ ] Redis
- [ ] MySQL
- [ ] RabbitMQ
- [ ] Distributed system
- [ ] Spring Cloud
- [ ] K8S
- [ ] Istio

## Java Annotation
SpringBootApplication
- @SpringBootApplication
Spring Bean
- @Autowired
- @Component
  - @Repository
  - @Service
  - @Controller
- @RestController
- @Scope
  - sigleton
  - prototype
  - request
  - session
- @Configuration
HTTP请求
- @GetMapper
- @PostMapper
- @PutMapper
- @DeleteMapper
- @PatchMapper
前后端传值
- @Pathvariable
- @RequestParam
- @RequestBody
读取配置信息
- @Value
- @ConfigurationProperties
- @PropetySource
参数校验1 字段
- @NotEmpty 被注释的字符串的不能为 null 也不能为空
- @NotBlank 被注释的字符串非 null，并且必须包含一个非空白字符
- @Null 被注释的元素必须为 null
- @NotNull 被注释的元素必须不为 null
- @AssertTrue 被注释的元素必须为 true
- @AssertFalse 被注释的元素必须为 false
- @Pattern(regex=,flag=)被注释的元素必须符合指定的正则表达式
- @Email 被注释的元素必须是 Email 格式。
- @Min(value)被注释的元素必须是一个数字，其值必须大于等于指定的最小值
- @Max(value)被注释的元素必须是一个数字，其值必须小于等于指定的最大值
- @DecimalMin(value)被注释的元素必须是一个数字，其值必须大于等于指定的最小值
- @DecimalMax(value) 被注释的元素必须是一个数字，其值必须小于等于指定的最大值
- @Size(max=, min=)被注释的元素的大小必须在指定的范围内
- @Digits(integer, fraction)被注释的元素必须是一个数字，其值必须在可接受的范围内
- @Past被注释的元素必须是一个过去的日期
- @Future 被注释的元素必须是一个将来的日期
参数校验2 请求体


```mermaid

```

## Developer Notes

### compile error
```bash
[ERROR] Errors: 
[ERROR]   NoteDbTest.testSelect » UnsatisfiedDependency Error creating bean with name 'com.edge51.notesite.NoteDbTest': Unsatisfied dependency expressed through field 'userMapper': No qualifying bean of type 'com.edge51.notesite.dao.UserMapper' available: expected at least 1 bean which qualifies as autowire candidate. Dependency annotations: {@org.springframework.beans.factory.annotation.Autowired(required=true)}
```

Reason:
the @Autowired field cannot find bean because the bean did not be reconized by the project, which should be scan by the MapperScan annotation.

solution:
1. correct the @MapperScan("com.edge5134.notesite.dao") to @MapperScan("com.edge51.notesite.dao")
2. add @Repository before UserMapper interface

