@bp.route('/buscar-anos-escolares-grafico')
@login_required
def buscar_anos_escolares_grafico():
    """Retorna lista de anos escolares disponíveis."""
    try:
        query = """
            SELECT DISTINCT ae.nome
            FROM ano_escolar ae
            JOIN usuarios u ON u.ano_escolar_id = ae.id
            WHERE u.tipo_usuario_id = 4
            AND u.codigo_ibge = :codigo_ibge
            ORDER BY ae.nome
        """
        
        result = db.session.execute(text(query), {'codigo_ibge': current_user.codigo_ibge})
        anos = [row[0] for row in result]
        
        return jsonify(anos)
    except Exception as e:
        print(f"Erro ao buscar anos escolares: {str(e)}")
        return jsonify({'error': str(e)}), 500
