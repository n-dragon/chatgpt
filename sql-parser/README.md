# SQL Parser avec ANTLR4

Un parser SQL généré avec ANTLR4 en Java. Ce projet permet de parser, valider et analyser des requêtes SQL SELECT.

## Fonctionnalités

### Requêtes supportées

- **SELECT** : avec JOIN, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT, sous-requêtes

### Fonctions SQL supportées

- Agrégation : `COUNT`, `SUM`, `AVG`, `MIN`, `MAX`
- Chaînes : `UPPER`, `LOWER`, `LENGTH`, `CONCAT`, `SUBSTRING`, `TRIM`
- Utilitaires : `COALESCE`

## Prérequis

- Java 11 ou supérieur
- Maven 3.6+

## Installation

```bash
# Cloner le repository
git clone <repository-url>
cd sql-parser

# Compiler le projet (génère automatiquement le parser ANTLR)
mvn clean package
```

## Utilisation

### Exécuter la démonstration

```bash
java -jar target/sql-parser-1.0.0.jar
```

### Utilisation programmatique

#### Valider une requête SQL

```java
import com.parser.sql.SQLParserUtil;

SQLParserUtil parser = new SQLParserUtil();

// Validation simple
boolean isValid = parser.isValid("SELECT * FROM users WHERE id = 1");
System.out.println("Valide: " + isValid);

// Avec détails des erreurs
SQLParserUtil.ParseResult result = parser.parse("SELEC * FROM users");
if (!result.isSuccess()) {
    result.getErrors().forEach(System.out::println);
}
```

#### Analyser une requête SQL

```java
import com.parser.sql.SQLQueryAnalyzer;
import com.parser.sql.SQLQueryAnalyzer.QueryInfo;

SQLQueryAnalyzer analyzer = new SQLQueryAnalyzer();
QueryInfo info = analyzer.analyze("""
    SELECT u.name, COUNT(o.id) as order_count
    FROM users u
    LEFT JOIN orders o ON u.id = o.user_id
    WHERE u.active = true
    GROUP BY u.name
    HAVING COUNT(o.id) > 5
    ORDER BY order_count DESC
    LIMIT 10
    """);

System.out.println("Type: " + info.getStatementType());     // SELECT
System.out.println("Tables: " + info.getTables());          // [users, orders]
System.out.println("Has WHERE: " + info.hasWhere());        // true
System.out.println("Has GROUP BY: " + info.hasGroupBy());   // true
System.out.println("Limit: " + info.getLimit());            // 10
System.out.println("Functions: " + info.getFunctions());    // [COUNT]
```

#### Mode strict (avec exceptions)

```java
SQLParserUtil strictParser = new SQLParserUtil().throwOnError(true);

try {
    strictParser.parse("INVALID SQL");
} catch (SQLParserUtil.SQLParseException e) {
    System.err.println("Erreur: " + e.getMessage());
}
```

#### Utiliser un Visitor personnalisé

```java
import com.parser.sql.SQLBaseVisitor;
import com.parser.sql.SQLParser;

public class MyVisitor extends SQLBaseVisitor<String> {
    @Override
    public String visitSelectStatement(SQLParser.SelectStatementContext ctx) {
        // Logique personnalisée
        return "Found SELECT statement";
    }
}

SQLParserUtil parser = new SQLParserUtil();
String result = parser.parseAndVisit("SELECT * FROM users", new MyVisitor());
```

## Structure du projet

```
sql-parser/
├── pom.xml
├── README.md
└── src/
    ├── main/
    │   ├── antlr4/
    │   │   └── com/parser/sql/
    │   │       └── SQL.g4              # Grammaire ANTLR
    │   └── java/
    │       └── com/parser/sql/
    │           ├── SQLParserUtil.java      # Utilitaire de parsing
    │           ├── SQLQueryAnalyzer.java   # Analyseur de requêtes
    │           └── SQLParserDemo.java      # Démonstration
    └── test/
        └── java/
            └── com/parser/sql/
                └── SQLParserTest.java      # Tests unitaires
```

## Développement

### Générer le parser depuis la grammaire

```bash
mvn generate-sources
```

Les classes générées seront dans `target/generated-sources/antlr4/`:
- `SQLLexer.java` - Analyseur lexical
- `SQLParser.java` - Parseur syntaxique
- `SQLListener.java` - Interface listener
- `SQLVisitor.java` - Interface visitor
- `SQLBaseListener.java` - Implémentation de base du listener
- `SQLBaseVisitor.java` - Implémentation de base du visitor

### Exécuter les tests

```bash
mvn test
```

### Créer le JAR exécutable

```bash
mvn package
```

## Exemples de requêtes supportées

```sql
-- SELECT simple
SELECT * FROM users WHERE active = true;

-- SELECT avec jointures
SELECT u.name, o.order_date, p.product_name
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
INNER JOIN products p ON o.product_id = p.id
WHERE u.active = true AND o.total > 100
ORDER BY o.order_date DESC
LIMIT 50;

-- SELECT avec agrégation
SELECT category, COUNT(*) as count, AVG(price) as avg_price
FROM products
GROUP BY category
HAVING COUNT(*) > 5
ORDER BY avg_price DESC;

-- Sous-requête
SELECT * FROM products
WHERE category_id IN (
    SELECT id FROM categories WHERE active = true
);

-- SELECT avec fonctions
SELECT UPPER(name), LOWER(email), COALESCE(nickname, name)
FROM users
WHERE LENGTH(name) > 3;
```

## Licence

MIT License
