"""Casos de uso. Cada função pública é UMA transação:
busca no repositório -> aplica as regras do domínio -> persiste -> commit.
Erros de banco viram exceções de DOMÍNIO aqui; a camada HTTP nunca vê
IntegrityError nem StaleDataError.
"""
