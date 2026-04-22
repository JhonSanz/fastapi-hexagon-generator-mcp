prompt example

> Generate a CRUD module called Product using hexagonal-generator mcp. Then define its fields: name (str, max 100, searchable), price (float, required), description (str, max 500, nullable), and category (str, max 50, searchable). A product has name, price, description, and category. Add a validation for the name, it has to start with the word "PRODUCT: ". Also, generate a module named Store, Then define its fields: name (str, max 100, searchable), address (float, required), products (It is a foreign key to Product). Wire the modules and complete all remaining TODOs..
