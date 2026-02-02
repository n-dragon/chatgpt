package com.parser.sql;

/**
 * Démonstration du parser SQL ANTLR.
 *
 * Cette classe montre comment utiliser le parser SQL pour:
 * - Valider des requêtes SQL SELECT
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

        // Exemple 4: SELECT avec DISTINCT
        demonstrateQuery(parserUtil, analyzer,
            "SELECT DISTINCT",
            "SELECT DISTINCT category FROM products ORDER BY category"
        );

        // Exemple 5: SELECT avec plusieurs JOIN
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec plusieurs JOIN",
            """
            SELECT u.name, o.order_date, p.product_name, p.price
            FROM users u
            INNER JOIN orders o ON u.id = o.user_id
            LEFT JOIN products p ON o.product_id = p.id
            WHERE u.active = true AND o.total > 50
            ORDER BY o.order_date DESC
            """
        );

        // Exemple 6: SELECT avec sous-requête IN
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec sous-requête IN",
            """
            SELECT * FROM products
            WHERE category_id IN (SELECT id FROM categories WHERE active = true)
            """
        );

        // Exemple 7: SELECT avec fonctions
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec fonctions",
            """
            SELECT
                UPPER(name) as upper_name,
                LOWER(email) as lower_email,
                COALESCE(nickname, name) as display_name
            FROM users
            WHERE LENGTH(name) > 3
            """
        );

        // Exemple 8: SELECT avec BETWEEN et LIKE
        demonstrateQuery(parserUtil, analyzer,
            "SELECT avec BETWEEN et LIKE",
            """
            SELECT * FROM products
            WHERE price BETWEEN 10 AND 100
            AND name LIKE '%phone%'
            AND description IS NOT NULL
            """
        );

        // Exemple 9: Requête invalide
        System.out.println("\n" + "─".repeat(60));
        System.out.println("Test de requête invalide:");
        System.out.println("─".repeat(60));
        String invalidQuery = "SELEC * FORM users";
        System.out.println("SQL: " + invalidQuery);
        SQLParserUtil.ParseResult result = parserUtil.parse(invalidQuery);
        if (!result.isSuccess()) {
            System.out.println("Erreurs détectées:");
            result.getErrors().forEach(e -> System.out.println("   - " + e));
        }

        // Exemple 10: Multiple SELECT
        demonstrateQuery(parserUtil, analyzer,
            "Multiple SELECT",
            "SELECT * FROM users; SELECT * FROM products"
        );

        System.out.println("\n" + "═".repeat(60));
        System.out.println("Démonstration terminée!");
    }

    private static void demonstrateQuery(SQLParserUtil parserUtil,
                                          SQLQueryAnalyzer analyzer,
                                          String title,
                                          String sql) {
        System.out.println("\n" + "─".repeat(60));
        System.out.println(title + ":");
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
        System.out.println("Valide: " + (isValid ? "Oui" : "Non"));

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
