"""Calculation tools for the chatbot."""


def sum_numbers(numbers: list[float]) -> float:
    """Sums an array of numbers.

    Args:
        numbers: A list of numbers to sum.

    Returns:
        The sum of the numbers.
    """
    return sum(numbers)


def multiply_numbers(numbers: list[float]) -> float:
    """Multiplies an array of numbers.

    Args:
        numbers: A list of numbers to multiply.

    Returns:
        The product of the numbers.
    """
    result = 1.0
    for num in numbers:
        result *= num
    return result
