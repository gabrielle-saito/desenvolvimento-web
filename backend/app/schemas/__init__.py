"""DTOs Pydantic: o contrato da API.

ENTRADA (herda de Entrada): extra="forbid" -> campo desconhecido vira 422.
Isso impede, por exemplo, que o cliente mande "usuario_id" tentando criar
uma reserva em nome de outra pessoa: o campo nem é aceito.

SAÍDA (herda de Saida): from_attributes -> lê o objeto ORM. O modelo do
banco nunca vai direto para a resposta; só o que está declarado aqui sai.
"""
