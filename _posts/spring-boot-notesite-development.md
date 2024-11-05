---
title: "NoteSite Spring Boot Project Development"
collection: Learning
type: "Programming"
permalink: /blogs/notesite-project
date: 2024-11-05
---

# NoteSite Develop


```bash
[ERROR] Errors: 
[ERROR]   NoteDbTest.testSelect » UnsatisfiedDependency Error creating bean with name 'com.edge51.notesite.NoteDbTest': Unsatisfied dependency expressed through field 'userMapper': No qualifying bean of type 'com.edge51.notesite.dao.UserMapper' available: expected at least 1 bean which qualifies as autowire candidate. Dependency annotations: {@org.springframework.beans.factory.annotation.Autowired(required=true)}
```

Reason:
the @Autowired field cannot find bean because the bean did not be reconized by the project, which should be scan by the MapperScan annotation.

solution:
1. correct the @MapperScan("com.edge5134.notesite.dao") to @MapperScan("com.edge51.notesite.dao")
2. add @Repository before UserMapper interface
