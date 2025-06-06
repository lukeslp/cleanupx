def fibonacci(n):\n    """Calculate fibonacci number"""\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)\n\nprint(fibonacci(10))
