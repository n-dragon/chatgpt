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

    // ========== Tests INSERT ==========

    @Test
    @DisplayName("INSERT est valide")
    void testInsert() {
        assertTrue(parser.isValid("INSERT INTO users VALUES (1, 'John', 'john@test.com')"));
        assertTrue(parser.isValid("INSERT INTO users (name, email) VALUES ('John', 'john@test.com')"));
        assertTrue(parser.isValid(
            "INSERT INTO users (name) VALUES ('John'), ('Jane'), ('Bob')"
        ));
    }

    // ========== Tests UPDATE ==========

    @Test
    @DisplayName("UPDATE est valide")
    void testUpdate() {
        assertTrue(parser.isValid("UPDATE users SET name = 'John'"));
        assertTrue(parser.isValid("UPDATE users SET name = 'John', email = 'john@test.com'"));
        assertTrue(parser.isValid("UPDATE users SET name = 'John' WHERE id = 1"));
    }

    // ========== Tests DELETE ==========

    @Test
    @DisplayName("DELETE est valide")
    void testDelete() {
        assertTrue(parser.isValid("DELETE FROM users"));
        assertTrue(parser.isValid("DELETE FROM users WHERE id = 1"));
        assertTrue(parser.isValid("DELETE FROM users WHERE active = false AND created_at < '2020-01-01'"));
    }

    // ========== Tests CREATE TABLE ==========

    @Test
    @DisplayName("CREATE TABLE est valide")
    void testCreateTable() {
        assertTrue(parser.isValid("CREATE TABLE users (id INT, name VARCHAR(100))"));
        assertTrue(parser.isValid("CREATE TABLE IF NOT EXISTS users (id INT PRIMARY KEY)"));
        assertTrue(parser.isValid(
            "CREATE TABLE users (id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(100) NOT NULL)"
        ));
        assertTrue(parser.isValid(
            "CREATE TABLE orders (id INT, user_id INT, FOREIGN KEY (user_id) REFERENCES users(id))"
        ));
    }

    // ========== Tests DROP TABLE ==========

    @Test
    @DisplayName("DROP TABLE est valide")
    void testDropTable() {
        assertTrue(parser.isValid("DROP TABLE users"));
        assertTrue(parser.isValid("DROP TABLE IF EXISTS users"));
    }

    // ========== Tests d'erreur ==========

    @Test
    @DisplayName("Requêtes invalides sont détectées")
    void testInvalidQueries() {
        assertFalse(parser.isValid("SELEC * FROM users"));
        assertFalse(parser.isValid("SELECT * FORM users"));
        assertFalse(parser.isValid("SELECT FROM users"));
        assertFalse(parser.isValid("INSERT users VALUES (1)"));
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
        assertEquals(SQLQueryAnalyzer.StatementType.INSERT,
            new SQLQueryAnalyzer().analyze("INSERT INTO users (name) VALUES ('test')").getStatementType());
        assertEquals(SQLQueryAnalyzer.StatementType.UPDATE,
            new SQLQueryAnalyzer().analyze("UPDATE users SET name = 'test'").getStatementType());
        assertEquals(SQLQueryAnalyzer.StatementType.DELETE,
            new SQLQueryAnalyzer().analyze("DELETE FROM users").getStatementType());
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
    @DisplayName("Multiple statements sont valides")
    void testMultipleStatements() {
        assertTrue(parser.isValid("SELECT * FROM users; SELECT * FROM orders"));
        assertTrue(parser.isValid("INSERT INTO logs (msg) VALUES ('test'); DELETE FROM logs WHERE id = 1"));
    }
}
