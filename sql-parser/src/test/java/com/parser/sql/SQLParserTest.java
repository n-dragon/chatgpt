package com.parser.sql;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.DisplayName;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests unitaires pour le parser SQL.
 */
class SQLParserTest {

    private final SQLParserUtil parser = new SQLParserUtil();

    // ========== Tests SELECT ==========

    @Test
    @DisplayName("SELECT simple est valide")
    void testSimpleSelect() {
        assertTrue(parser.isValid("SELECT * FROM users"));
        assertTrue(parser.isValid("SELECT id, name FROM users"));
        assertTrue(parser.isValid("SELECT DISTINCT name FROM users"));
    }

    @Test
    @DisplayName("SELECT avec WHERE est valide")
    void testSelectWithWhere() {
        assertTrue(parser.isValid("SELECT * FROM users WHERE id = 1"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE name = 'John'"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE active = true AND age > 18"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE id IN (1, 2, 3)"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE name LIKE '%john%'"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE age BETWEEN 18 AND 65"));
        assertTrue(parser.isValid("SELECT * FROM users WHERE email IS NOT NULL"));
    }

    @Test
    @DisplayName("SELECT avec JOIN est valide")
    void testSelectWithJoin() {
        assertTrue(parser.isValid(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        ));
        assertTrue(parser.isValid(
            "SELECT * FROM users u LEFT JOIN orders o ON u.id = o.user_id"
        ));
        assertTrue(parser.isValid(
            "SELECT * FROM users u RIGHT OUTER JOIN orders o ON u.id = o.user_id"
        ));
    }

    @Test
    @DisplayName("SELECT avec GROUP BY et HAVING est valide")
    void testSelectWithGroupBy() {
        assertTrue(parser.isValid(
            "SELECT category, COUNT(*) FROM products GROUP BY category"
        ));
        assertTrue(parser.isValid(
            "SELECT category, COUNT(*) as cnt FROM products GROUP BY category HAVING COUNT(*) > 5"
        ));
    }

    @Test
    @DisplayName("SELECT avec ORDER BY et LIMIT est valide")
    void testSelectWithOrderByAndLimit() {
        assertTrue(parser.isValid("SELECT * FROM users ORDER BY name"));
        assertTrue(parser.isValid("SELECT * FROM users ORDER BY name ASC, id DESC"));
        assertTrue(parser.isValid("SELECT * FROM users ORDER BY name LIMIT 10"));
        assertTrue(parser.isValid("SELECT * FROM users LIMIT 10 OFFSET 20"));
    }

    @Test
    @DisplayName("SELECT avec fonctions est valide")
    void testSelectWithFunctions() {
        assertTrue(parser.isValid("SELECT COUNT(*) FROM users"));
        assertTrue(parser.isValid("SELECT SUM(amount), AVG(amount) FROM orders"));
        assertTrue(parser.isValid("SELECT MAX(price), MIN(price) FROM products"));
        assertTrue(parser.isValid("SELECT UPPER(name), LOWER(email) FROM users"));
        assertTrue(parser.isValid("SELECT COALESCE(nickname, name) FROM users"));
    }

    @Test
    @DisplayName("SELECT avec alias est valide")
    void testSelectWithAlias() {
        assertTrue(parser.isValid("SELECT id AS user_id, name AS user_name FROM users"));
        assertTrue(parser.isValid("SELECT u.id, u.name FROM users u"));
        assertTrue(parser.isValid("SELECT u.id, u.name FROM users AS u"));
    }

    @Test
    @DisplayName("SELECT avec sous-requête est valide")
    void testSelectWithSubquery() {
        assertTrue(parser.isValid(
            "SELECT * FROM products WHERE category_id IN (SELECT id FROM categories WHERE active = true)"
        ));
    }

    // ========== Tests d'erreur ==========

    @Test
    @DisplayName("Requêtes invalides sont détectées")
    void testInvalidQueries() {
        assertFalse(parser.isValid("SELEC * FROM users"));
        assertFalse(parser.isValid("SELECT * FORM users"));
        assertFalse(parser.isValid("SELECT FROM users"));
    }

    @Test
    @DisplayName("Parse result contient les erreurs")
    void testParseResultErrors() {
        SQLParserUtil.ParseResult result = parser.parse("SELEC * FROM users");
        assertFalse(result.isSuccess());
        assertFalse(result.getErrors().isEmpty());
    }

    @Test
    @DisplayName("throwOnError lance une exception")
    void testThrowOnError() {
        SQLParserUtil strictParser = new SQLParserUtil().throwOnError(true);
        assertThrows(SQLParserUtil.SQLParseException.class, () -> {
            strictParser.parse("INVALID SQL");
        });
    }

    // ========== Tests Analyzer ==========

    @Test
    @DisplayName("Analyzer extrait le type de requête")
    void testAnalyzerStatementType() {
        SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();

        assertEquals(SQLQueryAnalyzer.StatementType.SELECT,
            analyzer.analyze("SELECT * FROM users").getStatementType());
    }

    @Test
    @DisplayName("Analyzer extrait les tables")
    void testAnalyzerTables() {
        SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();
        SQLQueryAnalyzer.QueryInfo info = analyzer.analyze(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        );
        assertTrue(info.getTables().contains("users"));
        assertTrue(info.getTables().contains("orders"));
    }

    @Test
    @DisplayName("Analyzer détecte les clauses")
    void testAnalyzerClauses() {
        SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();
        SQLQueryAnalyzer.QueryInfo info = analyzer.analyze(
            "SELECT * FROM users WHERE active = true ORDER BY name LIMIT 10"
        );
        assertTrue(info.hasWhere());
        assertTrue(info.hasOrderBy());
        assertTrue(info.hasLimit());
        assertEquals(10, info.getLimit());
    }

    @Test
    @DisplayName("Analyzer détecte les fonctions")
    void testAnalyzerFunctions() {
        SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();
        SQLQueryAnalyzer.QueryInfo info = analyzer.analyze(
            "SELECT COUNT(*), SUM(amount), AVG(price) FROM orders"
        );
        assertTrue(info.getFunctions().contains("COUNT"));
        assertTrue(info.getFunctions().contains("SUM"));
        assertTrue(info.getFunctions().contains("AVG"));
    }

    // ========== Tests de commentaires ==========

    @Test
    @DisplayName("Commentaires sont ignorés")
    void testCommentsIgnored() {
        assertTrue(parser.isValid("SELECT * FROM users -- this is a comment"));
        assertTrue(parser.isValid("/* block comment */ SELECT * FROM users"));
        assertTrue(parser.isValid("SELECT * /* inline */ FROM users"));
    }

    // ========== Tests de multiples statements ==========

    @Test
    @DisplayName("Multiple SELECT statements sont valides")
    void testMultipleStatements() {
        assertTrue(parser.isValid("SELECT * FROM users; SELECT * FROM orders"));
    }
}
