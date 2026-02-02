package com.parser.sql;

import org.antlr.v4.runtime.tree.ParseTree;
import java.util.*;

/**
 * Analyseur de requêtes SQL utilisant le pattern Visitor.
 * Extrait des informations utiles des requêtes SQL parsées.
 */
public class SQLQueryAnalyzer extends SQLBaseVisitor<Void> {

    private final QueryInfo queryInfo = new QueryInfo();

    /**
     * Analyse une requête SQL et retourne les informations extraites.
     *
     * @param sql La requête SQL à analyser
     * @return Les informations de la requête
     */
    public QueryInfo analyze(String sql) {
        SQLParserUtil parser = new SQLParserUtil();
        SQLParserUtil.ParseResult result = parser.parse(sql);

        if (!result.isSuccess()) {
            throw new SQLParserUtil.SQLParseException(
                "Erreur de parsing: " + String.join(", ", result.getErrors())
            );
        }

        visit(result.getParseTree());
        return queryInfo;
    }

    @Override
    public Void visitSelectStatement(SQLParser.SelectStatementContext ctx) {
        queryInfo.setStatementType(StatementType.SELECT);
        queryInfo.setDistinct(ctx.DISTINCT() != null);
        return visitChildren(ctx);
    }

    @Override
    public Void visitTableName(SQLParser.TableNameContext ctx) {
        String tableName = ctx.getText();
        queryInfo.addTable(tableName);
        return null;
    }

    @Override
    public Void visitColumnName(SQLParser.ColumnNameContext ctx) {
        String columnName = ctx.getText();
        queryInfo.addColumn(columnName);
        return null;
    }

    @Override
    public Void visitJoinClause(SQLParser.JoinClauseContext ctx) {
        JoinInfo joinInfo = new JoinInfo();

        if (ctx.joinType() != null) {
            joinInfo.setJoinType(ctx.joinType().getText().toUpperCase());
        } else {
            joinInfo.setJoinType("INNER");
        }

        if (ctx.tableName() != null) {
            joinInfo.setTableName(ctx.tableName().getText());
        }

        queryInfo.addJoin(joinInfo);
        return visitChildren(ctx);
    }

    @Override
    public Void visitWhereClause(SQLParser.WhereClauseContext ctx) {
        queryInfo.setHasWhere(true);
        return visitChildren(ctx);
    }

    @Override
    public Void visitGroupByClause(SQLParser.GroupByClauseContext ctx) {
        queryInfo.setHasGroupBy(true);
        return visitChildren(ctx);
    }

    @Override
    public Void visitHavingClause(SQLParser.HavingClauseContext ctx) {
        queryInfo.setHasHaving(true);
        return visitChildren(ctx);
    }

    @Override
    public Void visitOrderByClause(SQLParser.OrderByClauseContext ctx) {
        queryInfo.setHasOrderBy(true);
        return visitChildren(ctx);
    }

    @Override
    public Void visitLimitClause(SQLParser.LimitClauseContext ctx) {
        queryInfo.setHasLimit(true);
        if (ctx.INTEGER() != null && !ctx.INTEGER().isEmpty()) {
            queryInfo.setLimit(Integer.parseInt(ctx.INTEGER(0).getText()));
        }
        return null;
    }

    @Override
    public Void visitFunctionCall(SQLParser.FunctionCallContext ctx) {
        String functionName = ctx.functionName().getText().toUpperCase();
        queryInfo.addFunction(functionName);
        return visitChildren(ctx);
    }

    /**
     * Types de statements SQL supportés.
     */
    public enum StatementType {
        SELECT, UNKNOWN
    }

    /**
     * Informations sur une jointure.
     */
    public static class JoinInfo {
        private String joinType;
        private String tableName;

        public String getJoinType() { return joinType; }
        public void setJoinType(String joinType) { this.joinType = joinType; }
        public String getTableName() { return tableName; }
        public void setTableName(String tableName) { this.tableName = tableName; }

        @Override
        public String toString() {
            return joinType + " JOIN " + tableName;
        }
    }

    /**
     * Classe contenant les informations extraites d'une requête SQL.
     */
    public static class QueryInfo {
        private StatementType statementType = StatementType.UNKNOWN;
        private final Set<String> tables = new LinkedHashSet<>();
        private final Set<String> columns = new LinkedHashSet<>();
        private final List<JoinInfo> joins = new ArrayList<>();
        private final Set<String> functions = new LinkedHashSet<>();
        private boolean hasWhere = false;
        private boolean hasGroupBy = false;
        private boolean hasHaving = false;
        private boolean hasOrderBy = false;
        private boolean hasLimit = false;
        private boolean isDistinct = false;
        private int limit = -1;

        // Getters et Setters
        public StatementType getStatementType() { return statementType; }
        public void setStatementType(StatementType type) { this.statementType = type; }

        public Set<String> getTables() { return Collections.unmodifiableSet(tables); }
        public void addTable(String table) { tables.add(table); }

        public Set<String> getColumns() { return Collections.unmodifiableSet(columns); }
        public void addColumn(String column) { columns.add(column); }

        public List<JoinInfo> getJoins() { return Collections.unmodifiableList(joins); }
        public void addJoin(JoinInfo join) { joins.add(join); }

        public Set<String> getFunctions() { return Collections.unmodifiableSet(functions); }
        public void addFunction(String function) { functions.add(function); }

        public boolean hasWhere() { return hasWhere; }
        public void setHasWhere(boolean hasWhere) { this.hasWhere = hasWhere; }

        public boolean hasGroupBy() { return hasGroupBy; }
        public void setHasGroupBy(boolean hasGroupBy) { this.hasGroupBy = hasGroupBy; }

        public boolean hasHaving() { return hasHaving; }
        public void setHasHaving(boolean hasHaving) { this.hasHaving = hasHaving; }

        public boolean hasOrderBy() { return hasOrderBy; }
        public void setHasOrderBy(boolean hasOrderBy) { this.hasOrderBy = hasOrderBy; }

        public boolean hasLimit() { return hasLimit; }
        public void setHasLimit(boolean hasLimit) { this.hasLimit = hasLimit; }

        public boolean isDistinct() { return isDistinct; }
        public void setDistinct(boolean distinct) { this.isDistinct = distinct; }

        public int getLimit() { return limit; }
        public void setLimit(int limit) { this.limit = limit; }

        @Override
        public String toString() {
            StringBuilder sb = new StringBuilder();
            sb.append("=== Analyse de la requête SQL ===\n");
            sb.append("Type: ").append(statementType).append("\n");
            sb.append("Tables: ").append(tables).append("\n");
            sb.append("Colonnes: ").append(columns).append("\n");
            if (!joins.isEmpty()) {
                sb.append("Jointures: ").append(joins).append("\n");
            }
            if (!functions.isEmpty()) {
                sb.append("Fonctions: ").append(functions).append("\n");
            }
            sb.append("Clauses: ");
            List<String> clauses = new ArrayList<>();
            if (hasWhere) clauses.add("WHERE");
            if (hasGroupBy) clauses.add("GROUP BY");
            if (hasHaving) clauses.add("HAVING");
            if (hasOrderBy) clauses.add("ORDER BY");
            if (hasLimit) clauses.add("LIMIT(" + limit + ")");
            if (isDistinct) clauses.add("DISTINCT");
            sb.append(clauses.isEmpty() ? "aucune" : String.join(", ", clauses));
            return sb.toString();
        }
    }
}
