package com.parser.sql;

/**
 * Démonstration du parser SQL ANTLR.
 *
 * Cette classe montre comment utiliser le parser SQL pour:
 * - Valider des requêtes SQL
 * - Analyser et extraire des informations des requêtes
 * - Gérer les erreurs de parsing
 */
public class SQLParserDemo {

    public static void main(String[] args) {
        System.out.println("╔══════════════════════════════════════════════════════════════╗");
        System.out.println("║           SQL Parser ANTLR - Démonstration                   ║");
        System.out.println("╚══════════════════════════════════════════════════════════════╝\n");

        SQLParserUtil parserUtil = new SQLParserUtil();
        SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();

        // Exemple 1: SELECT simple
        demonstrateQuery(parserUtil, analyzer,
            "SELECT simple",
            "SELECT id, name, email FROM users WHERE active = true"
        );

        // Exemple 2: SELECT avec JOIN
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec JOIN",
            """
            SELECT u.name, o.order_date, o.total
            FROM users u
            LEFT JOIN orders o ON u.id = o.user_id
            WHERE o.total > 100
            ORDER BY o.order_date DESC
            """
        );

        // Exemple 3: SELECT avec agrégation
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec agrégation",
            """
            SELECT category, COUNT(*) as count, AVG(price) as avg_price
            FROM products
            GROUP BY category
            HAVING COUNT(*) > 5
            ORDER BY avg_price DESC
            LIMIT 10
            """
        );

        // Exemple 4: INSERT
        demonstrateQuery(parserUtil, analyzer,
            "INSERT",
            "INSERT INTO users (name, email, created_at) VALUES ('John Doe', 'john@example.com', '2024-01-15')"
        );

        // Exemple 5: UPDATE
        demonstrateQuery(parserUtil, analyzer,
            "UPDATE",
            "UPDATE products SET price = 29.99, updated_at = '2024-01-15' WHERE id = 123"
        );

        // Exemple 6: DELETE
        demonstrateQuery(parserUtil, analyzer,
            "DELETE",
            "DELETE FROM logs WHERE created_at < '2023-01-01'"
        );

        // Exemple 7: CREATE TABLE
        demonstrateQuery(parserUtil, analyzer,
            "CREATE TABLE",
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL,
                total DECIMAL(10, 2) DEFAULT 0.00,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        );

        // Exemple 8: DROP TABLE
        demonstrateQuery(parserUtil, analyzer,
            "DROP TABLE",
            "DROP TABLE IF EXISTS temp_data"
        );

        // Exemple 9: Requête invalide
        System.out.println("\n" + "─".repeat(60));
        System.out.println("📛 Test de requête invalide:");
        System.out.println("─".repeat(60));
        String invalidQuery = "SELEC * FORM users";
        System.out.println("SQL: " + invalidQuery);
        SQLParserUtil.ParseResult result = parserUtil.parse(invalidQuery);
        if (!result.isSuccess()) {
            System.out.println("❌ Erreurs détectées:");
            result.getErrors().forEach(e -> System.out.println("   • " + e));
        }

        // Exemple 10: Sous-requête IN
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec sous-requête IN",
            """
            SELECT * FROM products
            WHERE category_id IN (SELECT id FROM categories WHERE active = true)
            """
        );

        System.out.println("\n" + "═".repeat(60));
        System.out.println("Démonstration terminée!");
    }

    private static void demonstrateQuery(SQLParserUtil parserUtil,
                                          SQLQueryAnalyzer analyzer,
                                          String title,
                                          String sql) {
        System.out.println("\n" + "─".repeat(60));
        System.out.println("📋 " + title + ":");
        System.out.println("─".repeat(60));

        // Afficher la requête formatée
        String formattedSql = sql.trim().replaceAll("\\s+", " ");
        if (formattedSql.length() > 80) {
            System.out.println("SQL: " + formattedSql.substring(0, 77) + "...");
        } else {
            System.out.println("SQL: " + formattedSql);
        }

        // Valider
        boolean isValid = parserUtil.isValid(sql);
        System.out.println("Valide: " + (isValid ? "✅ Oui" : "❌ Non"));

        if (isValid) {
            // Analyser
            try {
                SQLQueryAnalyzer newAnalyzer = new SQLQueryAnalyzer();
                SQLQueryAnalyzer.QueryInfo info = newAnalyzer.analyze(sql);
                System.out.println("\n" + info);
            } catch (Exception e) {
                System.out.println("Erreur d'analyse: " + e.getMessage());
            }
        }
    }
}
