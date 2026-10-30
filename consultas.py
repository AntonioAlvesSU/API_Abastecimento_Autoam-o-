consultas = {
    
    
    "Abastecimentos": """	
		SELECT DISTINCT
		RPAD(l.grid::text, 9, ' ') AS indice,
		LPAD(l.nr_item::text, 1, ' ') AS "_",
		RPAD(l.grid::text, 12, ' ') AS numabast,
		LPAD(mi.info::text, 9, ' ') AS veicodigo,
		LPAD(l.nr_item::text, 6, ' ') AS tpreg,
		RPAD(l.nr_item::text, 6, '0') AS bomba,
		LPAD(l.nr_item::text, 6, ' ') AS rede,
		LPAD(%(codigo_posto)s::text, 5, ' ') AS posto,
		LPAD(pf.frota::text, 6, ' ') AS frota,

		CASE
			WHEN p.codigo = '3'   THEN 'OLEO DIESEL B COMUM S500'
			WHEN p.codigo = '1'   THEN 'GASOLINA COMUM'
			WHEN p.codigo = '2'   THEN 'ETANOL COMUM'
			WHEN p.codigo = '790' THEN 'GASOLINA ADITIVADA'
			WHEN p.codigo = '107' THEN 'OLEO DIESEL S50'
			WHEN p.codigo = '519' THEN 'OLEO DIESEL S10'
			WHEN p.codigo = '846' THEN 'ARLA 32'
		END AS Combustivel,

		LPAD(l.nr_item::text, 1, ' ') AS uve,
		RPAD(nf.placa::text, 8, ' ') AS placa,
		LPAD(l.nr_item::text, 20, ' ') AS motorista,
		RPAD(nf.km::text, 7, ' ') AS km,

		REPLACE(
			RPAD(l.quantidade::text, 10, ' '),
			'.', ','
		) AS qtd,

		REPLACE(
			RPAD(l.preco_unit::text, 10, ' '),
			'.', ','
		) AS preco_unit,

		REPLACE(
			RPAD(
				CAST(
					l.valor / NULLIF(l.quantidade, 0)
					AS NUMERIC(8,3)
				)::text,
				9,
				' '
			),
			'.', ','
		) AS pubrad,

		REPLACE(
			RPAD(l.valor::text, 14, ' '),
			'.', ','
		) AS total,

		RPAD(
			TO_CHAR(l.hora, 'DD/MM/YYYY HH24:MI:SS'),
			20,
			' '
		) AS DATABASTASTECIMENTO,

		LPAD(
			TO_CHAR(l.data, 'DD/MM/YYYY'),
			10,
			' '
		) AS DATDEB,

		LPAD(
			TO_CHAR(l.data, 'DD/MM/YYYY'),
			10,
			' '
		) AS ABTDATCRED,

		LPAD(l.nr_item::text, 15, ' ') AS ABTARQUIVO,
		LPAD(l.nr_item::text, 9, ' ') AS DIST_PERC,

		REPLACE(
			RPAD(l.quantidade::text, 10, ' '),
			'.', ','
		) AS COMB_TOTAL,

		LPAD('S', 1, ' ') AS S,

		LPAD(
			l.nr_item::text,
			18,
			' '
		) AS CD_ABAT_ANTR_VEIC,

		LPAD(
			e.nome_reduzido::text,
			19,
			' '
		) AS POSTOFANTASIA,

		RPAD(l.nr_item::text, 40, ' ') AS POSTOCIDADE,
		RPAD(l.nr_item::text, 40, ' ') AS CGC

	FROM lancto l

	INNER JOIN movto m
		ON l.mlid = m.mlid
		AND m.conta_creditar = '4.1'

	LEFT JOIN movto_info mp
		ON mp.movto = m.grid
		AND mp.tipo = 'placa'

	LEFT JOIN movto_info mk
		ON mk.movto = m.grid
		AND mk.tipo = 'km'

	LEFT JOIN movto_info mo
		ON mo.movto = m.grid
		AND mo.tipo = 'motorista'

	LEFT JOIN movto_info mi
		ON mi.movto = m.grid
		AND mi.tipo = 'frota'

	INNER JOIN empresa e
		ON l.empresa = e.grid

	INNER JOIN produto p
		ON l.produto = p.grid

	INNER JOIN pessoa pp
		ON pp.grid = m.pessoa

	LEFT JOIN pessoa_frota pf
		ON pf.frota = mi.info

	INNER JOIN nota_fiscal nf
		ON m.mlid = nf.mlid

	LEFT JOIN tipo_combustivel tc
		ON p.tipo_combustivel = tc.codigo

	WHERE
		l.data >= %(data_inicial)s
		AND l.data < (%(data_final)s::date + INTERVAL '1 day')
		AND REGEXP_REPLACE(
    		pp.cpf::text, 
      		'[^0-9]',
        		'',
				'g'
		)= %(cpf_cliente)s
		AND l.operacao = 'V';	
	
	"""
    
    
}