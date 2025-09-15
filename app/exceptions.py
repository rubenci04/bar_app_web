# Excepciones personalizadas para la base de datos
class DatabaseError(Exception):
    """Excepción base para errores de base de datos"""
    pass

class TransactionError(DatabaseError):
    """Error específico para transacciones de base de datos"""
    pass

class ConnectionError(DatabaseError):
    """Error específico para problemas de conexión a la base de datos"""
    pass

class ValidationError(DatabaseError):
    """Error específico para validaciones de datos"""
    pass