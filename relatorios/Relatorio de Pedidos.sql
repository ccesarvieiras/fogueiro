select 
	p.id as codigo_pedido, 
	c.nome as cliente, 
	c.telefone as tel_cliente, 
	'Rua: ' || l2.descricao || ', (' || c.complemento_endereco  || '), ' || l.descricao || ', - ' || c2.descricao as enderco
from 
	pedidos p	
	left join clientes c on c.id = p.cliente_id
	left join localidade l on l.id = c.localidade_id
	left join logradouro l2 on l2.id = c.logradouro_id
	left join cidade c2 on c2.id = c.cidade_id