import re
from typing import List, Optional, Tuple, Union

class Pila:
    def __init__(self):
        self._items = []

    def apilar(self, item):
        self._items.append(item)

    def desapilar(self):
        if self.esta_vacia():
            raise IndexError("Desbordamiento negativo: la pila está vacía.")
        return self._items.pop()

    def tope(self):
        if self.esta_vacia():
            return None
        return self._items[-1]

    def esta_vacia(self) -> bool:
        return len(self._items) == 0

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"Pila({self._items})"


class NodoAST:
    def __init__(
        self,
        valor: Union[str, float, int],
        izquierdo: Optional['NodoAST'] = None,
        derecho: Optional['NodoAST'] = None
    ):
        self.valor = valor
        self.izquierdo = izquierdo
        self.derecho = derecho

    def es_hoja(self) -> bool:
        return self.izquierdo is None and self.derecho is None


#TOKENIZACIÓN Y VALIDACIÓN SINTÁCTICA (PDA / PILA)

OPERADORES = {
    '+': {'precedencia': 1, 'asociatividad': 'L'},
    '-': {'precedencia': 1, 'asociatividad': 'L'},
    '*': {'precedencia': 2, 'asociatividad': 'L'},
    '/': {'precedencia': 2, 'asociatividad': 'L'},
    '^': {'precedencia': 3, 'asociatividad': 'R'},
}


def tokenizar(expresion: str) -> List[str]:
    patron_token = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|([\+\-\*\/\^\(\)]))')
    tokens = []
    pos = 0
    cadena = expresion.strip()

    while pos < len(cadena):
        match = patron_token.match(cadena, pos)
        if not match:
            caracter_invalido = cadena[pos]
            raise ValueError(
                f"Carácter léxico no reconocido '{caracter_invalido}' en la posición {pos}."
            )
        numero, simbolo = match.groups()
        tokens.append(numero if numero is not None else simbolo)
        pos = match.end()

    return tokens

def es_numero(token: str) -> bool:
    try:
        float(token)
        return True
    except ValueError:
        return False


def validar_pda(tokens: List[str]) -> Tuple[bool, str, str, str]:
    if not tokens:
        return False, "Vacía", "Error Sintáctico", "La expresión está vacía."

    pila_parentesis = Pila()
    estado_pila = "Correcto"
    error_parentesis_detalle = ""

    for token in tokens:
        if token == '(':
            pila_parentesis.apilar('(')
        elif token == ')':
            if pila_parentesis.esta_vacia():
                estado_pila = "Tope inválido / Desbalance"
                error_parentesis_detalle = (
                    "Se encontró ')' sin un '(' de apertura correspondiente en la pila."
                )
                break
            pila_parentesis.desapilar()

    if estado_pila == "Correcto" and not pila_parentesis.esta_vacia():
        estado_pila = "Falta )"
        error_parentesis_detalle = (
            f"Quedaron {len(pila_parentesis)} paréntesis '(' sin cerrar en la pila."
        )

    estado = "q0"
    pila_pda = Pila()
    pila_pda.apilar("Z0")

    for i, token in enumerate(tokens):
        if estado == "q0":
            if token == '(':
                pila_pda.apilar('(')
                estado = "q0"
            elif es_numero(token):
                estado = "q1"
            elif token in OPERADORES:
                return (
                    False,
                    estado_pila,
                    "Error Sintáctico",
                    f"Operador '{token}' mal ubicado en posición {i + 1} (se esperaba un operando o '(')."
                )
            elif token == ')':
                if pila_pda.tope() == "Z0":
                    return (
                        False,
                        "Tope inválido / Desbalance",
                        "Error Sintáctico",
                        f"Paréntesis de cierre ')' inválido al inicio o sin apertura previa (posición {i + 1})."
                    )
                return (
                    False,
                    estado_pila,
                    "Error Sintáctico",
                    f"Paréntesis ')' inesperado tras operador o paréntesis vacío en posición {i + 1}."
                )

        elif estado == "q1":
            if token in OPERADORES:
                estado = "q0"
            elif token == ')':
                if pila_pda.tope() == '(':
                    pila_pda.desapilar()
                    estado = "q1"
                else:
                    return (
                        False,
                        "Tope inválido / Desbalance",
                        "Error Sintáctico",
                        f"Desbalance de pila: se encontró ')' pero el tope de la pila es '{pila_pda.tope()}'."
                    )
            elif token == '(':
                return (
                    False,
                    estado_pila,
                    "Error Sintáctico",
                    f"Falta un operador antes de '(' en la posición {i + 1}."
                )
            elif es_numero(token):
                return (
                    False,
                    estado_pila,
                    "Error Sintáctico",
                    f"Dos operandos consecutivos sin operador ('{tokens[i-1]}' y '{token}')."
                )

    if estado == "q0":
        return (
            False,
            estado_pila,
            "Error Sintáctico",
            f"La expresión termina de forma incompleta tras '{tokens[-1]}'."
        )

    if pila_pda.tope() != "Z0":
        return (
            False,
            "Falta )",
            "Error Sintáctico",
            error_parentesis_detalle or "Falta ')' para vaciar la pila hasta Z0."
        )

    return True, "Correcto", "Válida", "Expresión sintácticamente válida y balanceada."


#CONSTRUCCIÓN DEL ÁRBOL DE SINTAXIS ABSTRACTA (AST)

def _reducir_subarbol(pila_operadores: Pila, pila_nodos: Pila):
    """Extrae un operador y dos operandos de las pilas para crear un subárbol."""
    operador = pila_operadores.desapilar()
    nodo_derecho = pila_nodos.desapilar()
    nodo_izquierdo = pila_nodos.desapilar()
    nuevo_nodo = NodoAST(operador, nodo_izquierdo, nodo_derecho)
    pila_nodos.apilar(nuevo_nodo)

