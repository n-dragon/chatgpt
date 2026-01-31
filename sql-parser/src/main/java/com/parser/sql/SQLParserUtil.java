package com.parser.sql;

import org.antlr.v4.runtime.*;
import org.antlr.v4.runtime.tree.*;
import java.util.List;
import java.util.ArrayList;

/**
 * Classe utilitaire pour parser des requêtes SQL avec ANTLR.
 *
 * Utilisation:
 * <pre>
 * SQLParserUtil parser = new SQLParserUtil();
 * ParseResult result = parser.parse("SELECT * FROM users WHERE id = 1");
 * if (result.isSuccess()) {
 *     // Utiliser result.getParseTree()
 * } else {
 *     // Gérer les erreurs avec result.getErrors()
 * }
 * </pre>
 */
public class SQLParserUtil {

    private boolean throwOnError = false;

    /**
     * Configure si une exception doit être levée en cas d'erreur de parsing.
     */
    public SQLParserUtil throwOnError(boolean throwOnError) {
        this.throwOnError = throwOnError;
        return this;
    }

    /**
     * Parse une requête SQL et retourne le résultat.
     *
     * @param sql La requête SQL à parser
     * @return Le résultat du parsing contenant l'arbre syntaxique ou les erreurs
     */
    public ParseResult parse(String sql) {
        ErrorListener errorListener = new ErrorListener();

        CharStream input = CharStreams.fromString(sql);
        SQLLexer lexer = new SQLLexer(input);
        lexer.removeErrorListeners();
        lexer.addErrorListener(errorListener);

        CommonTokenStream tokens = new CommonTokenStream(lexer);
        SQLParser parser = new SQLParser(tokens);
        parser.removeErrorListeners();
        parser.addErrorListener(errorListener);

        ParseTree tree = parser.sql();

        ParseResult result = new ParseResult(tree, errorListener.getErrors());

        if (throwOnError && !result.isSuccess()) {
            throw new SQLParseException("Erreur de parsing SQL: " + result.getErrors());
        }

        return result;
    }

    /**
     * Parse et visite l'arbre syntaxique avec un visitor personnalisé.
     *
     * @param sql La requête SQL à parser
     * @param visitor Le visitor à utiliser
     * @return Le résultat de la visite
     */
    public <T> T parseAndVisit(String sql, SQLVisitor<T> visitor) {
        ParseResult result = parse(sql);
        if (!result.isSuccess()) {
            throw new SQLParseException("Erreur de parsing SQL: " + result.getErrors());
        }
        return visitor.visit(result.getParseTree());
    }

    /**
     * Parse et parcourt l'arbre syntaxique avec un listener personnalisé.
     *
     * @param sql La requête SQL à parser
     * @param listener Le listener à utiliser
     */
    public void parseAndWalk(String sql, SQLListener listener) {
        ParseResult result = parse(sql);
        if (!result.isSuccess()) {
            throw new SQLParseException("Erreur de parsing SQL: " + result.getErrors());
        }
        ParseTreeWalker walker = new ParseTreeWalker();
        walker.walk(listener, result.getParseTree());
    }

    /**
     * Valide une requête SQL sans retourner l'arbre.
     *
     * @param sql La requête SQL à valider
     * @return true si la requête est valide, false sinon
     */
    public boolean isValid(String sql) {
        return parse(sql).isSuccess();
    }

    /**
     * Retourne une représentation textuelle de l'arbre syntaxique.
     *
     * @param sql La requête SQL à parser
     * @return La représentation textuelle de l'arbre
     */
    public String getParseTreeString(String sql) {
        ParseResult result = parse(sql);
        if (!result.isSuccess()) {
            return "Erreur: " + result.getErrors();
        }
        return result.getParseTree().toStringTree(new SQLParser(null));
    }

    /**
     * Classe interne pour collecter les erreurs de parsing.
     */
    private static class ErrorListener extends BaseErrorListener {
        private final List<String> errors = new ArrayList<>();

        @Override
        public void syntaxError(Recognizer<?, ?> recognizer,
                               Object offendingSymbol,
                               int line,
                               int charPositionInLine,
                               String msg,
                               RecognitionException e) {
            errors.add(String.format("Ligne %d:%d - %s", line, charPositionInLine, msg));
        }

        public List<String> getErrors() {
            return errors;
        }
    }

    /**
     * Classe représentant le résultat d'un parsing.
     */
    public static class ParseResult {
        private final ParseTree parseTree;
        private final List<String> errors;

        public ParseResult(ParseTree parseTree, List<String> errors) {
            this.parseTree = parseTree;
            this.errors = errors;
        }

        public boolean isSuccess() {
            return errors.isEmpty();
        }

        public ParseTree getParseTree() {
            return parseTree;
        }

        public List<String> getErrors() {
            return errors;
        }
    }

    /**
     * Exception levée en cas d'erreur de parsing SQL.
     */
    public static class SQLParseException extends RuntimeException {
        public SQLParseException(String message) {
            super(message);
        }
    }
}
