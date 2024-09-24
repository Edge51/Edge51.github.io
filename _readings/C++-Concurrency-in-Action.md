---
title: 'C++ Concurrency in Action'
date: 2024-09-10
permalink: /software-development/reading/cpp-concurrency-in-action
tags:
  - C++
  - Concurrency
---


# Reading Note of *C++ Concurrency in Action*

![mind map](/images/readings/c++_concurrency_in_action/C++_Concurrency_in_Action.drawio.svg)

## Introduction
### thread-safe vs. re-entrant
they are independent concepts.
- re-entrant means that whenever the code is run, the code will the 

## Thread Management
### Managing threads
- init thread with fuction
- join
- detach
### Exception
- RAII
### Thread Arguments
- pass arguments like function
Always remember to check the argument passing, as the thread will copy the value to initialize the variable even you pass by reference and pointer.
Using the std::ref when you need to pass by reference.


### Transfering ownership of thread
- std::move move only class
### Choosing number of threads at runtime
- std::thread::hardware_concurrency()
### Identifying thread
- thread.id

## Sharing Data between Threads
### Race condition
- definition: multiple threads access same data, the order they access lead to undefined behaviour.
### Using mutex to avoid Race condition
- RAII
- dead lock
- exception safe
### mutex ownership transfer
- mutex is move only class
### 
## Waiting in Threads
### wait for event with condition variable
### wait for one off event
#### std::future
#### std::async
#### std::package_task
#### std::promise
### wait for particular time period
### continuation for the *then* semantic
std::experimental::future facilitate the *then* semantic with the std::experimental::future::then member function.
if you want to pass arguments to the then function, you need to capture the arguments with lambda function.
after the then function is called, the future becomes invalid. It't an one off future.
### chaining of continuations
the then return a std::experimental::future object, and therefore it can be chained into a sequential call.
beware of the std::experimental::future returns a std::experimental::future and std::experimental::shared_future returns std::experimental::shared_future
and remember the exception delivering rules in future.
### waiting multiple threads
## Memory Model in C++
