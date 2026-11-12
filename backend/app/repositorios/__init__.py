"""Acesso a dados com SQLAlchemy.

Repositório = "como buscar/guardar", sem regra de negócio. As funções
recebem a Session e NÃO fazem commit: quem decide onde a transação começa e
termina é o serviço (um caso de uso = uma transação).
"""
