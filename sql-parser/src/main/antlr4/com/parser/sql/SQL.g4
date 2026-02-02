/**
 * Grammaire ANTLR4 pour parser SQL
 * Supporte SELECT uniquement
 */
grammar SQL;

// ============ Parser Rules ============

// Point d'entrée
sql
    : statement (SEMICOLON statement)* SEMICOLON? EOF
    ;

statement
    : selectStatement
    ;

// SELECT statement
selectStatement
    : SELECT DISTINCT? selectElements
      FROM tableSources
      whereClause?
      groupByClause?
      havingClause?
      orderByClause?
      limitClause?
    ;

selectElements
    : STAR
    | selectElement (COMMA selectElement)*
    ;

selectElement
    : expression (AS? alias)?
    ;

tableSources
    : tableSource (COMMA tableSource)*
    ;

tableSource
    : tableName (AS? alias)?
      joinClause*
    ;

joinClause
    : joinType? JOIN tableName (AS? alias)? ON expression
    ;

joinType
    : INNER
    | LEFT OUTER?
    | RIGHT OUTER?
    | FULL OUTER?
    | CROSS
    ;

whereClause
    : WHERE expression
    ;

groupByClause
    : GROUP BY expression (COMMA expression)*
    ;

havingClause
    : HAVING expression
    ;

orderByClause
    : ORDER BY orderByElement (COMMA orderByElement)*
    ;

orderByElement
    : expression (ASC | DESC)?
    ;

limitClause
    : LIMIT INTEGER (OFFSET INTEGER)?
    ;

// Expressions
expression
    : LPAREN expression RPAREN                                    # parenExpression
    | NOT expression                                              # notExpression
    | expression AND expression                                   # andExpression
    | expression OR expression                                    # orExpression
    | expression comparisonOperator expression                    # comparisonExpression
    | expression BETWEEN expression AND expression                # betweenExpression
    | expression NOT? IN LPAREN (expression (COMMA expression)* | selectStatement) RPAREN  # inExpression
    | expression NOT? LIKE expression                             # likeExpression
    | expression IS NOT? NULL                                     # isNullExpression
    | functionCall                                                # functionExpression
    | columnName                                                  # columnExpression
    | literal                                                     # literalExpression
    | STAR                                                        # starExpression
    ;

comparisonOperator
    : EQUALS
    | NOT_EQUALS
    | LESS_THAN
    | GREATER_THAN
    | LESS_THAN_OR_EQUALS
    | GREATER_THAN_OR_EQUALS
    ;

functionCall
    : functionName LPAREN (DISTINCT? expression (COMMA expression)*)? RPAREN
    ;

functionName
    : COUNT
    | SUM
    | AVG
    | MIN
    | MAX
    | UPPER
    | LOWER
    | LENGTH
    | CONCAT
    | SUBSTRING
    | TRIM
    | COALESCE
    | IDENTIFIER
    ;

literal
    : STRING
    | INTEGER
    | DECIMAL_LITERAL
    | TRUE
    | FALSE
    | NULL
    ;

tableName
    : IDENTIFIER (DOT IDENTIFIER)?
    ;

columnName
    : (IDENTIFIER DOT)? IDENTIFIER
    ;

alias
    : IDENTIFIER
    ;

// ============ Lexer Rules ============

// Mots-clés SQL
SELECT      : S E L E C T ;
FROM        : F R O M ;
WHERE       : W H E R E ;
AND         : A N D ;
OR          : O R ;
NOT         : N O T ;
IN          : I N ;
LIKE        : L I K E ;
BETWEEN     : B E T W E E N ;
IS          : I S ;
NULL        : N U L L ;
TRUE        : T R U E ;
FALSE       : F A L S E ;
AS          : A S ;
ON          : O N ;
JOIN        : J O I N ;
INNER       : I N N E R ;
LEFT        : L E F T ;
RIGHT       : R I G H T ;
FULL        : F U L L ;
OUTER       : O U T E R ;
CROSS       : C R O S S ;
GROUP       : G R O U P ;
BY          : B Y ;
HAVING      : H A V I N G ;
ORDER       : O R D E R ;
ASC         : A S C ;
DESC        : D E S C ;
LIMIT       : L I M I T ;
OFFSET      : O F F S E T ;
DISTINCT    : D I S T I N C T ;

// Fonctions
COUNT       : C O U N T ;
SUM         : S U M ;
AVG         : A V G ;
MIN         : M I N ;
MAX         : M A X ;
UPPER       : U P P E R ;
LOWER       : L O W E R ;
LENGTH      : L E N G T H ;
CONCAT      : C O N C A T ;
SUBSTRING   : S U B S T R I N G ;
TRIM        : T R I M ;
COALESCE    : C O A L E S C E ;

// Opérateurs
STAR                    : '*' ;
COMMA                   : ',' ;
DOT                     : '.' ;
SEMICOLON               : ';' ;
LPAREN                  : '(' ;
RPAREN                  : ')' ;
EQUALS                  : '=' ;
NOT_EQUALS              : '!=' | '<>' ;
LESS_THAN               : '<' ;
GREATER_THAN            : '>' ;
LESS_THAN_OR_EQUALS     : '<=' ;
GREATER_THAN_OR_EQUALS  : '>=' ;

// Littéraux
STRING
    : '\'' (~'\'' | '\'\'')* '\''
    | '"' (~'"' | '""')* '"'
    ;

INTEGER
    : DIGIT+
    ;

DECIMAL_LITERAL
    : DIGIT+ '.' DIGIT*
    | '.' DIGIT+
    ;

IDENTIFIER
    : [a-zA-Z_] [a-zA-Z0-9_]*
    | '`' (~'`')+ '`'
    | '[' (~']')+ ']'
    ;

// Fragments pour case-insensitive matching
fragment A : [aA] ;
fragment B : [bB] ;
fragment C : [cC] ;
fragment D : [dD] ;
fragment E : [eE] ;
fragment F : [fF] ;
fragment G : [gG] ;
fragment H : [hH] ;
fragment I : [iI] ;
fragment J : [jJ] ;
fragment K : [kK] ;
fragment L : [lL] ;
fragment M : [mM] ;
fragment N : [nN] ;
fragment O : [oO] ;
fragment P : [pP] ;
fragment Q : [qQ] ;
fragment R : [rR] ;
fragment S : [sS] ;
fragment T : [tT] ;
fragment U : [uU] ;
fragment V : [vV] ;
fragment W : [wW] ;
fragment X : [xX] ;
fragment Y : [yY] ;
fragment Z : [zZ] ;
fragment DIGIT : [0-9] ;

// Ignorer les espaces et commentaires
WS
    : [ \t\r\n]+ -> skip
    ;

LINE_COMMENT
    : '--' ~[\r\n]* -> skip
    ;

BLOCK_COMMENT
    : '/*' .*? '*/' -> skip
    ;
