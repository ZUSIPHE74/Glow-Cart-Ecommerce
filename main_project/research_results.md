# Research Results - Practical Task 2

This document provides the research findings required by the project brief regarding modern web development technologies.

## 1. Python Requests Module
The **Requests** module is a powerful and elegant HTTP library for Python. It simplifies the process of sending HTTP requests (GET, POST, PUT, DELETE, etc.) to web servers.
- **How it is used**: Developers use it to interact with web services and APIs. 
- **Example**: `requests.get('https://api.example.com/data')` returns a Response object containing the server's status code, headers, and content. It handles common tasks like authentication, cookies, and query parameters automatically.

## 2. JSON vs XML Data Formats

### JSON (JavaScript Object Notation)
A lightweight data-interchange format based on JavaScript object syntax.
- **Advantages**:
    1. Highly readable by humans and machines.
    2. Lightweight with less boilerplate than XML.
    3. Faster to parse in JavaScript environments.
    4. Supported by almost all modern programming languages.
- **Disadvantages**:
    1. Limited data types (no native support for dates or binary data).
    2. No standard schema for strict validation (unlike XSD).
    3. Does not support comments.
    4. Not as expressive as XML for document-style data.

### XML (eXtensible Markup Language)
A markup language that defines a set of rules for encoding documents.
- **Advantages**:
    1. Supports complex data structures and custom tags.
    2. Excellent for document-centric data (like word processor files).
    3. Strong validation available via DTD or XSD schemas.
    4. Unicode support is native and robust.
- **Disadvantages**:
    1. Verbose and results in larger file sizes.
    2. Slower to parse and process.
    3. Harder to read manually compared to JSON.
    4. Requires a specialized parser which can be resource-intensive.

## 3. RESTful API Overview
A **RESTful API** (Representational State Transfer) is an architectural style for providing interoperability between computer systems on the internet. It uses standard HTTP methods (GET, POST, PUT, DELETE) and operates on "resources" identified by URLs.

- **Advantages**:
    1. **Statelessness**: Each request contains all information needed to process it.
    2. **Scalability**: Decoupling client and server allows both to scale independently.
    3. **Caching**: Encourages caching of responses to improve performance.
    4. **Simplicity**: Uses standard web protocols (HTTP/HTTPS) and formats (JSON).
- **Disadvantages**:
    1. **Over-fetching**: May return more data than the client actually needs.
    2. **Under-fetching**: May require multiple requests to get related data (n+1 problem).
    3. **Statelessness Overheads**: Repeatedly sending authentication data can increase payload size.
    4. **Limited Real-time Support**: Not ideal for streaming or constant two-way communication (compared to WebSockets).
