from setuptools import setup, find_packages

setup(
    name="devmind",
    version="0.1.0",
    description="DevMind CLI",
    packages=find_packages(),
    py_modules=["cli", "main"],
    install_requires=[
        "typer",
        "rich",
        "langgraph>=0.2.28",
        "langchain-groq",
        "langchain-core>=0.3.0",
        "pydantic>=2.8.0",
        "chromadb>=0.5.0",
        "tree-sitter>=0.23.0",
        "python-dotenv>=1.0.0"
    ],
    entry_points={
        "console_scripts": [
            "devmind=cli:app",
        ],
    },
)