def construir_ast(tokens: List[str]) -> NodoAST:
    pila_operadores = Pila()
    pila_nodos = Pila()

    for token in tokens:
        if es_numero(token):
            valor_num = int(token) if '.' not in token else float(token)
            pila_nodos.apilar(NodoAST(valor_num))

        elif token == '(':
            pila_operadores.apilar(token)

        elif token == ')':
            while not pila_operadores.esta_vacia() and pila_operadores.tope() != '(':
                _reducir_subarbol(pila_operadores, pila_nodos)
            pila_operadores.desapilar()  # Extrae el '(' correspondiente

        elif token in OPERADORES:
            info_actual = OPERADORES[token]
            while (
                not pila_operadores.esta_vacia()
                and pila_operadores.tope() in OPERADORES
            ):
                op_tope = pila_operadores.tope()
                info_tope = OPERADORES[op_tope]

                # Regla de precedencia y asociatividad (L vs R)
                condicion_izquierda = (
                    info_actual['asociatividad'] == 'L'
                    and info_actual['precedencia'] <= info_tope['precedencia']
                )
                condicion_derecha = (
                    info_actual['asociatividad'] == 'R'
                    and info_actual['precedencia'] < info_tope['precedencia']
                )

                if condicion_izquierda or condicion_derecha:
                    _reducir_subarbol(pila_operadores, pila_nodos)
                else:
                    break

            pila_operadores.apilar(token)

    while not pila_operadores.esta_vacia():
        _reducir_subarbol(pila_operadores, pila_nodos)

    return pila_nodos.desapilar()


#VISUALIZACIÓN JERÁRQUICA DEL AST (FORMATO ASCII)
def formatear_ast_ascii(
    nodo: Optional[NodoAST],
    prefijo: str = "",
    es_ultimo: bool = True,
    es_raiz: bool = True
) -> str:
    if nodo is None:
        return ""

    lineas = []
    if es_raiz:
        lineas.append(f"    [{nodo.valor}]")
    else:
        conector = "└── " if es_ultimo else "├── "
        lineas.append(f"{prefijo}{conector}[{nodo.valor}]")

    hijos = [h for h in (nodo.izquierdo, nodo.derecho) if h is not None]
    nuevo_prefijo = prefijo + ("    " if es_raiz else ("    " if es_ultimo else "│   "))

    for idx, hijo in enumerate(hijos):
        ultimo_hijo = (idx == len(hijos) - 1)
        lineas.append(
            formatear_ast_ascii(hijo, nuevo_prefijo, ultimo_hijo, es_raiz=False)
        )

    return "\n".join(lineas)


#EVALUACIÓN DE LA EXPRESIÓN (RECORRIDO POSTORDEN)

def evaluar_ast_postorden(nodo: NodoAST) -> Union[int, float]:
    if nodo.es_hoja():
        return nodo.valor

    val_izq = evaluar_ast_postorden(nodo.izquierdo)
    val_der = evaluar_ast_postorden(nodo.derecho)

    op = nodo.valor
    if op == '+':
        resultado = val_izq + val_der
    elif op == '-':
        resultado = val_izq - val_der
    elif op == '*':
        resultado = val_izq * val_der
    elif op == '/':
        if val_der == 0:
            raise ZeroDivisionError("Error Matemático: División entre cero no permitida.")
        resultado = val_izq / val_der
    elif op == '^':
        resultado = val_izq ** val_der
    else:
        raise ValueError(f"Operador desconocido: {op}")

    # Si el resultado es un float exacto (ej. 10.0), mostrar como entero
    if isinstance(resultado, float) and resultado.is_integer():
        return int(resultado)
    return resultado


# FUNCIÓN PRINCIPAL Y EJECUCIÓN DE CASOS DE PRUEBA

def procesar_expresion(expresion: str):
    print("=" * 72)
    print(f"Expresión de entrada : {expresion}")

    try:
        tokens = tokenizar(expresion)
        print(f"Tokens extraídos     : {tokens}")
    except ValueError as err_lexico:
        print(f"Estado Sintáctico    : Error Léxico ({err_lexico})")
        return

    es_valida, estado_pila, estado_sintactico, detalle = validar_pda(tokens)
    print(f"Pila / Balanceo      : {estado_pila}")
    print(f"Estado Sintáctico    : {estado_sintactico}")

    if not es_valida:
        print(f"Detalle del fallo    : {detalle}")
        print("Resultado Esperado   : N/A")
        return

    ast = construir_ast(tokens)
    print("\nÁrbol de Sintaxis Abstracta (AST):")
    print(formatear_ast_ascii(ast))

    try:
        resultado = evaluar_ast_postorden(ast)
        print(f"\nResultado Final      : {resultado}")
    except ZeroDivisionError as err_div:
        print(f"\nAlerta de Evaluación : {err_div}")


if __name__ == "__main__":
    casos_de_prueba = [
        "3 + 5 * 2",
        "(3 + 5) * 2",
        "2 ^ 3 ^ 2",
        "((4 + 2) * (10 - 5))",
        "(3 + 5 * 2",
        "3 + * 5",
        ")2 + 3(",
        "10 / (5 - 5)"
    ]

    print("\n--- BATERÍA DE CASOS DE PRUEBA DEL PROYECTO ---")
    for caso in casos_de_prueba:
        procesar_expresion(caso)
    print("=" * 72)

    while True:
        try:
            entrada = input("\nIngresa una expresión aritmética (o 'salir' para terminar): ").strip()
            if entrada.lower() in ('salir', 'exit', 'q', ''):
                break
            procesar_expresion(entrada)
        except (EOFError, KeyboardInterrupt):
            break

# HOLA